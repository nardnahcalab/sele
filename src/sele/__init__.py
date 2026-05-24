"""sele — a pluggable agent harness for open-source models."""

from sele.interfaces import Skill
from sele.registry import (
    adapter,
    approval,
    loop,
    memory,
    protocol,
    sandbox,
    skill,
    tool,
    tracer,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "adapter",
    "approval",
    "loop",
    "memory",
    "protocol",
    "sandbox",
    "skill",
    "tool",
    "tracer",
    "Skill",
]
