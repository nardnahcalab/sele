"""Plain tool-use loop.

Repeats: model speaks -> tools run -> model speaks. Terminates when the
model returns no tool calls, or when ``max_steps`` is exhausted.
"""

from __future__ import annotations

from sele.loops.base import LoopBase, LoopContext


class ToolLoop(LoopBase):
    """Simple tool-use loop strategy."""

    name = "tool_loop"

    def __init__(self, ctx: LoopContext):
        super().__init__(ctx)

    def run(self, task: str) -> str:
        self.add_user(task)
        last_text = ""
        for _ in range(self.ctx.max_steps):
            text, calls, _ = self.step_once()
            last_text = text or last_text
            if not calls:
                return last_text
        return last_text or "(max steps reached)"
