"""Wire a Profile into a fully-constructed AgentLoop.

This is the only place that knows how to translate string identifiers in a
profile into concrete instances from the registry. Loops, tools, etc.
should never reach into the registry themselves.
"""

from __future__ import annotations

from sele.config import Profile, coerce_tracer_config
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

    memory_cls = REGISTRY.get("memory", profile.memory)
    memory = _instantiate(memory_cls)

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
    )

    loop_cls = REGISTRY.get("loops", profile.loop.kind)
    return loop_cls(ctx)
