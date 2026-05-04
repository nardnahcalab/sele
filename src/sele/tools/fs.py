"""Filesystem tools: read and write files inside the sandbox cwd."""

from __future__ import annotations

from typing import Any

from sele.interfaces import Sandbox
from sele.types import ToolResult, ToolSpec


class _FsRead:
    spec = ToolSpec(
        name="fs_read",
        description="Read a UTF-8 text file inside the sandbox cwd.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to sandbox cwd."},
                "max_bytes": {
                    "type": "integer",
                    "description": "Truncate after this many bytes (default 200000).",
                },
            },
            "required": ["path"],
        },
        destructive=False,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        path = arguments.get("path")
        if not isinstance(path, str):
            return ToolResult(call_id="", name=self.spec.name, ok=False, content="", error="missing 'path'")
        max_bytes = int(arguments.get("max_bytes") or 200_000)
        try:
            content = sandbox.read_file(path, max_bytes=max_bytes)
        except (FileNotFoundError, PermissionError, IsADirectoryError) as exc:
            return ToolResult(call_id="", name=self.spec.name, ok=False, content="", error=str(exc))
        return ToolResult(call_id="", name=self.spec.name, ok=True, content=content)


class _FsWrite:
    spec = ToolSpec(
        name="fs_write",
        description=(
            "Create or overwrite a UTF-8 text file inside the sandbox cwd. "
            "Returns the number of bytes written."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to sandbox cwd."},
                "content": {"type": "string", "description": "Full file contents to write."},
            },
            "required": ["path", "content"],
        },
        destructive=True,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        path = arguments.get("path")
        content = arguments.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            return ToolResult(
                call_id="", name=self.spec.name, ok=False, content="",
                error="'path' and 'content' must be strings",
            )
        try:
            n = sandbox.write_file(path, content)
        except PermissionError as exc:
            return ToolResult(call_id="", name=self.spec.name, ok=False, content="", error=str(exc))
        return ToolResult(call_id="", name=self.spec.name, ok=True, content=f"wrote {n} bytes to {path}")


fs_read = _FsRead()
fs_write = _FsWrite()
