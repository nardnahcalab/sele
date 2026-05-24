"""Wire a Profile into a fully-constructed AgentLoop.

This is the only place that knows how to translate string identifiers in a
profile into concrete instances from the registry. Loops, tools, etc.
should never reach into the registry themselves.
"""

from __future__ import annotations

from sele.config import Profile, coerce_memory_config, coerce_tracer_config
from sele.interfaces import AgentLoop
from sele.loops.base import LoopContext
from sele.registry import REGISTRY


def _instantiate(obj, *args, **kwargs):
    """Call ``obj(*args, **kwargs)`` if it's a class, else return as-is.

    Tools are typically singletons exposed as already-instantiated objects;
    adapters/loops/etc. are classes. Either is fine."""

    if isinstance(obj, type):
        return obj(*args, **kwargs)
    return obj


def build_loop(profile: Profile) -> AgentLoop:
    adapter_cls = REGISTRY.get("adapters", profile.model.adapter)
    adapter = _instantiate(adapter_cls, profile.model)

    protocol_cls = REGISTRY.get("protocols", profile.protocol)
    protocol = _instantiate(protocol_cls)

    memory_cfg = coerce_memory_config(profile.memory)
    memory_cls = REGISTRY.get("memory", memory_cfg.kind)
    memory = _instantiate(memory_cls, memory_cfg, adapter=adapter)

    sandbox_cls = REGISTRY.get("sandbox", profile.sandbox.kind)
    sandbox = _instantiate(sandbox_cls, profile.sandbox)

    approval_cls = REGISTRY.get("approval", profile.approval)
    approval = _instantiate(approval_cls)

    tools = {}
    for tool_name in profile.tools:
        tool_obj = REGISTRY.get("tools", tool_name)
        tools[tool_name] = _instantiate(tool_obj)

    tracer_cfg = coerce_tracer_config(profile.tracer)
    tracer_cls = REGISTRY.get("tracer", tracer_cfg.kind)
    tracer = _instantiate(tracer_cls, tracer_cfg)

    # Build skills if enabled
    skills = None
    skills_config = None
    if profile.loop.skills.enabled and profile.loop.skills.skills:
        skills = []
        for skill_name in profile.loop.skills.skills:
            skill_obj = REGISTRY.get("skills", skill_name)
            skills.append(_instantiate(skill_obj))
        
        # Prepare skills configuration
        skills_config = {
            "breadth": profile.loop.skills.breadth,
            "depth": profile.loop.skills.depth,
            "context_window": profile.loop.skills.context_window,
            "context_compression": profile.loop.skills.context_compression,
            "loop_strategy": profile.loop.skills.loop_strategy,
            "skill_settings": profile.loop.skills.skill_settings,
        }

    # Determine loop kind (can be overridden by skills)
    loop_kind = profile.loop.kind
    if skills_config and skills_config.get("loop_strategy"):
        loop_kind = skills_config["loop_strategy"]

    ctx = LoopContext(
        adapter=adapter,
        protocol=protocol,
        memory=memory,
        sandbox=sandbox,
        approval=approval,
        tools=tools,
        tracer=tracer,
        system_prompt=profile.system_prompt,
        max_steps=profile.loop.max_steps,
        skills=skills,
        skills_config=skills_config,
    )

    loop_cls = REGISTRY.get("loops", loop_kind)
    loop = loop_cls(ctx)
    
    # Initialize skills after loop creation
    if hasattr(loop, "_initialize_skills"):
        loop._initialize_skills()
    
    return loop
