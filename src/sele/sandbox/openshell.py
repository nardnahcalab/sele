"""OpenShell-based sandbox.

OpenShell provides container-based isolation with policy enforcement for
filesystem, network, process, and inference. Requires Docker and the
openshell package.

Linux/macOS/Windows (with Docker). Requires the host package:
    pip install openshell
    Docker Desktop (or Docker daemon) must be running
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from sele.config import SandboxConfig

_OPENSHELL_HINT = (
    "OpenShell is not installed. Install it:\n"
    "  pip install openshell\n"
    "Docker Desktop (or Docker daemon) must be running.\n"
    "See https://github.com/NVIDIA/OpenShell for details."
)


def find_openshell() -> str:
    """Locate the openshell binary or raise a clear error."""
    import shutil

    path = shutil.which("openshell")
    if path is None:
        raise RuntimeError(_OPENSHELL_HINT)
    return path


class OpenShellSandbox:
    def __init__(self, config: SandboxConfig | None = None, _skip_create: bool = False):
        self.config = config or SandboxConfig()
        self.cwd = Path(self.config.cwd).expanduser().resolve()
        self.cwd.mkdir(parents=True, exist_ok=True)

        # Custom openshell path can be set via SandboxConfig extras
        custom = getattr(self.config, "openshell_path", None)
        self.openshell_path = custom or find_openshell()

        # Sandbox name (use a hash of the cwd for uniqueness)
        import hashlib
        self.sandbox_name = f"sele-{hashlib.md5(str(self.cwd).encode()).hexdigest()[:8]}"

        # Create the sandbox on first use (unless skipped for testing)
        self._sandbox_created = False
        if not _skip_create:
            self._ensure_sandbox()

    def _ensure_sandbox(self):
        """Create the OpenShell sandbox if it doesn't exist."""
        if self._sandbox_created:
            return

        try:
            # Create a base sandbox without an agent
            subprocess.run(
                [self.openshell_path, "sandbox", "create", self.sandbox_name],
                capture_output=True,
                check=True,
                text=True,
            )
            self._sandbox_created = True
        except subprocess.CalledProcessError as exc:
            # If sandbox already exists, that's okay
            if "already exists" not in exc.stderr:
                raise RuntimeError(f"Failed to create OpenShell sandbox: {exc.stderr}") from exc

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
        import os

        allow = set(self.config.env_allowlist or [])
        env = {k: v for k, v in os.environ.items() if k in allow}
        env.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin"))
        return env

    # ------------------------------------------------------------------ ops

    def run_shell(self, command: str, *, timeout: float | None = None) -> tuple[int, str, str]:
        """Execute a shell command in the OpenShell sandbox."""
        self._ensure_sandbox()

        try:
            # Execute command in the sandbox
            result = subprocess.run(
                [self.openshell_path, "sandbox", "exec", self.sandbox_name, command],
                capture_output=True,
                text=True,
                timeout=timeout if timeout is not None else self.config.timeout,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "execution timed out"

    def read_file(self, path: str, *, max_bytes: int = 200_000) -> str:
        """Read a file from the sandbox cwd."""
        # For now, read directly from host (like host_direct)
        # OpenShell sandboxes have the cwd bind-mounted
        target = Path(self.resolve(path))
        data = target.read_bytes()[:max_bytes]
        try:
            return data.decode()
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> int:
        """Write a file to the sandbox cwd."""
        # For now, write directly to host (like host_direct)
        # OpenShell sandboxes have the cwd bind-mounted
        target = Path(self.resolve(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return len(content)

    def cleanup(self):
        """Clean up the OpenShell sandbox."""
        if self._sandbox_created:
            try:
                subprocess.run(
                    [self.openshell_path, "sandbox", "delete", self.sandbox_name],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass  # Best effort cleanup
            self._sandbox_created = False

    def __del__(self):
        """Clean up on destruction."""
        self.cleanup()
