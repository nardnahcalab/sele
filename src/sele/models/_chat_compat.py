"""Shared helpers for OpenAI-shape chat completions.

Both the OpenAI-compatible HTTP adapter and the in-process llama.cpp
adapter consume/produce the same JSON shape, so message and tool
conversion can be shared.
"""

from __future__ import annotations

import json
from typing import Any

from sele.types import Message, ModelResponse, ToolCall, ToolSpec


def msg_to_openai_dict(msg: Message) -> dict[str, Any]:
    """Convert a sele ``Message`` to an OpenAI-shape chat message dict."""

    out: dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
    if msg.role == "tool":
        out["tool_call_id"] = msg.tool_call_id or ""
        if msg.name:
            out["name"] = msg.name
    if msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in msg.tool_calls
        ]
        # OpenAI requires content to be present (empty allowed) alongside tool_calls.
        if not out["content"]:
            out["content"] = ""
    return out


def tool_to_openai_dict(spec: ToolSpec) -> dict[str, Any]:
    """Convert a ``ToolSpec`` to an OpenAI-shape tools entry."""

    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        },
    }


def parse_openai_choice(data: dict[str, Any]) -> ModelResponse:
    """Normalize an OpenAI ``chat.completion`` response into ``ModelResponse``.

    Accepts the full response payload (``choices[0]`` is read internally).
    Tool-call argument JSON is parsed best-effort; if a model emits invalid
    JSON the raw string is preserved under ``_raw`` so callers can surface
    a useful error to the model on the next turn.
    """

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""

    tool_calls: list[ToolCall] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            args = {"_raw": raw_args}
        tool_calls.append(
            ToolCall(id=tc.get("id") or "", name=fn.get("name") or "", arguments=args)
        )

    return ModelResponse(
        content=content,
        tool_calls=tool_calls,
        finish_reason=choice.get("finish_reason"),
        raw=data,
    )
