# Ollama Setup

Ollama is the easiest way to get started with local LLM inference.

## Installation

### Linux/macOS

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows

Download from https://ollama.com/download

## Pull a Model

```bash
# Recommended models for tool calling
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
ollama pull mistral-nemo

# Smaller models for testing
ollama pull llama3.1:8b
```

## Start the Server

```bash
ollama serve
```

Default: `http://localhost:11434`

## Configure sele Profile

Use the bundled `local-ollama` profile or create a custom one:

```yaml
# ~/.config/sele/profiles/my-ollama.yaml
name: my-ollama
model:
  adapter: openai_compat
  base_url: http://localhost:11434/v1
  model: llama3.1:8b
  api_key: ollama
protocol: react_text
loop: { kind: tool_loop, max_steps: 25 }
memory: full_history
sandbox: { kind: host_direct, cwd: . }
approval: confirm_destructive
tools: [shell, fs_read, fs_write, python_exec, http]
tracer: { kind: jsonl, dir: .sele/runs }
```

## Run sele

```bash
sele run "list the files in this directory" --profile my-ollama
```

## Ollama-Specific Tips

### GPU Acceleration

Ollama automatically uses GPU if available. Check with:

```bash
ollama ps
```

### Model Quantization

Ollama uses 4-bit quantization by default for efficiency. For higher quality:

```bash
# Pull a higher-precision variant (if available)
ollama pull llama3.1:8b
```

### Multiple Models

You can run multiple models and switch between them by changing the `model` field in your profile.

### System Requirements

- CPU: Any modern CPU
- RAM: 8GB+ for 8B models, 16GB+ for 70B models
- GPU: Optional but recommended for 8B+ models
- Disk: 4-8GB per model

## Troubleshooting

### Server Won't Start

```bash
# Check if port 11434 is in use
lsof -i :11434

# Kill existing ollama process
pkill ollama
```

### Model Download Failed

```bash
# Retry download
ollama pull llama3.1:8b

# Check disk space
df -h
```

### Slow Performance

```bash
# Check GPU usage
nvidia-smi  # NVIDIA
rocm-smi    # AMD

# Use a smaller model
ollama pull phi3:mini
```

## Advanced Configuration

### Custom Ollama Server

```bash
# Run on different port
OLLAMA_HOST=0.0.0.0:11435 ollama serve

# Update sele profile accordingly
# base_url: http://localhost:11435/v1
```

### Model-Specific Settings

```yaml
model:
  adapter: openai_compat
  base_url: http://localhost:11434/v1
  model: llama3.1:8b
  api_key: ollama
  temperature: 0.2
  num_ctx: 8192  # Context window
  num_gpu: 1     # GPU layers
  num_thread: 4  # CPU threads
```

## See Also

- Ollama documentation: https://ollama.com/docs
- Model library: https://ollama.com/library
