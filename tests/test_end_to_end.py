"""End-to-end smoke test using a mock model adapter.

Exercises: registry, builder, profile loading, ToolLoop, native_tools
protocol, host_direct sandbox, fs_write tool, jsonl tracer.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

import sele  # noqa: F401 - ensure decorators register
from sele.builder import build_loop
from sele.config import load_profile
from sele.registry import REGISTRY
from sele.types import ModelResponse, ToolCall


class _ScriptedAdapter:
    """ModelAdapter that returns a pre-baked sequence of responses."""

    def __init__(self, config):  # noqa: ARG002 - signature compat
        self._responses: list[ModelResponse] = list(_ScriptedAdapter._SCRIPT)

    @classmethod
    def script(cls, responses: list[ModelResponse]) -> None:
        cls._SCRIPT = list(responses)

    _SCRIPT: list[ModelResponse] = []

    def complete(self, messages, tools, *, tool_choice=None):  # noqa: ARG002
        if not self._responses:
            return ModelResponse(content="(done)")
        return self._responses.pop(0)


def _write_profile(tmp_path: Path, **overrides) -> Path:
    profile = {
        "name": "test",
        "model": {"adapter": "mock_scripted", "model": "mock"},
        "protocol": "native_tools",
        "loop": {"kind": "tool_loop", "max_steps": 5},
        "memory": "full_history",
        "sandbox": {"kind": "host_direct", "cwd": str(tmp_path)},
        "approval": "auto",
        "tools": ["fs_write", "fs_read"],
        "tracer": {"kind": "jsonl", "dir": str(tmp_path / ".runs")},
        "system_prompt": "Be brief.",
    }
    profile.update(overrides)
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(profile))
    return path


def test_loop_runs_tools_and_writes_trace(tmp_path: Path) -> None:
    REGISTRY.register("adapters", "mock_scripted", _ScriptedAdapter)
    _ScriptedAdapter.script([
        ModelResponse(
            content="",
            tool_calls=[ToolCall(id="c1", name="fs_write",
                                 arguments={"path": "out.txt", "content": "hello sele"})],
        ),
        ModelResponse(content="done."),
    ])

    profile_path = _write_profile(tmp_path)
    loop = build_loop(load_profile(str(profile_path)))
    loop.ctx.tracer.start("test", "write a file")
    result = loop.run("write a file containing 'hello sele' at out.txt")
    loop.ctx.tracer.end("ok")

    # Tool actually wrote.
    assert (tmp_path / "out.txt").read_text() == "hello sele"

    # Final assistant text reached us.
    assert result == "done."

    # Trace file exists and has start/step/end events.
    trace_files = list((tmp_path / ".runs").glob("*.jsonl"))
    assert len(trace_files) == 1
    events = [json.loads(line) for line in trace_files[0].read_text().splitlines() if line.strip()]
    kinds = [e["kind"] for e in events]
    assert kinds[0] == "start" and kinds[-1] == "end"
    assert "step" in kinds


def test_react_text_protocol_parses_tool_blocks() -> None:
    from sele.protocols.react_text import ReActTextProtocol

    proto = ReActTextProtocol()
    response = ModelResponse(
        content=(
            "I'll list the files.\n\n"
            "```tool\n{\"name\": \"shell\", \"arguments\": {\"command\": \"ls\"}}\n```\n"
        )
    )
    text, calls = proto.parse_response(response)
    assert "list the files" in text
    assert len(calls) == 1
    assert calls[0].name == "shell"
    assert calls[0].arguments == {"command": "ls"}


def test_react_final_block_terminates() -> None:
    from sele.protocols.react_text import ReActTextProtocol

    proto = ReActTextProtocol()
    response = ModelResponse(content="```final\nthe answer is 42\n```")
    text, calls = proto.parse_response(response)
    assert text == "the answer is 42"
    assert calls == []


def test_sandbox_rejects_path_escape(tmp_path: Path) -> None:
    from sele.config import SandboxConfig
    from sele.sandbox.host_direct import HostDirectSandbox

    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    try:
        sandbox.resolve("../../etc/passwd")
    except PermissionError:
        return
    raise AssertionError("expected PermissionError for path escape")
