"""Plan-then-execute loop.

Two phases:

1. **Plan** — ask the model for a numbered plan, no tool calls. The plan is
   recorded in memory as the assistant's first turn after the user task.
2. **Execute** — run a normal tool-loop. The plan stays in context so the
   model can refer to and revise it.

Useful for slightly longer-horizon tasks. Same termination conditions as
``ToolLoop``.
"""

from __future__ import annotations

from sele.loops.base import LoopBase, LoopContext
from sele.types import Message

PLAN_TEMPLATE = (
    "Before you take any action, write a short numbered plan for the task "
    "below. Do NOT call any tools yet. Keep it to 3-7 concrete steps.\n\n"
    "Task:\n{task}"
)

EXECUTE_NUDGE = (
    "Now execute your plan, calling tools as needed. Revise the plan if "
    "you discover new information."
)


class PlanExecuteLoop(LoopBase):
    """Plan-then-execute strategy."""

    name = "plan_execute"

    def __init__(self, ctx: LoopContext):
        super().__init__(ctx)

    def _plan(self, task: str) -> str:
        self._seed_system()
        self.ctx.memory.append(Message(role="user", content=PLAN_TEMPLATE.format(task=task)))
        text, _, _ = self.step_once()
        return text

    def run(self, task: str) -> str:
        self._plan(task)
        self.ctx.memory.append(Message(role="user", content=EXECUTE_NUDGE))

        last_text = ""
        for _ in range(self.ctx.max_steps):
            text, calls, _ = self.step_once()
            last_text = text or last_text
            if not calls:
                return self._finalize(last_text)
        return self._finalize(last_text or "(max steps reached)")
