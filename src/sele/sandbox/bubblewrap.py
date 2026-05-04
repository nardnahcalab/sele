"""Bubblewrap-based sandbox.

A lighter, faster alternative to Docker on Linux. Each ``run_shell`` call
launches ``bwrap`` to execute the command inside fresh PID/IPC/UTS/mount
namespaces, with all capabilities dropped, a tmpfs ``/tmp``, and the host
``/usr``, ``/etc``, etc. bind-mounted read-only. The sandbox cwd is
bind-mounted read-write so progress persists across calls.

File operations (``read_file`` / ``write_file``) run in-process inside
the configured cwd: sele itself is the trusted control plane, and the
dangerous surface is "execute arbitrary shell commands written by the
model" — that's what bwrap isolates.

Networking is configurable via ``egress``:

- ``mode: none`` — ``--unshare-net``. Total network blackout. Cannot be
  bypassed.
- ``mode: all`` — share the host network namespace. Same network
  exposure as ``host_direct``.
- ``mode: hosts`` — share the network but inject ``http_proxy`` /
  ``https_proxy`` env vars pointing at an in-process CONNECT proxy that
  allowlists hostnames. Best-effort; see ``_egress.py`` for caveats.

Install bubblewrap on the host:

  Debian/Ubuntu:  sudo apt install bubblewrap
  Fedora/RHEL:    sudo dnf install bubblewrap
  Arch:           sudo pacman -S bubblewrap
  Alpine:         sudo apk add bubblewrap

Linux only.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from sele.config import SandboxConfig
from sele.sandbox._egress import EgressProxy

DEFAULT_RO_BINDS: list[str] = [
    "/usr",
    "/etc",
    "/opt",
    "/lib",
    "/lib64",
    "/lib32",
    "/bin",
    "/sbin",
    "/var/lib",
]

DEFAULT_TMPFS: list[str] = [
    "/tmp",
    "/var/tmp",
    "/run",
    "/home",
    "/root",
]


_INSTALL_HINT = (
    "bwrap (bubblewrap) is not installed. Install it:\n"
    "  Debian/Ubuntu:  sudo apt install bubblewrap\n"
    "  Fedora/RHEL:    sudo dnf install bubblewrap\n"
    "  Arch:           sudo pacman -S bubblewrap\n"
    "  Alpine:         sudo apk add bubblewrap\n"
    "or pick a different sandbox kind in your profile (e.g. host_direct, docker)."
)


def find_bwrap(custom_path: str | None = None) -> str:
    """Locate the ``bwrap`` binary or raise a clear error."""

    if custom_path:
        if shutil.which(custom_path) or Path(custom_path).is_file():
            return custom_path
        raise RuntimeError(f"configured bwrap path {custom_path!r} is not executable")
    path = shutil.which("bwrap")
    if path is None:
        raise RuntimeError(_INSTALL_HINT)
    return path


def build_bwrap_args(
    bwrap_path: str,
    config: SandboxConfig,
    cwd: Path,
    command: str,
    env: dict[str, str],
) -> list[str]:
    """Pure-function: produce the full ``bwrap`` argv for a shell command."""

    args: list[str] = [
        bwrap_path,
        "--die-with-parent",
        "--new-session",
        "--unshare-ipc",
        "--unshare-pid",
        "--unshare-uts",
        "--unshare-cgroup-try",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
    ]

    if config.egress.mode == "none":
        args += ["--unshare-net"]

    if config.hostname:
        args += ["--hostname", config.hostname]

    ro_binds = config.ro_binds if config.ro_binds is not None else DEFAULT_RO_BINDS
    for path in ro_binds:
        if Path(path).exists():
            args += ["--ro-bind", path, path]

    tmpfs = config.tmpfs if config.tmpfs is not None else DEFAULT_TMPFS
    for path in tmpfs:
        args += ["--tmpfs", path]

    # cwd as the only rw mount by default.
    args += ["--bind", str(cwd), str(cwd)]
    for path in config.rw_binds:
        full = str(Path(path).expanduser().resolve())
        args += ["--bind", full, full]

    args += ["--chdir", str(cwd)]
    args += ["--cap-drop", "ALL"]

    # Clear inherited env, then re-add only what we want.
    args += ["--clearenv"]
    for k, v in env.items():
        args += ["--setenv", k, v]

    args += ["--", "bash", "-lc", command]
    return args


class BubblewrapSandbox:
    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.cwd = Path(self.config.cwd).expanduser().resolve()
        self.cwd.mkdir(parents=True, exist_ok=True)
        # Custom bwrap path can be set via SandboxConfig extras.
        custom = getattr(self.config, "bwrap_path", None)
        self.bwrap_path = find_bwrap(custom)

        self._egress_proxy: EgressProxy | None = None
        if self.config.egress.mode == "hosts":
            self._egress_proxy = EgressProxy(
                self.config.egress.hosts, port=self.config.egress.proxy_port
            )
            self._egress_proxy.start()

    # ------------------------------------------------------------------ utils

    def resolve(self, path: str) -> str:
        candidate = (
            (self.cwd / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        )
        try:
            candidate.relative_to(self.cwd)
        except ValueError as exc:
            raise PermissionError(
                f"path {path!r} escapes sandbox cwd {self.cwd}"
            ) from exc
        return str(candidate)

    def _env(self) -> dict[str, str]:
        allow = set(self.config.env_allowlist or [])
        env = {k: v for k, v in os.environ.items() if k in allow}
        env.setdefault("PATH", os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"))
        env.setdefault("HOME", "/tmp")
        env.setdefault("SHELL", "/bin/bash")
        if self._egress_proxy is not None:
            proxy_url = f"http://127.0.0.1:{self._egress_proxy.port}"
            for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
                env[key] = proxy_url
            env["no_proxy"] = ""
        return env

    # ------------------------------------------------------------------ ops

    def build_args(self, command: str) -> list[str]:
        return build_bwrap_args(
            self.bwrap_path, self.config, self.cwd, command, self._env()
        )

    def run_shell(self, command: str, *, timeout: float | None = None) -> tuple[int, str, str]:
        proc = subprocess.run(
            self.build_args(command),
            capture_output=True,
            text=True,
            timeout=timeout if timeout is not None else self.config.timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def read_file(self, path: str, *, max_bytes: int = 200_000) -> str:
        target = Path(self.resolve(path))
        data = target.read_bytes()[:max_bytes]
        try:
            return data.decode()
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> int:
        target = Path(self.resolve(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return len(content)
