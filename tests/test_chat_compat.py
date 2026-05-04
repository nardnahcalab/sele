"""Unit tests for shared OpenAI-shape chat helpers."""

from __future__ import annotations

import json

from sele.models._chat_compat import (
    msg_to_openai_dict,
    parse_openai_choice,
    tool_to_openai_dict,
)
from sele.types import Message, ToolCall, ToolSpec


def test_msg_to_openai_user_basic() -> None:
    out = msg_to_openai_dict(Message(role="user", content="hi"))
    assert out == {"role": "user", "content": "hi"}


def test_msg_to_openai_tool_role_carries_call_id_and_name() -> None:
    out = msg_to_openai_dict(
        Message(role="tool", content="ok", tool_call_id="c1", name="shell")
    )
    assert out["role"] == "tool"
    assert out["tool_call_id"] == "c1"
    assert out["name"] == "shell"


def test_msg_to_openai_assistant_with_tool_calls_serializes_args() -> None:
    msg = Message(
        role="assistant",
        content="",
        tool_calls=[ToolCall(id="c1", name="shell", arguments={"command": "ls"})],
    )
    out = msg_to_openai_dict(msg)
    assert out["role"] == "assistant"
    assert out["content"] == ""  # OpenAI requires non-null content alongside tool_calls
    assert out["tool_calls"][0]["function"]["name"] == "shell"
    assert json.loads(out["tool_calls"][0]["function"]["arguments"]) == {"command": "ls"}


def test_tool_to_openai_dict_shape() -> None:
    spec = ToolSpec(
        name="echo",
        description="d",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}},
    )
    out = tool_to_openai_dict(spec)
    assert out["type"] == "function"
    assert out["function"]["name"] == "echo"
    assert out["function"]["parameters"]["properties"]["x"]["type"] == "string"


def test_parse_openai_choice_text_only() -> None:
    payload = {"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]}
    resp = parse_openai_choice(payload)
    assert resp.content == "hello"
    assert resp.tool_calls == []
    assert resp.finish_reason == "stop"
    assert resp.raw == payload


def test_parse_openai_choice_with_tool_calls() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "shell",
                                "arguments": json.dumps({"command": "ls"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    resp = parse_openai_choice(payload)
    assert resp.content == ""  # None coerced to empty string
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "shell"
    assert resp.tool_calls[0].arguments == {"command": "ls"}


def test_parse_openai_choice_preserves_invalid_json_args() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "c1",
                            "function": {"name": "shell", "arguments": "not-json"},
                        }
                    ],
                }
            }
        ]
    }
    resp = parse_openai_choice(payload)
    assert resp.tool_calls[0].arguments == {"_raw": "not-json"}
