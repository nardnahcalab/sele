"""Example: Writing a custom skill for sele.

This example demonstrates how to create a custom skill that tracks task progress
and provides feedback to the agent.

Key patterns:
1. Store ctx.memory in initialize() to modify conversation
2. Use memory.append() to inject prompts during before_step()
3. Use on_loop_end() to modify final output
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sele import skill
from sele.skills import BaseSkill
from sele.types import Message

if TYPE_CHECKING:
    from sele.interfaces import Memory
    from sele.loops.base import LoopContext
    from sele.types import ModelResponse, ToolResult


@skill("progress_tracker")
class ProgressTrackerSkill(BaseSkill):
    """A skill that tracks and reports on task progress.

    This skill:
    1. Counts the number of tool calls made
    2. Tracks the types of tools used
    3. Monitors response length over time
    4. Injects periodic progress prompts into memory
    5. Reports progress at the end
    """

    name = "progress_tracker"

    def __init__(self):
        self.tool_call_count = 0
        self.tool_types: dict[str, int] = {}
        self.response_lengths: list[int] = []
        self._memory: Memory | None = None
        self.progress_check_interval = 5
        self.last_progress_step = 0

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize the skill and store memory reference."""
        self._memory = ctx.memory
        print(f"[{self.name}] Initialized")

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Called before each model step.

        This is where you can inject prompts into the conversation.
        """
        # Inject progress reminder every N steps
        if (step_index - self.last_progress_step >= self.progress_check_interval
            and self._memory is not None):
            prompt = (
                "[Progress Check] You've been working for a while. "
                "Consider if you're making progress toward the goal. "
                "If stuck, try a different approach."
            )
            self._memory.append(Message(role="user", content=prompt))
            self.last_progress_step = step_index

    def after_step(
        self, step_index: int, response: ModelResponse, tool_results: list[ToolResult]
    ) -> None:
        """Track tool usage and response length."""
        # Track response length
        self.response_lengths.append(len(response.content))

        # Track tool calls
        if response.tool_calls:
            self.tool_call_count += len(response.tool_calls)
            for call in response.tool_calls:
                self.tool_types[call.name] = self.tool_types.get(call.name, 0) + 1

    def on_loop_end(self, final_text: str, total_steps: int) -> str:
        """Generate a progress report and append to final output."""
        report = self._generate_report(total_steps)
        return final_text + "\n" + report

    def _generate_report(self, total_steps: int) -> str:
        """Generate a detailed progress report."""
        lines = [
            "\n[Progress Report]",
            f"Total steps: {total_steps}",
            f"Total tool calls: {self.tool_call_count}",
        ]

        if self.tool_types:
            lines.append("Tool usage breakdown:")
            for tool_name, count in sorted(self.tool_types.items()):
                lines.append(f"  - {tool_name}: {count} calls")

        if self.response_lengths:
            avg_length = sum(self.response_lengths) / len(self.response_lengths)
            max_length = max(self.response_lengths)
            min_length = min(self.response_lengths)
            lines.extend([
                f"Response length stats:",
                f"  - Average: {avg_length:.0f} chars",
                f"  - Max: {max_length} chars",
                f"  - Min: {min_length} chars",
            ])

        return "\n".join(lines)


if __name__ == "__main__":
    # Example usage in a profile:
    # 
    # loop:
    #   skills:
    #     enabled: true
    #     skills: [progress_tracker]
    #
    # Then run:
    # sele run "your task" -p your-profile
    
    print("Progress tracker skill loaded.")
    print("Add to your profile to use:")
    print("""
    loop:
      skills:
        enabled: true
        skills: [progress_tracker]
    """)
