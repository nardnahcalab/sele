"""Tests for the in-process llama.cpp adapter.

The real ``llama-cpp-python`` package is not required: we substitute a
fake ``Llama`` class via the module's loader hook, which lets us assert
on the exact ``create_chat_completion`` kwargs the adapter passes.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from sele.config import ModelConfig
from sele.models import llama_cpp_native as adapter_mod
from sele.models.llama_cpp_native import LlamaCppNativeAdapter, clear_cache
from sele.types import Message, ToolCall, ToolSpec


class _FakeLlama:
    """Minimal stand-in for llama_cpp.Llama used in tests."""

    def __init__(self, **kwargs: Any) -> None:
        self.init_kwargs = kwargs
        self.calls: list[dict[str, Any]] = []
        self._next_response: dict[str, Any] = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]
        }

    def queue(self, response: dict[str, Any]) -> None:
        self._next_response = response

    def create_chat_completion(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self._next_response


@pytest.fixture(autouse=True)
def _reset_cache_and_loader(monkeypatch: pytest.MonkeyPatch):
    clear_cache()

    def _fake_load(cfg: ModelConfig) -> _FakeLlama:
        if not cfg.model_path:
            raise ValueError("model_path required")
        return _FakeLlama(
            model_path=cfg.model_path,
            n_ctx=cfg.n_ctx,
            n_gpu_layers=cfg.n_gpu_layers,
            chat_format=cfg.chat_format,
        )

    monkeypatch.setattr(adapter_mod, "_load_llama", _fake_load)
    yield
    clear_cache()


def test_missing_model_path_is_a_clear_error() -> None:
    with pytest.raises(ValueError, match="model_path"):
        LlamaCppNativeAdapter(ModelConfig(adapter="llama_cpp_native", model="x"))


def test_complete_passes_messages_tools_and_sampling_params() -> None:
    cfg = ModelConfig(
        adapter="llama_cpp_native",
        model="m",
        model_path="/tmp/fake.gguf",
        n_ctx=4096,
        n_gpu_layers=-1,
        chat_format="llama-3",
        temperature=0.3,
        max_tokens=64,
        top_p=0.95,
        repeat_penalty=1.1,
        stop=["\n\n"],
    )
    a = LlamaCppNativeAdapter(cfg)
    a._llm.queue(  # type: ignore[attr-defined]
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "c1",
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
    )

    msgs = [
        Message(role="system", content="be brief"),
        Message(role="user", content="list files"),
    ]
    tools = [
        ToolSpec(
            name="shell",
            description="run",
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )
    ]
    resp = a.complete(msgs, tools)

    # Assert response was parsed correctly.
    assert resp.tool_calls and resp.tool_calls[0].name == "shell"
    assert resp.tool_calls[0].arguments == {"command": "ls"}

    # Assert the kwargs we forwarded.
    sent = a._llm.calls[-1]  # type: ignore[attr-defined]
    assert sent["messages"][0] == {"role": "system", "content": "be brief"}
    assert sent["tools"][0]["function"]["name"] == "shell"
    assert sent["temperature"] == 0.3
    assert sent["max_tokens"] == 64
    assert sent["top_p"] == 0.95
    assert sent["repeat_penalty"] == 1.1
    assert sent["stop"] == ["\n\n"]


def test_assistant_tool_calls_serialize_for_followup_turn() -> None:
    cfg = ModelConfig(adapter="llama_cpp_native", model="m", model_path="/tmp/fake.gguf")
    a = LlamaCppNativeAdapter(cfg)
    msgs = [
        Message(role="user", content="x"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="c1", name="shell", arguments={"command": "ls"})],
        ),
        Message(role="tool", content='{"ok": true}', tool_call_id="c1", name="shell"),
    ]
    a.complete(msgs, tools=[])
    sent = a._llm.calls[-1]  # type: ignore[attr-defined]
    assert sent["messages"][1]["tool_calls"][0]["function"]["name"] == "shell"
    assert sent["messages"][2]["tool_call_id"] == "c1"
    assert sent["messages"][2]["name"] == "shell"
    # No tools key since none were provided.
    assert "tools" not in sent


def test_model_cache_reuses_instance_for_same_params() -> None:
    cfg = ModelConfig(
        adapter="llama_cpp_native",
        model="m",
        model_path="/tmp/fake.gguf",
        n_ctx=2048,
        chat_format="llama-3",
    )
    a1 = LlamaCppNativeAdapter(cfg)
    a2 = LlamaCppNativeAdapter(cfg)
    assert a1._llm is a2._llm  # cache hit


def test_model_cache_keys_on_loader_relevant_params() -> None:
    base = dict(adapter="llama_cpp_native", model="m", model_path="/tmp/fake.gguf")
    a = LlamaCppNativeAdapter(ModelConfig(**base, n_ctx=2048))
    b = LlamaCppNativeAdapter(ModelConfig(**base, n_ctx=4096))
    assert a._llm is not b._llm  # different cache key
