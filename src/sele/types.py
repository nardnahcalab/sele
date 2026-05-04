"""Core data types shared across sele's pluggable surfaces.

These are intentionally minimal and serializable. Adapters/protocols/loops
exchange these objects; concrete implementations may carry richer state
internally.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ToolCall(BaseModel):
    """A model-issued request to invoke a tool."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """The outcome of executing a ToolCall."""

    call_id: str
    name: str
    ok: bool
    content: str
    error: str | None = None


class Message(BaseModel):
    """A single chat message in the agent transcript."""

    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None  # set when role == "tool"
    name: str | None = None  # tool name when role == "tool"


class ToolSpec(BaseModel):
    """Declarative description of a tool, exposed to the model."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    destructive: bool = False  # used by approval policies


class ModelResponse(BaseModel):
    """Normalized response from a ModelAdapter."""

    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None


class Step(BaseModel):
    """One iteration of the agent loop, captured for tracing."""

    index: int
    messages_in: list[Message]
    response: ModelResponse | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
    note: str | None = None
