"""In-process llama.cpp adapter.

Loads a GGUF directly via ``llama-cpp-python`` and calls
``Llama.create_chat_completion``, which mirrors OpenAI's chat-completions
shape — including ``tool_calls`` for chat formats that support tool/function
calling (e.g. ``llama-3``, ``qwen``, ``functionary-v2``, ``chatml-function-calling``).

Install the optional dependency::

    pip install "sele[llama_cpp]"

Tool calling depends on the chat format / chat handler — pick a model+format
combo that supports it (Llama 3.1 Instruct, Qwen 2.5 Instruct, Functionary,
Hermes 2 Pro). For models without tool support, set ``protocol: react_text``
in your profile and tools will be rendered into the system prompt instead.

The first construction with a given ``(model_path, n_ctx, n_gpu_layers,
n_threads, seed, chat_format)`` tuple loads the model; subsequent
constructions in the same process reuse the cached ``Llama`` instance.
This makes ``sele chat`` viable with large native models, since each turn
rebuilds the loop (and therefore the adapter).
"""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING, Any

from sele.config import ModelConfig
from sele.models._chat_compat import (
    msg_to_openai_dict,
    parse_openai_choice,
    tool_to_openai_dict,
)
from sele.types import Message, ModelResponse, ToolSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from llama_cpp import Llama


_INSTALL_HINT = (
    "llama-cpp-python is not installed. Install the optional extra with:\n"
    "  pip install 'sele[llama_cpp]'\n"
    "or directly:\n"
    "  pip install llama-cpp-python"
)


# Process-wide model cache. Keyed on the parameters that actually affect the
# loaded weights / sampling state. Generation params (temperature, etc.) do
# not warrant a reload and are passed per-call.
_MODEL_CACHE: dict[tuple, Llama] = {}
_CACHE_LOCK = Lock()


def _cache_key(cfg: ModelConfig) -> tuple:
    return (
        cfg.model_path,
        cfg.n_ctx,
        cfg.n_gpu_layers,
        cfg.n_threads,
        cfg.seed,
        cfg.chat_format,
        cfg.verbose,
    )


def _load_llama(cfg: ModelConfig) -> Llama:
    try:
        from llama_cpp import Llama
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise ImportError(_INSTALL_HINT) from exc

    if not cfg.model_path:
        raise ValueError(
            "llama_cpp_native requires `model.model_path` (path to a .gguf file) in the profile."
        )

    kwargs: dict[str, Any] = {"model_path": cfg.model_path, "verbose": cfg.verbose}
    if cfg.n_ctx is not None:
        kwargs["n_ctx"] = cfg.n_ctx
    if cfg.n_gpu_layers is not None:
        kwargs["n_gpu_layers"] = cfg.n_gpu_layers
    if cfg.n_threads is not None:
        kwargs["n_threads"] = cfg.n_threads
    if cfg.seed is not None:
        kwargs["seed"] = cfg.seed
    if cfg.chat_format is not None:
        kwargs["chat_format"] = cfg.chat_format
    return Llama(**kwargs)


def _get_or_load(cfg: ModelConfig) -> Llama:
    key = _cache_key(cfg)
    with _CACHE_LOCK:
        llm = _MODEL_CACHE.get(key)
        if llm is not None:
            return llm
        llm = _load_llama(cfg)
        _MODEL_CACHE[key] = llm
        return llm


def clear_cache() -> None:
    """Drop all cached ``Llama`` instances. Useful in tests."""

    with _CACHE_LOCK:
        _MODEL_CACHE.clear()


class LlamaCppNativeAdapter:
    """ModelAdapter backed by an in-process ``llama_cpp.Llama``."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._llm = _get_or_load(config)

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse:
        cfg = self.config
        kwargs: dict[str, Any] = {
            "messages": [msg_to_openai_dict(m) for m in messages],
        }
        if tools:
            kwargs["tools"] = [tool_to_openai_dict(t) for t in tools]
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        if cfg.temperature is not None:
            kwargs["temperature"] = cfg.temperature
        if cfg.max_tokens is not None:
            kwargs["max_tokens"] = cfg.max_tokens
        if cfg.top_p is not None:
            kwargs["top_p"] = cfg.top_p
        if cfg.top_k is not None:
            kwargs["top_k"] = cfg.top_k
        if cfg.min_p is not None:
            kwargs["min_p"] = cfg.min_p
        if cfg.repeat_penalty is not None:
            kwargs["repeat_penalty"] = cfg.repeat_penalty
        if cfg.stop is not None:
            kwargs["stop"] = cfg.stop

        result = self._llm.create_chat_completion(**kwargs)
        # llama-cpp-python returns a dict that matches OpenAI's response shape.
        if not isinstance(result, dict):  # pragma: no cover - streaming guard
            raise TypeError(
                f"llama_cpp_native expected a dict response, got {type(result).__name__}; "
                "streaming is not supported in v0.1."
            )
        return parse_openai_choice(result)
