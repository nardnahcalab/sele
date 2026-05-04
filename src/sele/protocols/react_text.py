"""ReAct-style text protocol.

Tools are described in the system prompt. The model is asked to emit calls
as fenced JSON code blocks::

    ```tool
    {"name": "shell", "arguments": {"command": "ls"}}
    ```

This works with any text-completion or chat model that does not support
native function calling. Parsing is permissive — multiple blocks per turn
are supported.
"""

from __future__ import annotations

import json
import re
import uuid

from sele.types import Message, ModelResponse, ToolCall, ToolSpec

_BLOCK_RE = re.compile(r"```\s*tool\s*\n(?P<body>.*?)```", re.DOTALL | re.IGNORECASE)
_FINAL_RE = re.compile(r"```\s*final\s*\n(?P<body>.*?)```", re.DOTALL | re.IGNORECASE)


def _format_tools(tools: list[ToolSpec]) -> str:
    lines: list[str] = []
    for t in tools:
        params = json.dumps(t.parameters, indent=2)
        lines.append(f"- {t.name}: {t.description}\n  parameters schema:\n{params}")
    return "\n".join(lines)


SYSTEM_TEMPLATE = """{base}

You can call tools. Available tools:
{tools_block}

When you want to call a tool, emit a fenced block with the language tag
`tool` containing JSON of the form `{{"name": "...", "arguments": {{...}}}}`.
You may emit multiple `tool` blocks in one turn; they will all be executed.

When you are done and ready to give the final answer, emit:

```final
<your final answer>
```

If you only emit prose without a `tool` or `final` block, the run will end.
"""


class ReActTextProtocol:
    name = "react_text"

    def __init__(self, **_: object) -> None:
        pass

    def render_system(self, base: str, tools: list[ToolSpec]) -> str:
        return SYSTEM_TEMPLATE.format(base=base, tools_block=_format_tools(tools))

    def prepare_request(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> tuple[list[Message], list[ToolSpec]]:
        # Don't send tool schemas natively; they're already in the system prompt.
        return messages, []

    def parse_response(self, response: ModelResponse) -> tuple[str, list[ToolCall]]:
        text = response.content or ""

        # Final answer wins outright.
        if final := _FINAL_RE.search(text):
            return final.group("body").strip(), []

        calls: list[ToolCall] = []
        for match in _BLOCK_RE.finditer(text):
            body = match.group("body").strip()
            try:
                obj = json.loads(body)
            except json.JSONDecodeError:
                continue
            name = obj.get("name") or obj.get("tool")
            args = obj.get("arguments") or obj.get("args") or {}
            if not isinstance(name, str) or not isinstance(args, dict):
                continue
            calls.append(ToolCall(id=f"react-{uuid.uuid4().hex[:8]}", name=name, arguments=args))

        # Strip tool blocks from prose so the visible content reads cleanly.
        clean = _BLOCK_RE.sub("", text).strip()
        return clean, calls
