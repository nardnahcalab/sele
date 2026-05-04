"""Trivial memory that keeps every message verbatim."""

from __future__ import annotations

from sele.types import Message


class FullHistoryMemory:
    """Append-only history. Suitable for short tasks; doesn't compact."""

    def __init__(self, **_: object) -> None:
        self._messages: list[Message] = []

    def append(self, message: Message) -> None:
        self._messages.append(message)

    def extend(self, messages: list[Message]) -> None:
        self._messages.extend(messages)

    def view(self) -> list[Message]:
        return list(self._messages)
