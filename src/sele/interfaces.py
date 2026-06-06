"""Abstract interfaces for sele's pluggable surfaces.

Concrete implementations are registered via the registry. Loops should
program against these protocols, never against concrete types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sele.types import (
    Message,
    ModelResponse,
    Step,
    ToolCall,
    ToolResult,
    ToolSpec,
)

if TYPE_CHECKING:
    from sele.loops.base import LoopContext


@runtime_checkable
class ModelAdapter(Protocol):
    """Talks to a model backend. Implementations are constructed from the
    profile's ``model`` config."""

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse: ...


@runtime_checkable
class ToolProtocol(Protocol):
    """Defines how tools are presented to the model and how its output is
    parsed back into tool calls."""

    name: str

    def render_system(self, base: str, tools: list[ToolSpec]) -> str: ...

    def prepare_request(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
    ) -> tuple[list[Message], list[ToolSpec]]: ...

    def parse_response(self, response: ModelResponse) -> tuple[str, list[ToolCall]]: ...


@runtime_checkable
class Memory(Protocol):
    """Maintains the message history shown to the model on each step."""

    def append(self, message: Message) -> None: ...
    def extend(self, messages: list[Message]) -> None: ...
    def view(self) -> list[Message]: ...


@runtime_checkable
class Tool(Protocol):
    """Callable tool. ``spec`` describes it to the model; ``__call__`` executes
    it inside a Sandbox."""

    spec: ToolSpec

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult: ...


@runtime_checkable
class Sandbox(Protocol):
    """Execution boundary for tool calls."""

    def run_shell(self, command: str, *, timeout: float | None = None) -> tuple[int, str, str]: ...
    def read_file(self, path: str, *, max_bytes: int = 200_000) -> str: ...
    def write_file(self, path: str, content: str) -> int: ...
    def resolve(self, path: str) -> str: ...


@runtime_checkable
class ApprovalPolicy(Protocol):
    def check(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> bool: ...


@runtime_checkable
class Tracer(Protocol):
    run_id: str

    def start(self, profile_name: str, task: str) -> None: ...
    def step(self, step: Step) -> None: ...
    def end(self, status: str, message: str | None = None) -> None: ...


@runtime_checkable
class Skill(Protocol):
    """A skill augments the agent loop with specialized reasoning strategies,
    context management, or search space control.

    Skills can:
    - Modify the agent loop strategy (e.g., reflexion, tree search)
    - Control context window and compression
    - Configure breadth/depth of search
    - Provide specialized tools or prompts
    """

    name: str

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize the skill with the loop context.

        Called once before the loop starts. Skills can inspect and potentially
        modify the context (e.g., add specialized tools, update system prompt).
        """
        ...

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Hook called before each model step.

        Skills can inspect memory and potentially modify it (e.g., inject
        reflection prompts, compress context).
        """
        ...

    def after_step(
        self, step_index: int, response: ModelResponse, tool_results: list[ToolResult]
    ) -> None:
        """Hook called after each model step completes.

        Skills can inspect the step outcome and potentially trigger actions
        (e.g., evaluate progress, trigger re-planning).
        """
        ...

    def on_loop_end(self, final_text: str, total_steps: int) -> str:
        """Hook called when the loop terminates.

        Skills can post-process the final output or trigger cleanup.
        Returns the (possibly modified) final text.
        """
        ...


@runtime_checkable
class AgentLoop(Protocol):
    """The outer agent strategy. Drives Memory + ModelAdapter + Tools to a
    terminal state."""

    ctx: LoopContext

    def run(self, task: str) -> str: ...
