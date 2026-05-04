"""Shell tool: run a bash command inside the sandbox."""

from __future__ import annotations

from typing import Any

from sele.interfaces import Sandbox
from sele.types import ToolResult, ToolSpec


class _ShellTool:
    spec = ToolSpec(
        name="shell",
        description=(
            "Run a bash command in the sandbox working directory and return "
            "stdout, stderr, and exit code. Prefer non-interactive commands."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run."},
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds (default uses sandbox config).",
                },
            },
            "required": ["command"],
        },
        destructive=True,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        command = arguments.get("command")
        if not isinstance(command, str) or not command.strip():
            return ToolResult(
                call_id="", name=self.spec.name, ok=False, content="",
                error="missing or invalid 'command'",
            )
        timeout = arguments.get("timeout")
        try:
            timeout_f = float(timeout) if timeout is not None else None
        except (TypeError, ValueError):
            timeout_f = None
        rc, stdout, stderr = sandbox.run_shell(command, timeout=timeout_f)
        ok = rc == 0
        body = f"$ {command}\n[exit {rc}]\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        return ToolResult(
            call_id=arguments.get("_call_id", ""),
            name=self.spec.name,
            ok=ok,
            content=body,
            error=None if ok else f"non-zero exit: {rc}",
        )


shell = _ShellTool()
