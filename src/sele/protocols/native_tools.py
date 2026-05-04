"""Native tool-calling protocol.

Trusts the model/adapter to handle tool definitions natively (OpenAI
function calling). Pass-through render and parse.
"""

from __future__ import annotations

from sele.types import Message, ModelResponse, ToolCall, ToolSpec


class NativeToolsProtocol:
    name = "native_tools"

    def __init__(self, **_: object) -> None:
        pass

    def render_system(self, base: str, tools: list[ToolSpec]) -> str:
        return base

    def prepare_request(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> tuple[list[Message], list[ToolSpec]]:
        return messages, tools

    def parse_response(self, response: ModelResponse) -> tuple[str, list[ToolCall]]:
        return response.content, list(response.tool_calls)
