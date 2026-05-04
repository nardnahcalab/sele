"""OpenAI-compatible chat-completions adapter.

Works with any server that implements ``POST /v1/chat/completions`` in the
OpenAI shape: OpenAI itself, OpenRouter, vLLM, llama.cpp's server,
Ollama (>=0.1.30), LM Studio, Together, Groq, etc.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from sele.config import ModelConfig
from sele.types import Message, ModelResponse, ToolCall, ToolSpec


class OpenAICompatAdapter:
    """ModelAdapter that hits an OpenAI-compatible chat-completions endpoint."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._client = httpx.Client(timeout=config.timeout)

    # ------------------------------------------------------------------ utils

    def _resolve_api_key(self) -> str | None:
        if self.config.api_key:
            return self.config.api_key
        if self.config.api_key_env:
            return os.environ.get(self.config.api_key_env)
        # common fallbacks
        for env in ("OPENAI_API_KEY", "OPENROUTER_API_KEY"):
            if v := os.environ.get(env):
                return v
        return None

    def _base_url(self) -> str:
        url = self.config.base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        return url.rstrip("/")

    @staticmethod
    def _msg_to_openai(msg: Message) -> dict[str, Any]:
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
            # OpenAI wants empty string content alongside tool_calls.
            if not out["content"]:
                out["content"] = ""
        return out

    @staticmethod
    def _tool_to_openai(spec: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }

    # ------------------------------------------------------------------ call

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [self._msg_to_openai(m) for m in messages],
        }
        if tools:
            body["tools"] = [self._tool_to_openai(t) for t in tools]
            if tool_choice:
                body["tool_choice"] = tool_choice
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens

        headers = {"Content-Type": "application/json", **self.config.extra_headers}
        if key := self._resolve_api_key():
            headers["Authorization"] = f"Bearer {key}"

        url = f"{self._base_url()}/chat/completions"
        resp = self._client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

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
            tool_calls.append(ToolCall(id=tc.get("id") or "", name=fn.get("name") or "", arguments=args))
        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason"),
            raw=data,
        )

    def close(self) -> None:
        self._client.close()
