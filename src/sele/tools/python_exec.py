"""Python execution tool: run Python code inside the sandbox."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

from sele.interfaces import Sandbox
from sele.types import ToolResult, ToolSpec


class _PythonExec:
    spec = ToolSpec(
        name="python_exec",
        description=(
            "Execute Python code in the sandbox working directory and return "
            "stdout, stderr, and exit code. For multi-line code, use triple quotes. "
            "The code runs in the sandbox's Python interpreter."
        ),
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use triple quotes for multi-line code.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds (default uses sandbox config).",
                },
            },
            "required": ["code"],
        },
        destructive=True,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        code = arguments.get("code")
        if not isinstance(code, str) or not code.strip():
            return ToolResult(
                call_id="", name=self.spec.name, ok=False, content="",
                error="missing or invalid 'code'",
            )
        timeout = arguments.get("timeout")
        try:
            timeout_f = float(timeout) if timeout is not None else None
        except (TypeError, ValueError):
            timeout_f = None

        # Use python3 -c for inline execution (python3 is more common on Linux).
        # Fall back to python if python3 is not available.
        # For multi-line code, we use a heredoc approach.
        if "\n" in code:
            # Multi-line: use a heredoc
            escaped = code.replace("'", "'\\''")  # Escape single quotes for shell
            command = f"python3 -c '{escaped}'"
        else:
            # Single-line: direct
            command = f"python3 -c {shlex.quote(code)}"

        try:
            rc, stdout, stderr = sandbox.run_shell(command, timeout=timeout_f)
        except subprocess.TimeoutExpired:
            return ToolResult(
                call_id=arguments.get("_call_id", ""),
                name=self.spec.name,
                ok=False,
                content="",
                error=f"execution timed out after {timeout_f}s",
            )
        ok = rc == 0
        code_preview = code[:100] + ("..." if len(code) > 100 else "")
        body = (
            f">>> {code_preview}\n[exit {rc}]\n"
            f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        )
        return ToolResult(
            call_id=arguments.get("_call_id", ""),
            name=self.spec.name,
            ok=ok,
            content=body,
            error=None if ok else f"non-zero exit: {rc}",
        )


python_exec = _PythonExec()
