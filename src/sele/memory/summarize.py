"""Summarize-old-turns memory.

Keeps the original system message and a sliding window of recent turns
verbatim. When the total message content exceeds ``trigger_chars``, the
older portion is condensed by calling a ``ModelAdapter`` (typically the
agent's own adapter) to produce a brief factual summary, which replaces
the older messages as a single inserted message.

Boundaries are chosen so a tool-call → tool-result run never straddles
the recent/older split — splitting them would corrupt the chat protocol
on backends that enforce it (OpenAI rejects tool messages that don't
follow a matching ``assistant`` turn with the right ``tool_call_id``).

Why summarize instead of just truncating: agents discover key facts
mid-task (file contents, error messages, IDs). Truncation throws those
away; summarization preserves the gist.

Honest tradeoffs:
- Char-based budget, not token-based. A ``chars_per_token ≈ 4`` proxy is
  fine for budgeting against a context window; for tight budgets,
  configure conservatively. A pluggable token counter can replace this
  later without changing the public API.
- Each compaction is one model call. Set ``trigger_chars`` so this
  doesn't fire too often.
- Default ``summary_role`` is ``system``. Most ``openai_compat`` backends
  accept multiple system messages. Some models behave better with the
  summary as a prior assistant turn — set ``summary_role: assistant`` in
  the profile to switch.
- If no adapter is wired in (e.g., in tests, or by a third-party builder
  variant), compaction falls back to truncation with a placeholder
  message rather than raising.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sele.config import MemoryConfig
from sele.types import Message

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sele.interfaces import ModelAdapter


DEFAULT_SUMMARIZER_PROMPT = """\
You are summarizing the EARLIER portion of an autonomous agent's
conversation so the agent can continue with limited context. The agent
will only see your summary plus its most recent turns, so the summary
must capture every fact the agent might still need.

Produce a concise, factual summary that:
- States what the user asked for and the high-level plan.
- Lists key facts discovered: filenames, file contents (excerpts ok),
  command outputs, error messages, configuration values, IDs.
- Notes which subtasks are complete and which remain.
- Preserves any decisions made and any constraints you've inferred.

Do NOT speculate or invent. Use bullet points for lists.
Keep the summary under {budget} characters.
"""


def render_transcript(messages: list[Message]) -> str:
    """Format messages as a plain-text transcript for the summarizer."""

    lines: list[str] = []
    for m in messages:
        if m.role == "tool":
            lines.append(f"[TOOL {m.name or '?'} -> {m.content}]")
        elif m.role == "assistant":
            if m.tool_calls:
                calls = "; ".join(f"{tc.name}({tc.arguments})" for tc in m.tool_calls)
                lines.append(f"ASSISTANT (called: {calls})")
                if m.content:
                    lines.append(f"  {m.content}")
            else:
                lines.append(f"ASSISTANT: {m.content}")
        else:
            lines.append(f"{m.role.upper()}: {m.content}")
    return "\n".join(lines)


class SummarizeMemory:
    """Memory that compacts old turns into a model-generated summary."""

    def __init__(
        self,
        config: MemoryConfig | None = None,
        *,
        adapter: ModelAdapter | None = None,
    ) -> None:
        self._messages: list[Message] = []
        self._adapter = adapter
        cfg = config or MemoryConfig(kind="summarize")
        self.trigger_chars: int = int(cfg.trigger_chars)
        self.recent_chars: int = int(cfg.recent_chars)
        self.prompt_template: str = cfg.prompt or DEFAULT_SUMMARIZER_PROMPT
        self.summary_role: str = cfg.summary_role or "system"
        if self.recent_chars > self.trigger_chars:
            # Defensive: a recent budget bigger than the trigger means we'd
            # never compact. Cap it.
            self.recent_chars = max(1, self.trigger_chars // 2)

    # ------------------------------------------------------------------ public

    def append(self, message: Message) -> None:
        self._messages.append(message)
        self._compact_if_needed()

    def extend(self, messages: list[Message]) -> None:
        self._messages.extend(messages)
        self._compact_if_needed()

    def view(self) -> list[Message]:
        return list(self._messages)

    # ------------------------------------------------------------------ internals

    def _total_chars(self) -> int:
        return sum(len(m.content) for m in self._messages)

    def _compact_if_needed(self) -> None:
        if self._total_chars() <= self.trigger_chars:
            return
        if self._adapter is None:
            self._fallback_truncate()
            return
        self._compact()

    def _safe_split_index(self) -> int:
        """Return ``i`` such that ``messages[:i]`` is "older" (to be
        summarized) and ``messages[i:]`` is "recent" (kept verbatim).

        Guarantees:
          - ``i >= 1`` so any leading ``system`` message is preserved.
          - ``messages[i]`` is never a ``tool`` message — if it would be,
            we walk back to include the ``assistant`` turn that issued
            those tool calls.
          - ``sum(chars in messages[i:]) <= recent_chars`` (best-effort;
            a single oversize message can blow this).
        """

        msgs = self._messages
        if len(msgs) <= 2:
            return 1

        running = 0
        i = len(msgs)
        while i > 1:
            cand = i - 1
            running += len(msgs[cand].content)
            if running > self.recent_chars:
                break
            i = cand

        # Never start the recent window with a tool message: tool messages
        # only make sense alongside the assistant turn that called them.
        while i < len(msgs) and msgs[i].role == "tool" and i > 1:
            i -= 1

        return max(1, i)

    def _split_for_summary(self) -> tuple[list[Message], list[Message], list[Message]]:
        """Split current messages into ``(kept_system, to_summarize, recent)``.

        ``kept_system`` is the original leading system message if any, kept
        verbatim. ``to_summarize`` is everything older that should be folded
        into a single summary. ``recent`` is the verbatim window."""

        i = self._safe_split_index()
        older = self._messages[:i]
        recent = self._messages[i:]
        if older and older[0].role == "system":
            return older[:1], older[1:], recent
        return [], older, recent

    def _compact(self) -> None:
        kept_system, to_summarize, recent = self._split_for_summary()
        if not to_summarize:
            return
        summary_text = self._call_summarizer(to_summarize)
        summary_msg = Message(
            role=self.summary_role if self.summary_role in {"system", "assistant"} else "system",
            content=f"[summary of earlier turns]\n{summary_text}",
        )
        self._messages = [*kept_system, summary_msg, *recent]

    def _call_summarizer(self, msgs: list[Message]) -> str:
        assert self._adapter is not None
        prompt = self.prompt_template.format(budget=self.recent_chars)
        transcript = render_transcript(msgs)
        request = [
            Message(role="system", content=prompt),
            Message(role="user", content=transcript),
        ]
        try:
            resp = self._adapter.complete(request, tools=[])
        except Exception as exc:  # noqa: BLE001 - never crash the loop on summarizer errors
            return f"(summarizer error: {type(exc).__name__}: {exc})"
        return (resp.content or "").strip() or "(empty summary)"

    def _fallback_truncate(self) -> None:
        kept_system, to_drop, recent = self._split_for_summary()
        if not to_drop:
            return
        notice = Message(
            role="system",
            content=(
                f"[{len(to_drop)} earlier message(s) truncated; "
                "no summarizer adapter configured]"
            ),
        )
        self._messages = [*kept_system, notice, *recent]
