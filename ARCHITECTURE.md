# sele Architecture

This document describes the system architecture of sele, a pluggable agent harness for open-source language models.

## Overview

sele is designed as a thin coordinator over a set of pluggable surfaces. Every component that the agent needs to function — the model backend, tool-calling protocol, agent loop strategy, memory management, sandbox isolation, approval policy, tools, and tracing — is swappable via a YAML profile.

```
┌─────────────────────────────────────────────────────────────────┐
│                        YAML Profile                              │
│  (model, protocol, loop, memory, sandbox, approval, tools, tracer)│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Builder                                  │
│  - Resolves implementations from registry                       │
│  - Instantiates concrete classes                               │
│  - Wires dependencies together                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LoopContext                                 │
│  { ModelAdapter · ToolProtocol · AgentLoop                      │
│    Memory · Sandbox · Approval · Tools · Tracer }               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Loop                                  │
│  - Drives turns: model → tools → model → ...                    │
│  - Enforces step limits                                         │
│  - Handles errors and interrupts                                │
└─────────────────────────────────────────────────────────────────┘
```

## Pluggable Surfaces

### ModelAdapter

Talks to a model backend. Implementations handle different inference strategies.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `openai_compat` | OpenAI-compatible HTTP API (Ollama, vLLM, OpenRouter, etc.) | ✅ v0.1 |
| `llama_cpp_native` | In-process llama.cpp for GGUF models (no server) | ✅ v0.2 |
| `transformers_native` | Hugging Face transformers in-process | Planned |

**Interface:**
```python
class ModelAdapter(Protocol):
    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse: ...
```

### ToolProtocol

Defines how tools are presented to the model and how its output is parsed back into tool calls.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `native_tools` | OpenAI-style native tool calling (function calling) | ✅ v0.1 |
| `react_text` | ReAct-style text protocol (tool blocks in markdown) | ✅ v0.1 |
| `json_grammar` | Constrained generation via JSON grammars | Planned |
| `xml_tags` | XML-based tool calling | Planned |

**Interface:**
```python
class ToolProtocol(Protocol):
    name: str
    def render_system(self, base: str, tools: list[ToolSpec]) -> str: ...
    def prepare_request(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
    ) -> tuple[list[Message], list[ToolSpec]]: ...
    def parse_response(self, response: ModelResponse) -> tuple[str, list[ToolCall]]: ...
```

### AgentLoop

The outer agent strategy. Drives Memory + ModelAdapter + Tools to a terminal state.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `tool_loop` | Simple loop: model → tools → model until done | ✅ v0.1 |
| `plan_execute` | Plan first, then execute steps | ✅ v0.1 |
| `reflexion` | Self-reflection and correction | ✅ v0.2 |
| `tree_search` | Tree-of-thought search | Planned |

**Interface:**
```python
class AgentLoop(Protocol):
    def run(self, task: str) -> str: ...
```

### Memory

Maintains the message history shown to the model on each step.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `full_history` | Keep all messages verbatim | ✅ v0.1 |
| `summarize` | Fold older turns into summaries when budget exceeded | ✅ v0.2 |
| `sliding_window` | Fixed-size sliding window | Planned |
| `retrieval` | RAG-style retrieval from external store | Planned |

**Interface:**
```python
class Memory(Protocol):
    def append(self, message: Message) -> None: ...
    def extend(self, messages: list[Message]) -> None: ...
    def view(self) -> list[Message]: ...
```

### Sandbox

Execution boundary for tool calls. Provides isolation and resource limits.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `host_direct` | Direct host execution with cwd boundary only | ✅ v0.1 |
| `bubblewrap` | Linux namespaces (PID/IPC/UTS/mount) with egress control | ✅ v0.2 |
| `openshell` | Docker-based sandbox with policy-based network control | ✅ v0.2 |
| `docker` | Docker container isolation | Planned |
| `firejail` | Firejail sandbox (Linux) | Planned |
| `gvisor` | gVisor application sandbox | Planned |

**Interface:**
```python
class Sandbox(Protocol):
    def run_shell(self, command: str, *, timeout: float | None = None) -> tuple[int, str, str]: ...
    def read_file(self, path: str, *, max_bytes: int = 200_000) -> str: ...
    def write_file(self, path: str, content: str) -> int: ...
    def resolve(self, path: str) -> str: ...
```

### ApprovalPolicy

Controls whether tool calls require user confirmation.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `auto` | Allow all tool calls | ✅ v0.1 |
| `confirm_all` | Confirm every tool call | ✅ v0.1 |
| `confirm_destructive` | Confirm only destructive tools (shell, fs_write) | ✅ v0.1 |
| `allowlist` | Allowlist-based policy | Planned |
| `policy_lm` | LLM-based policy decision | Planned |

**Interface:**
```python
class ApprovalPolicy(Protocol):
    def check(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> bool: ...
```

### Tools

Callable functions the agent can invoke.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `shell` | Run bash commands in sandbox | ✅ v0.1 |
| `fs_read` | Read text files in sandbox cwd | ✅ v0.1 |
| `fs_write` | Write text files in sandbox cwd | ✅ v0.1 |
| `python_exec` | Execute Python code in sandbox | ✅ v0.2 |
| `http` | Make HTTP requests from sandbox | ✅ v0.2 |
| `git` | Git operations | Planned |

**Interface:**
```python
class Tool(Protocol):
    spec: ToolSpec
    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult: ...
```

### Tracer

Records execution traces for debugging and analysis.

| Implementation | Description | Status |
|----------------|-------------|--------|
| `jsonl` | JSONL file traces | ✅ v0.1 |
| `console` | Print to console | ✅ v0.1 |
| `null` | No tracing | ✅ v0.1 |
| `otel` | OpenTelemetry integration | Planned |

**Interface:**
```python
class Tracer(Protocol):
    run_id: str
    def start(self, profile_name: str, task: str) -> None: ...
    def step(self, step: Step) -> None: ...
    def end(self, status: str, message: str | None = None) -> None: ...
```

## Data Flow

### Single Turn Execution

```
1. Loop calls ModelAdapter.complete()
   - Input: messages (from Memory), tools (from ToolProtocol)
   - Output: ModelResponse (text + optional tool_calls)

2. If tool_calls present:
   a. ToolProtocol parses tool_calls from response
   b. For each tool_call:
      - ApprovalPolicy checks if allowed
      - Tool.__call__() executes via Sandbox
      - ToolResult returned
      - ToolResult converted to Message(role="tool")
      - Memory.append(tool_message)
   c. ModelResponse text converted to Message(role="assistant")
   d. Memory.append(assistant_message)

3. If no tool_calls:
   - ModelResponse text converted to Message(role="assistant")
   - Memory.append(assistant_message)
   - Loop terminates (or continues based on loop strategy)

4. Tracer records each step
```

### Memory Management

```
Memory.view() → messages shown to model
    │
    ├─ full_history: returns all messages
    └─ summarize:
        ├─ if total chars < trigger_chars: return all messages
        └─ if total chars >= trigger_chars:
            ├─ keep system prompt verbatim
            ├─ summarize older turns via ModelAdapter
            ├─ keep recent window verbatim
            └─ return [system, summary, recent_window]
```

### Sandbox Execution

```
Tool.__call__(sandbox, arguments)
    │
    ├─ shell: sandbox.run_shell(command)
    │   ├─ HostDirectSandbox: subprocess.run(bash -lc command)
    │   ├─ BubblewrapSandbox: subprocess.run(bwrap ... bash -lc command)
    │   └─ OpenShellSandbox: subprocess.run(openshell exec ... bash -lc command)
    │
    ├─ fs_read: sandbox.read_file(path)
    │   └─ Direct file read (in-process, respects cwd boundary)
    │
    ├─ fs_write: sandbox.write_file(path, content)
    │   └─ Direct file write (in-process, respects cwd boundary)
    │
    ├─ python_exec: sandbox.run_shell(python -c code)
    │   └─ Uses shell, respects sandbox isolation
    │
    └─ http: sandbox.run_shell(curl ...)
        └─ Uses shell, respects egress control (proxy in bubblewrap, policy in openshell)
```

## Plugin Development

### In-Tree Plugins

Use decorators for simple in-tree plugins:

```python
from sele import tool
from sele.types import ToolSpec, ToolResult

class _Echo:
    spec = ToolSpec(
        name="echo",
        description="Echo back the input.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    )
    def __call__(self, sandbox, arguments):
        return ToolResult(
            call_id="",
            name="echo",
            ok=True,
            content=arguments.get("text", "")
        )

tool("echo")(_Echo())
```

### Out-of-Tree Plugins

Add entry points in `pyproject.toml`:

```toml
[project.entry-points."sele.tools"]
echo = "my_pkg.tools:echo"

[project.entry-points."sele.adapters"]
my_adapter = "my_pkg.adapters:MyAdapter"

[project.entry-points."sele.protocols"]
my_protocol = "my_pkg.protocols:MyProtocol"
```

The same pattern works for all surface types: `sele.adapters`, `sele.protocols`, `sele.loops`, `sele.memory`, `sele.sandbox`, `sele.approval`, `sele.tracer`.

## Configuration

### Profile Structure

```yaml
name: my-profile
description: My custom profile

model:
  adapter: openai_compat
  base_url: http://localhost:11434/v1
  model: llama3.1:8b
  api_key: ollama
  temperature: 0.2

protocol: native_tools

loop:
  kind: tool_loop
  max_steps: 25

memory:
  kind: summarize
  trigger_chars: 12000
  recent_chars: 6000

sandbox:
  kind: host_direct
  cwd: .
  timeout: 60.0

approval: confirm_destructive

tools: [shell, fs_read, fs_write, python_exec, http]

tracer:
  kind: jsonl
  dir: .sele/runs

system_prompt: |
  You are a careful agent.
```

### Profile Resolution Order

1. Absolute or relative path to YAML file
2. `./.sele/profiles/<name>.yaml`
3. `~/.config/sele/profiles/<name>.yaml`
4. Bundled profile in package (`sele/profiles/<name>.yaml`)

User profiles override bundled profiles with the same name.

## Key Design Decisions

### Protocol-Based Plugins

Uses Python's `Protocol` for interface definitions. This provides:
- Type checking via mypy
- Duck typing compatibility
- Clear contract documentation
- No inheritance required

### Registry Pattern

Singleton registry resolves names to implementations. This enables:
- Runtime plugin discovery
- Profile-based configuration
- Easy testing with mock implementations

### Config Objects

Pydantic models for configuration with `extra="allow"`. This provides:
- Validation and type coercion
- Documentation via docstrings
- Forward compatibility (unknown fields pass through)
- Easy serialization

### Sandbox Separation

File operations (read/write) run in-process; only shell commands go through sandbox. This provides:
- Performance (no subprocess overhead for file ops)
- Simpler error handling
- Clear security boundary (dangerous surface = arbitrary shell commands)
- Progress persistence (cwd bind-mounted in bubblewrap)

### Memory Adapter Wiring

The builder wires the agent's ModelAdapter into Memory implementations. This enables:
- SummarizeMemory to use the same model as the agent
- No separate model configuration needed
- Credential reuse
- Consistent behavior

### Char-Based Budgeting

Memory budgets use character counts, not token counts. This provides:
- Simpler implementation (no tokenizer dependency)
- Good enough proxy (~4 chars/token)
- Pluggable token counter can replace later without API changes

## Security Considerations

### Default Sandbox

`host_direct` provides only a working-directory boundary. It is **not a security sandbox**. Use:
- `--cwd` to confine to scratch directories
- `confirm_destructive` approval policy
- Trace inspection after runs

### Bubblewrap Sandbox

`bubblewrap` provides real Linux isolation:
- Namespaces: PID, IPC, UTS, mount
- Capabilities dropped
- Read-only host binds
- Network egress control

**Limitations:**
- Linux only
- Best-effort egress control (proxy can be bypassed)
- File ops run in-process (trusted control plane)

### OpenShell Sandbox

`openshell` provides Docker-based isolation with policy-based network control:
- Full Docker container isolation
- Policy-based network egress control
- Working directory bind-mounted for persistence
- Container lifecycle managed by openshell CLI

**Limitations:**
- Requires Docker and OpenShell installation
- Heavier than bubblewrap (Docker overhead)
- File ops run in-process (trusted control plane)

### Approval Policies

- `auto`: No confirmation (dangerous in production)
- `confirm_all`: Confirm every tool call (safe but annoying)
- `confirm_destructive`: Balance (default)

## Performance Considerations

### Model Caching

`llama_cpp_native` caches `Llama` instances keyed on model path and parameters. This enables:
- Fast `sele chat` (no reload per turn)
- Memory reuse across loop iterations
- Configurable cache key parameters

### Memory Compaction

`summarize` memory compacts only when budget exceeded. This provides:
- No overhead for short tasks
- One model call per compaction
- Configurable trigger points

### Sandbox Overhead

- `host_direct`: Minimal overhead (direct subprocess)
- `bubblewrap`: Millisecond startup per shell call
- `openshell`: Second-level startup (Docker container creation)
- Trade-off: isolation vs. performance

## Extensibility Points

### Adding a New Surface

1. Define Protocol in `interfaces.py`
2. Implement concrete class
3. Register via decorator or entry point
4. Add config model in `config.py`
5. Update builder to wire it in
6. Add tests

### Adding a New Tool

1. Create class with `spec` and `__call__`
2. Register in `pyproject.toml` entry points
3. Add to profile `tools` list
4. Add unit tests

### Adding a New Profile

1. Create YAML file
2. Place in `sele/profiles/` (bundled) or user profile dir
3. Test with `sele profiles show <name>`

## Testing Strategy

See [EVAL.md](./EVAL.md) for complete test coverage documentation.

Test categories:
- Unit tests per module
- Integration tests for sandboxes
- End-to-end tests for full loops
- Eval tests for benchmark runner

## Future Directions

### v0.3+ Planned Features

- `transformers_native` adapter
- `docker` sandbox (cross-platform)
- `retrieval` memory
- Persistent multi-turn memory
- `gvisor` sandbox

### Research Areas

- Better tool selection strategies
- Multi-agent collaboration
- Hierarchical task decomposition
- Learning from traces
- Safety verification
