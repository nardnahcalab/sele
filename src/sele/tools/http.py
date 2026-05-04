"""HTTP tool: make HTTP requests from the sandbox."""

from __future__ import annotations

import shlex
from typing import Any

from sele.interfaces import Sandbox
from sele.types import ToolResult, ToolSpec


class _Http:
    spec = ToolSpec(
        name="http",
        description=(
            "Make an HTTP request from the sandbox. Returns status code, response body, "
            "and selected headers. Respects sandbox egress control (e.g., bubblewrap proxy)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to request."},
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, etc.). Default: GET.",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional headers as key-value pairs.",
                },
                "body": {
                    "type": "string",
                    "description": "Optional request body for POST/PUT requests.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds (default 30).",
                },
            },
            "required": ["url"],
        },
        destructive=True,  # Can have side effects via API calls
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        url = arguments.get("url")
        if not isinstance(url, str) or not url.strip():
            return ToolResult(
                call_id="", name=self.spec.name, ok=False, content="",
                error="missing or invalid 'url'",
            )

        method = arguments.get("method", "GET").upper()
        headers = arguments.get("headers") or {}
        body = arguments.get("body")
        timeout = arguments.get("timeout", 30)

        try:
            timeout_f = float(timeout)
        except (TypeError, ValueError):
            timeout_f = 30.0

        # Build curl command
        curl_args = ["curl", "-sS", "-w", "\\n%{http_code}", "-X", method]

        # Add headers
        if headers:
            if isinstance(headers, dict):
                for key, value in headers.items():
                    curl_args.extend(["-H", f"{shlex.quote(str(key))}: {shlex.quote(str(value))}"])

        # Add body if provided
        if body:
            curl_args.extend(["-d", shlex.quote(str(body))])

        # Add URL and timeout
        curl_args.extend(["--max-time", str(int(timeout_f)), shlex.quote(url)])

        command = " ".join(curl_args)

        rc, stdout, stderr = sandbox.run_shell(command, timeout=timeout_f)

        # Parse output: last line is status code, rest is body
        lines = stdout.strip().split("\n")
        if lines:
            status_line = lines[-1]
            body_text = "\n".join(lines[:-1])
            try:
                status_code = int(status_line)
            except ValueError:
                status_code = 0
                body_text = stdout  # Fallback if parsing fails
        else:
            status_code = 0
            body_text = ""

        response_ok = 200 <= status_code < 300
        body = f"{method} {url}\n[status {status_code}]\n--- response ---\n{body_text}"
        if stderr:
            body += f"\n--- stderr ---\n{stderr}"

        return ToolResult(
            call_id=arguments.get("_call_id", ""),
            name=self.spec.name,
            ok=response_ok,
            content=body,
            error=None if response_ok else f"HTTP {status_code}",
        )


http = _Http()
