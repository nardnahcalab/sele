"""Base skill class for easier implementation of custom skills."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sele.loops.base import LoopContext
    from sele.types import Message, ModelResponse, ToolResult


class BaseSkill:
    """Base class for implementing skills.

    Subclass this to create custom skills. Override the hook methods you need:
    - initialize(): Called once before the loop starts
    - before_step(): Called before each model step
    - after_step(): Called after each model step completes
    - on_loop_end(): Called when the loop terminates

    Example::

        from sele import skill
        from sele.skills import BaseSkill

        @skill("my_skill")
        class MySkill(BaseSkill):
            name = "my_skill"

            def initialize(self, ctx):
                print(f"Initializing {self.name}")

            def before_step(self, step_index, memory):
                print(f"Step {step_index}: {len(memory)} messages in memory")

            def after_step(self, step_index, response, tool_results):
                print(f"Step {step_index} completed")

            def on_loop_end(self, final_text, total_steps):
                return final_text
    """

    name: str = "base_skill"

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize the skill with the loop context.

        Called once before the loop starts. Skills can inspect and potentially
        modify the context (e.g., add specialized tools, update system prompt).

        Args:
            ctx: The LoopContext containing all agent components
        """
        pass

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Hook called before each model step.

        Skills can inspect memory and potentially modify it (e.g., inject
        reflection prompts, compress context).

        Args:
            step_index: The current step number (0-based)
            memory: The current message history
        """
        pass

    def after_step(
        self, step_index: int, response: ModelResponse, tool_results: list[ToolResult]
    ) -> None:
        """Hook called after each model step completes.

        Skills can inspect the step outcome and potentially trigger actions
        (e.g., evaluate progress, trigger re-planning).

        Args:
            step_index: The current step number (0-based)
            response: The model's response
            tool_results: Results from executing tool calls (if any)
        """
        pass

    def on_loop_end(self, final_text: str, total_steps: int) -> str:
        """Hook called when the loop terminates.

        Skills can post-process the final output or trigger cleanup.

        Args:
            final_text: The final text output from the agent
            total_steps: Total number of steps executed

        Returns:
            The (possibly modified) final text
        """
        return final_text
