"""OpenAI-compatible chat-completions adapter.

Works with any server that implements ``POST /v1/chat/completions`` in the
OpenAI shape: OpenAI itself, OpenRouter, vLLM, llama.cpp's server,
Ollama (>=0.1.30), LM Studio, Together, Groq, etc.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from sele.config import ModelConfig
from sele.models._chat_compat import (
    msg_to_openai_dict,
    parse_openai_choice,
    tool_to_openai_dict,
)
from sele.types import Message, ModelResponse, ToolSpec


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
            "messages": [msg_to_openai_dict(m) for m in messages],
        }
        if tools:
            body["tools"] = [tool_to_openai_dict(t) for t in tools]
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
        return parse_openai_choice(resp.json())

    def close(self) -> None:
        self._client.close()
