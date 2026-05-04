"""Run tools directly on the host with a working-directory boundary.

Not a security sandbox — agents with this sandbox can do anything the
invoking user can do. The cwd boundary only prevents accidental escape via
relative paths in fs_read / fs_write; shell commands are unconstrained.
Use the Approval policy and review traces to stay safe.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sele.config import SandboxConfig


class HostDirectSandbox:
    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.cwd = Path(self.config.cwd).expanduser().resolve()
        self.cwd.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ utils

    def resolve(self, path: str) -> str:
        """Resolve ``path`` relative to the sandbox cwd. Reject escapes."""

        candidate = (self.cwd / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
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
        env.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin"))
        return env

    # ------------------------------------------------------------------ ops

    def run_shell(self, command: str, *, timeout: float | None = None) -> tuple[int, str, str]:
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(self.cwd),
            env=self._env(),
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
