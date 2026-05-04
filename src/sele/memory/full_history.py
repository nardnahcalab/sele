"""Trivial memory that keeps every message verbatim."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sele.types import Message

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sele.config import MemoryConfig
    from sele.interfaces import ModelAdapter


class FullHistoryMemory:
    """Append-only history. Suitable for short tasks; doesn't compact.

    Accepts the same ``(config, *, adapter=...)`` shape as other memory
    implementations for builder uniformity, but ignores both — there's
    nothing to configure and nothing to call.
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,  # noqa: ARG002
        *,
        adapter: ModelAdapter | None = None,  # noqa: ARG002
        **_: Any,
    ) -> None:
        self._messages: list[Message] = []

    def append(self, message: Message) -> None:
        self._messages.append(message)

    def extend(self, messages: list[Message]) -> None:
        self._messages.extend(messages)

    def view(self) -> list[Message]:
        return list(self._messages)
