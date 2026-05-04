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
# Optional: in-process llama.cpp backend (compiles native code)
uv pip install -e ".[llama_cpp]"
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
| ModelAdapter    | `openai_compat`, `llama_cpp_native` | `transformers_native`            |
| ToolProtocol    | `native_tools`/`react_text` | `json_grammar`, `xml_tags`                |
| AgentLoop       | `tool_loop`/`plan_execute` | `reflexion`, `tree_search`                 |
| Memory          | `full_history`            | `sliding_window`, `summarize`, `retrieval`  |
| Sandbox         | `host_direct`, `bubblewrap` | `docker`, `firejail`, `gvisor`            |
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

The default sandbox (`host_direct`) runs commands directly on your host
with only a working-directory boundary. The default approval policy
(`confirm_destructive`) prompts before `shell` and `fs_write` calls when
sele is attached to a terminal, and denies them in non-interactive
sessions. Use `sele run -p ... --cwd /tmp/work` to confine filesystem
operations to a scratch directory, and inspect traces under
`.sele/runs/` to see exactly what was attempted.

For real isolation on Linux, use the `bubblewrap` sandbox (next section).

## Sandboxing with `bubblewrap`

`bubblewrap` (the same tool Flatpak uses) is dramatically lighter than
Docker — milliseconds to start, no daemon, single static binary,
unprivileged. Each `shell` call runs in fresh PID/IPC/UTS/mount namespaces
with all capabilities dropped, the host `/usr`, `/etc`, etc. bind-mounted
read-only, and a tmpfs `/tmp`. The sandbox cwd is bind-mounted read-write
so progress persists across calls.

Linux only. Install on the host:

```bash
sudo apt install bubblewrap     # Debian / Ubuntu
sudo dnf install bubblewrap     # Fedora / RHEL
sudo pacman -S bubblewrap       # Arch
sudo apk add bubblewrap         # Alpine
```

Then use the bundled profile:

```bash
sele run "look at this directory and write a one-line summary to NOTES.md" \
  -p bubblewrap-local
```

### Network egress modes

`bubblewrap-local` defaults to `egress.mode: none`, which fully blocks
network from inside the sandbox via `--unshare-net`. To allow specific
hosts:

```yaml
sandbox:
  kind: bubblewrap
  egress:
    mode: hosts
    hosts: [github.com, "*.github.com", pypi.org, "*.pypi.org"]
```

`hosts` mode runs an in-process HTTP CONNECT proxy on `127.0.0.1` and
sets `http_proxy` / `https_proxy` env vars in the sandbox. Well-behaved
tools (curl, git, pip, requests) will route through it. **This is
best-effort only**: tools that ignore proxy env vars or use raw sockets
can bypass it. For hard guarantees use `mode: none`.

| Mode | Network | Bypassable? |
|---|---|---|
| `none` | `--unshare-net` — fully blocked | No |
| `all` | shares host network namespace | n/a (no policy) |
| `hosts` | shares network + CONNECT proxy with hostname allowlist | Yes (proxy env, raw sockets) |

## Running fully offline with `llama_cpp_native`

`llama_cpp_native` runs a GGUF model directly in the `sele` process — no
server, no network, no Ollama. It's slower to start (loads weights into
memory) but more controllable and has no inter-process IPC.

```bash
pip install "sele[llama_cpp]"
# Build with hardware acceleration if you have it:
#   CMAKE_ARGS="-DGGML_CUDA=on" pip install --upgrade --force-reinstall llama-cpp-python
#   CMAKE_ARGS="-DGGML_METAL=on" pip install --upgrade --force-reinstall llama-cpp-python
```

Copy the bundled `local-llamacpp` profile to `./.sele/profiles/` (or
`~/.config/sele/profiles/`), edit `model.model_path` to point at your
`.gguf`, then:

```bash
sele run "summarize this directory" -p local-llamacpp
```

The first call loads the model; subsequent loop iterations within the
same process reuse the cached `Llama` instance, so `sele chat` is
viable without paying load cost per turn.

Tool calling works with chat formats that support it — `llama-3`,
`qwen`, `functionary-v2`, `chatml-function-calling`. For models without
tool support, switch the profile's `protocol` to `react_text` and tools
will be rendered into the system prompt.

## Roadmap

- v0.2 — `transformers_native` adapter; `docker` sandbox (cross-platform fallback to bubblewrap); `summarize` and `retrieval` memory; `python_exec` and `http` tools.
- v0.3 — `reflexion` loop; eval runner against agent benchmarks; persistent multi-turn chat memory; optional `gvisor` sandbox for stricter isolation.

## License

Apache-2.0. See [LICENSE](./LICENSE).
