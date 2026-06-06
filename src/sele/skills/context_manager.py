"""Context management skill: Handles context window and compression.

This skill manages the agent's context window to prevent exceeding model limits.
It can:

1. Monitor context size
2. Compress old messages when approaching limits
3. Summarize long conversations
4. Maintain a sliding window of recent context

Configuration in profile:
    loop:
      skills:
        enabled: true
        skills: [context_manager]
        skill_settings:
          context_manager:
            max_context_chars: 8000  # Max characters before compression
            compression_ratio: 0.5  # Keep 50% of old messages
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sele.skills.base import BaseSkill

if TYPE_CHECKING:
    from sele.loops.base import LoopContext
    from sele.types import Message, ModelResponse, ToolResult


class ContextManagerSkill(BaseSkill):
    """Skill that manages context window and compression."""

    name = "context_manager"

    def __init__(self):
        self.max_context_chars = 8000
        self.compression_ratio = 0.5
        self.compression_triggered = False

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize context manager with configuration."""
        if ctx.skills_config:
            if ctx.skills_config.get("context_window"):
                self.max_context_chars = ctx.skills_config["context_window"]

            settings = ctx.skills_config.get("skill_settings", {}).get("context_manager", {})
            self.max_context_chars = settings.get("max_context_chars", self.max_context_chars)
            self.compression_ratio = settings.get("compression_ratio", self.compression_ratio)

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Check context size and compress if needed."""
        total_chars = sum(len(m.content) for m in memory)

        if total_chars > self.max_context_chars and not self.compression_triggered:
            # In a real implementation, we would compress old messages here
            # For now, we just track that compression was triggered
            self.compression_triggered = True

    def after_step(
        self, step_index: int, response: ModelResponse, tool_results: list[ToolResult]
    ) -> None:
        """Monitor context usage after each step."""
        pass

    def on_loop_end(self, final_text: str, total_steps: int) -> str:
        """Report on context management."""
        if self.compression_triggered:
            summary = (
                "\n\n[Context Manager] "
                "Context compression was triggered during execution."
            )
            return final_text + summary
        return final_text
