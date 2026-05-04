"""Tests for ``SummarizeMemory``.

A scripted ``ModelAdapter`` substitutes for a real model so we can assert
on what the summarizer is asked to produce, when it's called, and how
its output is integrated.
"""

from __future__ import annotations

from sele.config import MemoryConfig
from sele.memory.summarize import SummarizeMemory, render_transcript
from sele.types import Message, ModelResponse, ToolCall


class _MockAdapter:
    """Captures the messages sent for summarization and returns canned output."""

    def __init__(self, summary: str = "[summary]") -> None:
        self.calls: list[list[Message]] = []
        self._summary = summary

    def queue(self, summary: str) -> None:
        self._summary = summary

    def complete(self, messages, tools, *, tool_choice=None):  # noqa: ARG002
        self.calls.append(list(messages))
        return ModelResponse(content=self._summary)


def _make(adapter=None, **cfg) -> tuple[SummarizeMemory, _MockAdapter | None]:
    cfg.setdefault("kind", "summarize")
    mc = MemoryConfig(**cfg)
    a = adapter if adapter is not None else _MockAdapter()
    mem = SummarizeMemory(mc, adapter=a)
    return mem, (a if isinstance(a, _MockAdapter) else None)


def _u(content: str) -> Message:
    return Message(role="user", content=content)


def _a(content: str) -> Message:
    return Message(role="assistant", content=content)


def _sys(content: str) -> Message:
    return Message(role="system", content=content)


# --------------------------------------------------------------- under trigger


def test_under_trigger_no_compaction() -> None:
    mem, adapter = _make(trigger_chars=10_000, recent_chars=5_000)
    mem.append(_sys("be brief"))
    mem.append(_u("x" * 100))
    mem.append(_a("y" * 100))
    assert len(mem.view()) == 3
    assert adapter is not None and adapter.calls == []


# --------------------------------------------------------------- compaction


def test_above_trigger_compacts_and_keeps_system_plus_summary_plus_recent() -> None:
    mem, adapter = _make(trigger_chars=500, recent_chars=200)
    assert adapter is not None
    adapter.queue("SHORT_SUMMARY_TEXT")

    mem.append(_sys("be brief"))
    for _ in range(8):
        mem.append(_u("x" * 80))
        mem.append(_a("y" * 80))

    view = mem.view()
    # Original system at index 0, intact.
    assert view[0].role == "system" and view[0].content == "be brief"
    # Inserted summary at index 1.
    assert view[1].role == "system"
    assert "SHORT_SUMMARY_TEXT" in view[1].content
    # Recent block respects the budget (within the size of the last single message).
    recent_chars = sum(len(m.content) for m in view[2:])
    assert recent_chars <= 200 + 80  # tolerance for the trailing single message
    # Adapter called at least once for the compaction.
    assert len(adapter.calls) >= 1


def test_summarizer_receives_prompt_and_transcript() -> None:
    mem, adapter = _make(
        trigger_chars=400, recent_chars=100, prompt="MY_CUSTOM_PROMPT budget={budget}"
    )
    assert adapter is not None
    for _ in range(20):
        mem.append(_u("X" * 50))

    assert adapter.calls
    request = adapter.calls[0]
    # First request message is the system prompt with budget interpolated.
    assert request[0].role == "system"
    assert "MY_CUSTOM_PROMPT" in request[0].content
    assert "budget=100" in request[0].content
    # Second request message is the rendered transcript of the older turns.
    assert request[1].role == "user"
    assert "USER:" in request[1].content


def test_compaction_does_not_thrash_after_summary_fits() -> None:
    mem, adapter = _make(trigger_chars=500, recent_chars=200)
    assert adapter is not None
    adapter.queue("tiny")
    for _ in range(20):
        mem.append(_u("x" * 50))
    n_after_first = len(adapter.calls)

    # A few small additions afterward should not retrigger compaction.
    for _ in range(3):
        mem.append(_u("y" * 5))
    assert len(adapter.calls) == n_after_first


def test_recent_chars_capped_when_larger_than_trigger() -> None:
    # Defensive: misconfiguration shouldn't turn off compaction entirely.
    mem, _ = _make(trigger_chars=100, recent_chars=500)
    assert mem.recent_chars <= mem.trigger_chars


# --------------------------------------------------------------- tool pair


def test_boundary_does_not_split_tool_call_pair() -> None:
    mem, adapter = _make(trigger_chars=300, recent_chars=120)
    assert adapter is not None
    adapter.queue("SUM")

    mem.append(_sys("sys"))
    mem.append(_u("old context " * 10))
    mem.append(_u("more old " * 10))
    mem.append(
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="c1", name="shell", arguments={"command": "ls"})],
        )
    )
    mem.append(Message(role="tool", content="files: a b c", tool_call_id="c1", name="shell"))
    mem.append(_a("done"))

    view = mem.view()
    # Walk through view; whenever we see a tool message, it must be preceded by
    # an assistant message that issued a matching tool_call_id.
    for idx, m in enumerate(view):
        if m.role != "tool":
            continue
        assert idx > 0, "tool message at index 0"
        prev = view[idx - 1]
        assert prev.role == "assistant", f"tool message follows {prev.role!r}, not assistant"
        ids = {tc.id for tc in prev.tool_calls}
        assert m.tool_call_id in ids


# --------------------------------------------------------------- no adapter


def test_no_adapter_falls_back_to_truncation_with_notice() -> None:
    cfg = MemoryConfig(kind="summarize", trigger_chars=200, recent_chars=80)
    mem = SummarizeMemory(cfg, adapter=None)

    mem.append(_sys("sys"))
    for _ in range(20):
        mem.append(_u("x" * 50))

    view = mem.view()
    assert view[0].role == "system" and view[0].content == "sys"
    assert any("truncated" in m.content for m in view[1:3])


# --------------------------------------------------------------- summarizer error


def test_summarizer_exception_does_not_crash() -> None:
    class _BoomAdapter:
        def complete(self, messages, tools, *, tool_choice=None):  # noqa: ARG002
            raise RuntimeError("upstream down")

    cfg = MemoryConfig(kind="summarize", trigger_chars=200, recent_chars=80)
    mem = SummarizeMemory(cfg, adapter=_BoomAdapter())
    mem.append(_sys("sys"))
    for _ in range(20):
        mem.append(_u("x" * 50))

    view = mem.view()
    # The placeholder message should embed the error so it's visible in traces.
    assert any("summarizer error" in m.content for m in view[:3])


# --------------------------------------------------------------- transcript helper


def test_render_transcript_handles_tool_calls_and_tool_results() -> None:
    msgs = [
        _u("hi"),
        Message(
            role="assistant",
            content="planning",
            tool_calls=[ToolCall(id="c1", name="shell", arguments={"command": "ls"})],
        ),
        Message(role="tool", content='{"ok": true}', tool_call_id="c1", name="shell"),
        _a("done"),
    ]
    out = render_transcript(msgs)
    assert "USER: hi" in out
    assert "ASSISTANT (called: shell" in out
    assert "[TOOL shell ->" in out
    assert "ASSISTANT: done" in out


# --------------------------------------------------------------- builder integration


def test_builder_wires_adapter_into_summarize_memory(tmp_path) -> None:
    """The builder should pass the agent's adapter into SummarizeMemory."""

    import yaml

    import sele  # noqa: F401 - ensure entry points loaded
    from sele.builder import build_loop
    from sele.config import load_profile
    from sele.registry import REGISTRY
    from sele.types import ModelResponse

    # Register a scripted adapter under a name unique to this test.
    class _CountingAdapter:
        instances: list[_CountingAdapter] = []  # noqa: F821

        def __init__(self, config) -> None:  # noqa: ARG002
            type(self).instances.append(self)
            self.responses = [ModelResponse(content="(done)")]

        def complete(self, messages, tools, *, tool_choice=None):  # noqa: ARG002
            return self.responses[0]

    REGISTRY.register("adapters", "test_counting", _CountingAdapter)

    profile = {
        "name": "t",
        "model": {"adapter": "test_counting", "model": "x"},
        "protocol": "native_tools",
        "loop": {"kind": "tool_loop", "max_steps": 1},
        "memory": {"kind": "summarize", "trigger_chars": 999_999, "recent_chars": 100},
        "sandbox": {"kind": "host_direct", "cwd": str(tmp_path)},
        "approval": "auto",
        "tools": [],
        "tracer": "null",
        "system_prompt": "x",
    }
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(profile))

    loop = build_loop(load_profile(str(path)))
    # The memory's adapter should be the same instance the loop uses.
    assert loop.ctx.memory._adapter is loop.ctx.adapter  # type: ignore[attr-defined]
