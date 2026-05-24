"""Skills that augment the agent loop with specialized reasoning strategies.

Skills can:
- Modify the agent loop strategy (e.g., reflexion, tree search)
- Control context window and compression
- Configure breadth/depth of search
- Provide specialized tools or prompts
"""

from sele.registry import skill
from sele.skills.base import BaseSkill
from sele.skills.context_manager import ContextManagerSkill
from sele.skills.reflexion import ReflexionSkill

# Register built-in skills
skill("reflexion")(ReflexionSkill())
skill("context_manager")(ContextManagerSkill())

__all__ = ["BaseSkill", "ReflexionSkill", "ContextManagerSkill"]
