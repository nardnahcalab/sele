"""Plugin registry for sele.

Two ways to register components:

1.  In-tree, via decorators::

        from sele import tool

        @tool("my_tool", description="...")
        def my_tool(...): ...

2.  Out-of-tree, via Python entry points declared in your package's
    ``pyproject.toml``::

        [project.entry-points."sele.tools"]
        my_tool = "my_pkg.module:my_tool"

The ``Registry`` lazily loads entry points on first lookup.
"""

from __future__ import annotations

import importlib.metadata as md
from collections.abc import Callable
from typing import Any

# Entry-point group name -> friendly kind name.
_GROUPS = {
    "tools": "sele.tools",
    "adapters": "sele.adapters",
    "protocols": "sele.protocols",
    "loops": "sele.loops",
    "memory": "sele.memory",
    "sandbox": "sele.sandbox",
    "approval": "sele.approval",
    "tracer": "sele.tracer",
    "skills": "sele.skills",
}


class Registry:
    """Mapping of (kind, name) -> object, populated lazily."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {k: {} for k in _GROUPS}
        self._loaded: set[str] = set()

    def register(self, kind: str, name: str, obj: Any) -> None:
        if kind not in self._items:
            raise ValueError(f"unknown kind: {kind!r}")
        self._items[kind][name] = obj

    def _load_entry_points(self, kind: str) -> None:
        if kind in self._loaded:
            return
        self._loaded.add(kind)
        group = _GROUPS[kind]
        try:
            eps = md.entry_points(group=group)
        except TypeError:  # pragma: no cover - older importlib
            eps = md.entry_points().get(group, [])  # type: ignore[attr-defined]
        for ep in eps:
            if ep.name in self._items[kind]:
                continue
            try:
                self._items[kind][ep.name] = ep.load()
            except Exception as exc:  # noqa: BLE001 - surface plugin errors loudly
                raise RuntimeError(
                    f"failed loading entry point {group}:{ep.name} -> {ep.value}: {exc}"
                ) from exc

    def get(self, kind: str, name: str) -> Any:
        if kind not in self._items:
            raise ValueError(f"unknown kind: {kind!r}")
        self._load_entry_points(kind)
        try:
            return self._items[kind][name]
        except KeyError as exc:
            available = ", ".join(sorted(self._items[kind])) or "<none>"
            raise KeyError(
                f"no {kind} registered as {name!r}. available: {available}"
            ) from exc

    def list(self, kind: str) -> list[str]:
        if kind not in self._items:
            raise ValueError(f"unknown kind: {kind!r}")
        self._load_entry_points(kind)
        return sorted(self._items[kind])


REGISTRY = Registry()


def _decorator(kind: str) -> Callable[..., Callable[[Any], Any]]:
    def factory(name: str, **_: Any) -> Callable[[Any], Any]:
        def wrap(obj: Any) -> Any:
            REGISTRY.register(kind, name, obj)
            return obj

        return wrap

    return factory


tool = _decorator("tools")
adapter = _decorator("adapters")
protocol = _decorator("protocols")
loop = _decorator("loops")
memory = _decorator("memory")
sandbox = _decorator("sandbox")
approval = _decorator("approval")
tracer = _decorator("tracer")
skill = _decorator("skills")
