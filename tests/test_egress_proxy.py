"""Tests for the egress allowlist matcher and the threaded CONNECT proxy.

The proxy tests open real localhost sockets; they do not require
``bwrap``. They use a stub upstream server (also on localhost) to verify
that allowlisted hosts get connected and disallowed ones get rejected
with HTTP 403.
"""

from __future__ import annotations

import socket
import threading
from contextlib import closing

import pytest

from sele.sandbox._egress import EgressProxy, host_matches

# ---------------------------------------------------------------- matcher


@pytest.mark.parametrize(
    "host,allowlist,expected",
    [
        ("github.com", ["github.com"], True),
        ("Github.COM", ["github.com"], True),
        ("api.github.com", ["github.com"], False),
        ("api.github.com", ["*.github.com"], True),
        ("github.com", ["*.github.com"], True),  # wildcard suffix matches bare suffix
        ("evil.com.github.com.attacker.com", ["*.github.com"], False),
        ("evil.com", ["github.com", "*.example.org"], False),
        ("foo.example.org", ["*.example.org"], True),
        ("127.0.0.1", ["127.0.0.1"], True),
    ],
)
def test_host_matches(host: str, allowlist: list[str], expected: bool) -> None:
    assert host_matches(host, allowlist) is expected


# ---------------------------------------------------------------- proxy


def _start_echo_server() -> tuple[int, threading.Event]:
    """Tiny TCP echo server bound to 127.0.0.1; returns (port, stop_event)."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(4)
    sock.settimeout(0.2)
    port = sock.getsockname()[1]
    stop = threading.Event()

    def serve() -> None:
        with sock:
            while not stop.is_set():
                try:
                    conn, _ = sock.accept()
                except TimeoutError:
                    continue
                with conn:
                    try:
                        data = conn.recv(64)
                        if data:
                            conn.sendall(b"ECHO:" + data)
                    except OSError:
                        pass

    threading.Thread(target=serve, daemon=True).start()
    return port, stop


def _connect_via_proxy(proxy_port: int, target_host: str, target_port: int) -> socket.socket:
    s = socket.create_connection(("127.0.0.1", proxy_port), timeout=2.0)
    s.sendall(f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}\r\n\r\n".encode())
    s.settimeout(2.0)
    # Read status line + headers up to blank line.
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    if not buf.startswith(b"HTTP/1.1 200"):
        raise AssertionError(f"proxy did not return 200: {buf!r}")
    return s


def test_proxy_allows_listed_host_and_pipes_data() -> None:
    upstream_port, stop_upstream = _start_echo_server()
    try:
        proxy = EgressProxy(allowed_hosts=["127.0.0.1"])
        proxy.start()
        try:
            with closing(_connect_via_proxy(proxy.port, "127.0.0.1", upstream_port)) as s:
                s.sendall(b"hello")
                got = s.recv(64)
                assert got == b"ECHO:hello"
        finally:
            proxy.stop()
    finally:
        stop_upstream.set()


def test_proxy_rejects_unlisted_host_with_403() -> None:
    proxy = EgressProxy(allowed_hosts=["github.com"])
    proxy.start()
    try:
        s = socket.create_connection(("127.0.0.1", proxy.port), timeout=2.0)
        s.sendall(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com\r\n\r\n")
        s.settimeout(2.0)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        s.close()
        assert buf.startswith(b"HTTP/1.1 403"), f"expected 403, got {buf!r}"
    finally:
        proxy.stop()


def test_proxy_rejects_non_connect_with_405() -> None:
    proxy = EgressProxy(allowed_hosts=["github.com"])
    proxy.start()
    try:
        s = socket.create_connection(("127.0.0.1", proxy.port), timeout=2.0)
        s.sendall(b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
        s.settimeout(2.0)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        s.close()
        assert buf.startswith(b"HTTP/1.1 405"), f"expected 405, got {buf!r}"
    finally:
        proxy.stop()
