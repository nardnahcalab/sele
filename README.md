# sele

> *sele* — Danish for "harness". A pluggable agent harness for open-source language models.

`sele` is a Python CLI that lets you point any open-source LLM at a task and watch it plan, run shell commands, read/write files, and report back. It is designed for experimentation: every part of the harness — the model adapter, the tool-calling protocol, the agent loop, memory, sandbox, approval policy, tracer — is a pluggable interface you can swap via a YAML profile.

## Status

`v0.1` — early scaffold. Works against any OpenAI-compatible server (Ollama, vLLM, llama.cpp's server, OpenRouter, LM Studio, …).

## Install

```bash
git clone https://github.com/nardnahcalab/sele
cd sele
uv venv
uv pip install -e ".[dev]"
```

## Quickstart

Start an OpenAI-compatible server (e.g. Ollama):

```bash
ollama pull llama3.1:8b
ollama serve  # listens on 127.0.0.1:11434
```

Run a task with the bundled `local-ollama` profile:

```bash
sele run "list the files in this directory and summarize what the project is" \
  --profile local-ollama
```

Interactive REPL:

```bash
sele chat -p local-ollama
```

Inspect bundled profiles or the latest trace:

```bash
sele profiles list
sele profiles show local-ollama
sele trace show .sele/runs/<run-id>.jsonl
```

## Architecture

`sele` is a thin coordinator over a set of pluggable surfaces. A YAML
profile wires them together; the builder instantiates concrete classes
from the registry; the loop drives them.

```
Profile (YAML)
   │
   ▼
Builder ──► LoopContext { ModelAdapter · ToolProtocol · AgentLoop ·
                          Memory · Sandbox · Approval · Tools · Tracer }
                   │
                   ▼
              Agent loop drives turns
```

| Surface         | Default impl              | Other planned impls                         |
| --------------- | ------------------------- | ------------------------------------------- |
| ModelAdapter    | `openai_compat`           | `llama_cpp_native`, `transformers_native`   |
| ToolProtocol    | `native_tools`/`react_text` | `json_grammar`, `xml_tags`                |
| AgentLoop       | `tool_loop`/`plan_execute` | `reflexion`, `tree_search`                 |
| Memory          | `full_history`            | `sliding_window`, `summarize`, `retrieval`  |
| Sandbox         | `host_direct`             | `docker`, `firejail`                        |
| Approval        | `confirm_destructive`     | `allowlist`, `policy_lm`                    |
| Tools           | `shell`, `fs_read`, `fs_write` | `http`, `python_exec`, `git`           |
| Tracer          | `jsonl`, `console`, `null` | `otel`                                     |

## Writing a profile

```yaml
name: my-profile
model:
  adapter: openai_compat
  base_url: http://localhost:11434/v1
  model: qwen2.5:7b
  api_key: ollama
protocol: react_text
loop: { kind: tool_loop, max_steps: 25 }
memory: full_history
sandbox: { kind: host_direct, cwd: . }
approval: confirm_destructive
tools: [shell, fs_read, fs_write]
tracer: { kind: jsonl, dir: .sele/runs }
system_prompt: |
  You are a careful agent.
```

Drop it in `./.sele/profiles/my-profile.yaml` or `~/.config/sele/profiles/my-profile.yaml` and use `sele run -p my-profile "..."`.

## Writing a plugin

In-tree, register with a decorator:

```python
from sele import tool
from sele.types import ToolSpec, ToolResult

class _Echo:
    spec = ToolSpec(name="echo", description="Echo back the input.",
                    parameters={"type": "object",
                                "properties": {"text": {"type": "string"}},
                                "required": ["text"]})
    def __call__(self, sandbox, arguments):
        return ToolResult(call_id="", name="echo", ok=True,
                          content=arguments.get("text", ""))

tool("echo")(_Echo())
```

Out-of-tree, add an entry point in your package's `pyproject.toml`:

```toml
[project.entry-points."sele.tools"]
echo = "my_pkg.tools:echo"
```

The same pattern works for `sele.adapters`, `sele.protocols`, `sele.loops`, `sele.memory`, `sele.sandbox`, `sele.approval`, and `sele.tracer`.

## Safety

The default sandbox runs commands directly on your host. The default
approval policy (`confirm_destructive`) prompts before `shell` and
`fs_write` calls when sele is attached to a terminal, and denies them in
non-interactive sessions. Use `sele run -p ... --cwd /tmp/work` to
confine filesystem operations to a scratch directory, and inspect traces
under `.sele/runs/` to see exactly what was attempted.

## Roadmap

- v0.2 — `llama_cpp_native` and `transformers_native` adapters; `docker` sandbox; `summarize` and `retrieval` memory; `python_exec` and `http` tools.
- v0.3 — `reflexion` loop; eval runner against agent benchmarks; persistent multi-turn chat memory.

## License

Apache-2.0. See [LICENSE](./LICENSE).
