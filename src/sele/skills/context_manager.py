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

import logging
from typing import TYPE_CHECKING

from sele.skills.base import BaseSkill
from sele.types import Message

if TYPE_CHECKING:
    from sele.interfaces import Memory
    from sele.loops.base import LoopContext
    from sele.types import ModelResponse, ToolResult

logger = logging.getLogger(__name__)


class ContextManagerSkill(BaseSkill):
    """Skill that manages context window and compression."""

    name = "context_manager"

    def __init__(self):
        self.max_context_chars = 8000
        self.compression_ratio = 0.5
        self.compression_triggered = False
        self.compression_count = 0
        self._memory: Memory | None = None

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize context manager with configuration."""
        self._memory = ctx.memory
        if ctx.skills_config:
            if ctx.skills_config.get("context_window"):
                self.max_context_chars = ctx.skills_config["context_window"]

            settings = ctx.skills_config.get("skill_settings", {}).get("context_manager", {})
            self.max_context_chars = settings.get("max_context_chars", self.max_context_chars)
            self.compression_ratio = settings.get("compression_ratio", self.compression_ratio)

    def _find_trim_index(self, messages: list[Message]) -> int:
        """Find the index where we should start keeping messages.

        Keeps the leading system message(s) and enough recent messages
        to stay within ``max_context_chars * compression_ratio``. Never
        splits a tool-call / tool-result pair.
        """
        target_chars = int(self.max_context_chars * self.compression_ratio)

        # Walk backwards to find how many recent messages fit in budget.
        running = 0
        i = len(messages)
        while i > 1:
            cand = i - 1
            running += len(messages[cand].content)
            if running > target_chars:
                break
            i = cand

        # Don't start the kept window on a tool message (belongs with its
        # preceding assistant turn that issued the call).
        while i < len(messages) and messages[i].role == "tool" and i > 1:
            i -= 1

        return max(1, i)

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Check context size and compress if needed."""
        total_chars = sum(len(m.content) for m in memory)

        if total_chars <= self.max_context_chars:
            return

        self.compression_triggered = True

        # We need a mutable handle on the memory's internal list.
        mem = self._memory
        if mem is None:
            return
        internal: list[Message] | None = getattr(mem, "_messages", None)
        if internal is None:
            return

        trim_idx = self._find_trim_index(internal)
        dropped = trim_idx - 1  # -1 because index 0 is the system prompt

        if dropped <= 0:
            return

        # Keep the system prompt, insert a notice, then the recent window.
        system = internal[:1] if internal[0].role == "system" else []
        notice = Message(
            role="system",
            content=f"[context manager: {dropped} older message(s) trimmed to fit context window]",
        )
        internal[:] = [*system, notice, *internal[trim_idx:]]
        self.compression_count += 1
        logger.info(
            "context_manager: trimmed %d messages at step %d (total was %d chars)",
            dropped, step_index, total_chars,
        )

    def after_step(
        self, step_index: int, response: ModelResponse, tool_results: list[ToolResult]
    ) -> None:
        """Monitor context usage after each step."""
        pass

    def on_loop_end(self, final_text: str, total_steps: int) -> str:
        """Report on context management."""
        if self.compression_triggered:
            summary = (
                f"\n\n[Context Manager] "
                f"Context compression was triggered {self.compression_count} time(s) during execution."
            )
            return final_text + summary
        return final_text
