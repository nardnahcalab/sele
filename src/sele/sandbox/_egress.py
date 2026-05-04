"""Tiny HTTP CONNECT proxy with hostname allowlisting.

Used by ``BubblewrapSandbox`` when ``egress.mode == "hosts"``: well-behaved
tools inside the sandbox honor ``http_proxy`` / ``https_proxy`` env vars
and route through this proxy, which only forwards CONNECTs to allowlisted
hosts.

Important caveats — read before relying on this:
  - **CONNECT only.** Plain HTTP forwarding is not implemented. Most
    real-world endpoints are HTTPS, so curl/git/pip/requests usually work.
    Plain HTTP-to-allowlisted-host will fail.
  - **Bypassable.** Tools that ignore proxy env vars, talk raw TCP/UDP,
    or use DNS-over-HTTPS to a non-allowlisted host can still reach the
    network. For hard guarantees use ``egress.mode: none``.
  - **Hostname matching only.** Patterns are exact names (``github.com``)
    or wildcard suffixes (``*.github.com``). IP literals are matched as
    exact strings; we do not resolve allowlist entries.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import suppress

logger = logging.getLogger(__name__)


def host_matches(host: str, allowlist: set[str] | list[str]) -> bool:
    """Return True if ``host`` is permitted by ``allowlist``."""

    host = host.lower().strip(".")
    for raw in allowlist:
        pattern = raw.lower().strip(".")
        if pattern.startswith("*."):
            suffix = pattern[2:]
            if host == suffix or host.endswith("." + suffix):
                return True
        elif host == pattern:
            return True
    return False


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        with suppress(Exception):
            writer.close()


async def _handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    allowlist: set[str],
) -> None:
    try:
        line = await reader.readline()
        if not line.startswith(b"CONNECT "):
            writer.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            await writer.drain()
            return
        parts = line.split(b" ", 2)
        if len(parts) < 2:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            return
        target = parts[1].decode(errors="replace")

        # Drain remaining headers.
        while True:
            hdr = await reader.readline()
            if hdr in (b"\r\n", b""):
                break

        host, _, port_s = target.rpartition(":")
        try:
            port = int(port_s)
        except ValueError:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            return
        # Strip IPv6 brackets if present.
        host = host.strip("[]")

        if not host_matches(host, allowlist):
            logger.info("egress proxy: deny %s:%d", host, port)
            writer.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            await writer.drain()
            return

        try:
            up_reader, up_writer = await asyncio.open_connection(host, port)
        except OSError as exc:
            logger.warning("egress proxy: upstream connect failed: %s", exc)
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await writer.drain()
            return

        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        logger.info("egress proxy: allow %s:%d", host, port)
        await asyncio.gather(
            _pipe(reader, up_writer),
            _pipe(up_reader, writer),
            return_exceptions=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("egress proxy: handler error")
    finally:
        with suppress(Exception):
            writer.close()
            await writer.wait_closed()


class EgressProxy:
    """Threaded asyncio CONNECT proxy bound to ``127.0.0.1:port``.

    Run as a daemon thread. ``start()`` blocks until the listening port is
    known, then returns it. ``stop()`` closes the server but the thread
    will also die with the host process anyway (it's a daemon).
    """

    def __init__(self, allowed_hosts: list[str] | set[str], port: int = 0):
        self.allowed_hosts: set[str] = set(allowed_hosts)
        self._requested_port = port
        self._port: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: asyncio.AbstractServer | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    @property
    def port(self) -> int:
        if self._port is None:
            raise RuntimeError("EgressProxy not started")
        return self._port

    def is_allowed(self, host: str) -> bool:
        return host_matches(host, self.allowed_hosts)

    def start(self, *, ready_timeout: float = 5.0) -> int:
        if self._thread is not None:
            return self.port

        def runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop

            async def serve() -> None:
                self._server = await asyncio.start_server(
                    lambda r, w: _handle_client(r, w, self.allowed_hosts),
                    "127.0.0.1",
                    self._requested_port,
                )
                sock = self._server.sockets[0]
                self._port = sock.getsockname()[1]
                self._ready.set()
                async with self._server:
                    await self._server.serve_forever()

            with suppress(asyncio.CancelledError, RuntimeError):
                loop.run_until_complete(serve())
            loop.close()

        self._thread = threading.Thread(target=runner, daemon=True, name="sele-egress")
        self._thread.start()
        if not self._ready.wait(timeout=ready_timeout):
            raise RuntimeError("EgressProxy did not become ready in time")
        return self.port

    def stop(self) -> None:
        loop, server = self._loop, self._server
        if loop is not None and server is not None:
            with suppress(RuntimeError):
                loop.call_soon_threadsafe(server.close)
        # Daemon thread dies with the process; no join.
