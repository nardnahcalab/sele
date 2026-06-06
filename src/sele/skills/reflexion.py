"""Reflexion skill: Enables self-reflection and iterative improvement.

This skill implements a reflexion loop where the agent can evaluate its progress
and adjust its strategy. It works by:

1. Tracking progress across steps
2. Detecting when progress stalls
3. Injecting reflection prompts to encourage re-planning
4. Tracking the number of reflection iterations

Configuration in profile:
    loop:
      skills:
        enabled: true
        skills: [reflexion]
        skill_settings:
          reflexion:
            reflection_threshold: 3  # Trigger reflection after N steps without progress
            max_reflections: 2  # Max reflection cycles
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sele.skills.base import BaseSkill
from sele.types import Message

if TYPE_CHECKING:
    from sele.interfaces import Memory
    from sele.loops.base import LoopContext
    from sele.types import ModelResponse, ToolResult


class ReflexionSkill(BaseSkill):
    """Skill that enables self-reflection and iterative improvement."""

    name = "reflexion"

    def __init__(self):
        self.reflection_threshold = 3
        self.max_reflections = 2
        self.reflection_count = 0
        self.last_reflection_step = -1
        self.steps_since_progress = 0
        self.last_response_length = 0
        self._memory: Memory | None = None

    def initialize(self, ctx: LoopContext) -> None:
        """Initialize reflexion skill with configuration."""
        self._memory = ctx.memory
        if ctx.skills_config and "skill_settings" in ctx.skills_config:
            settings = ctx.skills_config["skill_settings"].get("reflexion", {})
            if settings:
                self.reflection_threshold = settings.get("reflection_threshold", 3)
                self.max_reflections = settings.get("max_reflections", 2)

    def before_step(self, step_index: int, memory: list[Message]) -> None:
        """Check if reflection is needed before the step."""
        # Check if we should trigger reflection
        if (
            self.reflection_count < self.max_reflections
            and step_index - self.last_reflection_step >= self.reflection_threshold
            and self.steps_since_progress >= self.reflection_threshold
        ):
            # Inject reflection prompt
            reflection_prompt = (
                "[Reflection] You've been working on this task for a while. "
                "Take a moment to reflect on your progress so far:\n"
                "1. What have you accomplished?\n"
                "2. What challenges have you encountered?\n"
                "3. What should you try next?\n"
                "Then continue with your plan."
            )
            if self._memory is not None:
                self._memory.append(Message(role="user", content=reflection_prompt))
            self.reflection_count += 1
            self.last_reflection_step = step_index

    def after_step(
        self, step_index: int, response: ModelResponse, tool_results: list[ToolResult]
    ) -> None:
        """Track progress after each step."""
        # Track if we made progress (response length as a proxy)
        current_response_length = len(response.content)

        if current_response_length > self.last_response_length:
            self.steps_since_progress = 0
            self.last_response_length = current_response_length
        else:
            self.steps_since_progress += 1

    def on_loop_end(self, final_text: str, total_steps: int) -> str:
        """Post-process output with reflection summary."""
        if self.reflection_count > 0:
            summary = (
                f"\n\n[Reflexion Summary] "
                f"Completed in {total_steps} steps with {self.reflection_count} reflection(s)."
            )
            return final_text + summary
        return final_text
