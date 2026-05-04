"""Shared agent-loop machinery.

A loop owns a ModelAdapter, a ToolProtocol, a Memory, a Sandbox, an
ApprovalPolicy, a tool registry, and a Tracer. Concrete loops differ only
in the outer reasoning strategy (plain tool-loop, plan-then-execute, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sele.interfaces import (
    ApprovalPolicy,
    Memory,
    ModelAdapter,
    Sandbox,
    Tool,
    ToolProtocol,
    Tracer,
)
from sele.types import (
    Message,
    ModelResponse,
    Step,
    ToolCall,
    ToolResult,
    ToolSpec,
)


@dataclass
class LoopContext:
    adapter: ModelAdapter
    protocol: ToolProtocol
    memory: Memory
    sandbox: Sandbox
    approval: ApprovalPolicy
    tools: dict[str, Tool]
    tracer: Tracer
    system_prompt: str
    max_steps: int = 25

    @property
    def tool_specs(self) -> list[ToolSpec]:
        return [t.spec for t in self.tools.values()]


class LoopBase:
    """Base class providing the per-step execution helpers used by concrete
    loops. Not registered as a strategy itself."""

    def __init__(self, ctx: LoopContext):
        self.ctx = ctx
        self._step_index = 0
        self._seeded = False

    # ------------------------------------------------------------------ setup

    def _seed_system(self) -> None:
        if self._seeded:
            return
        rendered = self.ctx.protocol.render_system(self.ctx.system_prompt, self.ctx.tool_specs)
        self.ctx.memory.append(Message(role="system", content=rendered))
        self._seeded = True

    def add_user(self, content: str) -> None:
        self._seed_system()
        self.ctx.memory.append(Message(role="user", content=content))

    # ------------------------------------------------------------------ step

    def _call_model(self) -> tuple[ModelResponse, Step]:
        messages, tools = self.ctx.protocol.prepare_request(
            self.ctx.memory.view(), self.ctx.tool_specs
        )
        response = self.ctx.adapter.complete(messages, tools)
        step = Step(index=self._step_index, messages_in=messages, response=response)
        return response, step

    def _execute_tool_calls(self, calls: list[ToolCall]) -> list[ToolResult]:
        results: list[ToolResult] = []
        for call in calls:
            tool = self.ctx.tools.get(call.name)
            if tool is None:
                results.append(
                    ToolResult(
                        call_id=call.id,
                        name=call.name,
                        ok=False,
                        content="",
                        error=f"unknown tool: {call.name!r}",
                    )
                )
                continue
            if not self.ctx.approval.check(tool.spec, call.arguments):
                results.append(
                    ToolResult(
                        call_id=call.id,
                        name=call.name,
                        ok=False,
                        content="",
                        error="denied by approval policy",
                    )
                )
                continue
            try:
                results.append(tool(self.ctx.sandbox, call.arguments))
            except Exception as exc:  # noqa: BLE001 - tool errors must not crash the loop
                results.append(
                    ToolResult(
                        call_id=call.id,
                        name=call.name,
                        ok=False,
                        content="",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results

    @staticmethod
    def _result_to_message(result: ToolResult) -> Message:
        body: dict[str, Any] = {"ok": result.ok}
        if result.error:
            body["error"] = result.error
        if result.content:
            body["content"] = result.content
        return Message(
            role="tool",
            content=json.dumps(body),
            tool_call_id=result.call_id,
            name=result.name,
        )

    def _record_assistant(self, content: str, calls: list[ToolCall]) -> None:
        self.ctx.memory.append(Message(role="assistant", content=content, tool_calls=calls))

    def _record_tool_results(self, results: list[ToolResult]) -> None:
        self.ctx.memory.extend([self._result_to_message(r) for r in results])

    def step_once(self) -> tuple[str, list[ToolCall], list[ToolResult]]:
        """Run one model turn. Returns (assistant_text, calls, results).
        If ``calls`` is empty, the loop should terminate."""

        response, step = self._call_model()
        text, calls = self.ctx.protocol.parse_response(response)
        self._record_assistant(text, calls)

        results = self._execute_tool_calls(calls) if calls else []
        if results:
            self._record_tool_results(results)
            step.tool_results = results

        self.ctx.tracer.step(step)
        self._step_index += 1
        return text, calls, results
