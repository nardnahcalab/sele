"""No-op tracer."""

from __future__ import annotations

from sele.types import Step


class NullTracer:
    run_id = "null"

    def __init__(self, config: object = None, **_: object) -> None:  # noqa: ARG002
        pass

    def start(self, profile_name: str, task: str) -> None:  # noqa: ARG002
        pass

    def step(self, step: Step) -> None:  # noqa: ARG002
        pass

    def end(self, status: str, message: str | None = None) -> None:  # noqa: ARG002
        pass
