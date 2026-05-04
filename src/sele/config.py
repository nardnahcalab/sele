"""Profile loading and schema.

A profile is a YAML file that selects one implementation for each pluggable
surface, plus per-component config. It looks like::

    name: local-ollama
    description: Llama 3.1 via Ollama, ReAct text protocol.
    model:
      adapter: openai_compat
      base_url: http://localhost:11434/v1
      model: llama3.1:8b
      api_key: ollama
      temperature: 0.2
    protocol: react_text
    loop:
      kind: tool_loop
      max_steps: 25
    memory: full_history
    sandbox:
      kind: host_direct
      cwd: .
    approval: confirm_destructive
    tools: [shell, fs_read, fs_write]
    tracer: jsonl
    system_prompt: |
      You are sele, ...
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Lax(BaseModel):
    model_config = ConfigDict(extra="allow")


class ModelConfig(_Lax):
    adapter: str = "openai_compat"
    # Common params (used by all adapters where applicable)
    model: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float = 120.0

    # OpenAI-compatible HTTP transport
    base_url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    extra_headers: dict[str, str] = Field(default_factory=dict)

    # In-process native backends (e.g. llama_cpp_native)
    model_path: str | None = None  # path to a local .gguf
    n_ctx: int | None = None  # context window
    n_gpu_layers: int | None = None  # -1 = offload all
    n_threads: int | None = None
    seed: int | None = None
    chat_format: str | None = None  # e.g. "llama-3", "chatml", "mistral-instruct"
    verbose: bool = False

    # Extra sampling params (forwarded when the adapter supports them)
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    repeat_penalty: float | None = None
    stop: list[str] | None = None


class LoopConfig(_Lax):
    kind: str = "tool_loop"
    max_steps: int = 25


class MemoryConfig(_Lax):
    """Settings for any Memory implementation. Unknown fields pass through
    via ``extra='allow'`` so individual implementations can read what they need."""

    kind: str = "full_history"

    # SummarizeMemory fields (ignored by full_history)
    trigger_chars: int = 24000  # compact when total content exceeds this
    recent_chars: int = 12000  # target size of the recent verbatim window
    prompt: str | None = None  # custom summarizer prompt; default in the impl
    summary_role: str = "system"  # role for the inserted summary message


class EgressConfig(_Lax):
    """Network egress policy for sandboxes that support it.

    - ``none``: Block all outbound network. For Bubblewrap this means
      ``--unshare-net``; cannot be bypassed.
    - ``all``: Share the host network namespace. Same network access as
      ``host_direct``.
    - ``hosts``: Share the host network but route the sandbox through a
      lightweight HTTP CONNECT proxy that allowlists hostnames (including
      ``*.suffix`` wildcards). Best-effort only: tools that ignore
      ``http_proxy`` / ``https_proxy`` env vars or use raw sockets can
      bypass this. Use ``none`` for hard guarantees.
    """

    mode: str = "all"  # one of: none, all, hosts
    hosts: list[str] = Field(default_factory=list)
    proxy_port: int = 0  # 0 = auto-bind


class SandboxConfig(_Lax):
    kind: str = "host_direct"
    cwd: str = "."
    env_allowlist: list[str] = Field(
        default_factory=lambda: ["PATH", "HOME", "LANG", "LC_ALL", "USER", "SHELL", "TERM"]
    )
    timeout: float = 60.0

    # Bubblewrap-specific (ignored by host_direct)
    hostname: str = "sele-sandbox"
    ro_binds: list[str] | None = None  # None -> use sandbox's defaults
    rw_binds: list[str] = Field(default_factory=list)
    tmpfs: list[str] | None = None  # None -> use sandbox's defaults
    egress: EgressConfig = Field(default_factory=EgressConfig)


class TracerConfig(_Lax):
    kind: str = "jsonl"
    dir: str = ".sele/runs"


class Profile(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    model: ModelConfig = Field(default_factory=ModelConfig)
    protocol: str = "native_tools"
    loop: LoopConfig = Field(default_factory=LoopConfig)
    memory: MemoryConfig | str = Field(default_factory=MemoryConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    approval: str = "confirm_destructive"
    tools: list[str] = Field(default_factory=lambda: ["shell", "fs_read", "fs_write"])
    tracer: TracerConfig | str = Field(default_factory=TracerConfig)
    system_prompt: str = ""


DEFAULT_SYSTEM_PROMPT = (
    "You are sele, a careful command-line agent.\n"
    "- Think step-by-step. Prefer small, verifiable actions.\n"
    "- Use tools when they help; otherwise answer directly.\n"
    "- Stop and report when the task is done."
)


def _bundled_profile_path(name: str) -> Path | None:
    try:
        root = resources.files("sele").joinpath("profiles")
    except (ModuleNotFoundError, FileNotFoundError):
        return None
    candidate = root.joinpath(f"{name}.yaml")
    try:
        if candidate.is_file():
            return Path(str(candidate))
    except (FileNotFoundError, OSError):
        pass
    return None


def _user_profile_path(name: str) -> Path | None:
    for base in (Path.cwd() / ".sele" / "profiles", Path.home() / ".config" / "sele" / "profiles"):
        candidate = base / f"{name}.yaml"
        if candidate.is_file():
            return candidate
    return None


def resolve_profile_path(name_or_path: str) -> Path:
    """Resolve a profile name or filesystem path to an absolute Path."""

    p = Path(name_or_path)
    if p.suffix in {".yaml", ".yml"} and p.exists():
        return p.resolve()
    user = _user_profile_path(name_or_path)
    if user is not None:
        return user.resolve()
    bundled = _bundled_profile_path(name_or_path)
    if bundled is not None:
        return bundled.resolve()
    raise FileNotFoundError(f"profile not found: {name_or_path!r}")


def load_profile(name_or_path: str) -> Profile:
    path = resolve_profile_path(name_or_path)
    raw = yaml.safe_load(path.read_text()) or {}
    raw.setdefault("name", path.stem)
    raw.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
    return Profile.model_validate(raw)


def list_bundled_profiles() -> list[str]:
    try:
        root = resources.files("sele").joinpath("profiles")
        return sorted(p.stem for p in root.iterdir() if p.suffix in {".yaml", ".yml"})  # type: ignore[union-attr]
    except (ModuleNotFoundError, FileNotFoundError, AttributeError):
        return []


def coerce_tracer_config(value: TracerConfig | str | dict[str, Any]) -> TracerConfig:
    if isinstance(value, TracerConfig):
        return value
    if isinstance(value, str):
        return TracerConfig(kind=value)
    return TracerConfig(**value)


def coerce_memory_config(value: MemoryConfig | str | dict[str, Any]) -> MemoryConfig:
    if isinstance(value, MemoryConfig):
        return value
    if isinstance(value, str):
        return MemoryConfig(kind=value)
    return MemoryConfig(**value)
