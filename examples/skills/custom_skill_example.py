"""Example: Writing a custom skill for sele.

This example demonstrates how to create a custom skill that tracks task progress
and provides feedback to the agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sele import skill
from sele.skills import BaseSkill

if TYPE_CHECKING:
    from sele.loops.base import LoopContext
    from sele.types import Message, ModelResponse, ToolResult


@skill("progress_tracker")
class ProgressTrackerSkill(BaseSkill):
    """A skill that tracks and reports on task progress.
    
    This skill:
    1. Counts the number of tool calls made
    2. Tracks the types of tools used
    3. Monitors response length over time
    4. Reports progress at the end
    """

    name = "progress_tracker"

    def __init__(self):
        self.tool_call_count = 0
        self.tool_types: dict[str, int] = {}
        self.response_lengths: list[int] = []
        self.task_description = ""

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize the skill."""
        print(f"[{self.name}] Initialized")

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Called before each model step."""
        # You could inject progress prompts here
        pass

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
        """Generate a progress report."""
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
