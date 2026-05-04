# LM Studio Setup

LM Studio provides a GUI for local LLM inference with an OpenAI-compatible server.

## Installation

Download from https://lmstudio.ai

## Setup

### 1. Install LM Studio

Run the installer for your platform.

### 2. Download a Model

- Open LM Studio
- Go to "Models" tab
- Search for a model (e.g., "Llama 3.1 8B")
- Click "Download"

Recommended models:
- `Llama 3.1 8B Instruct`
- `Qwen 2.5 7B Instruct`
- `Phi 3 Mini 4K Instruct`

### 3. Start the Server

- Go to "Local Server" tab
- Click "Start Server"
- Note the port (default 1234)

### 4. Configure sele Profile

```yaml
# ~/.config/sele/profiles/lm-studio.yaml
name: lm-studio
model:
  adapter: openai_compat
  base_url: http://localhost:1234/v1
  model: llama-3.1-8b-instruct
  api_key: lm-studio
  temperature: 0.2
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
sele run "list the files in this directory" --profile lm-studio
```

## LM Studio-Specific Tips

### GPU Configuration

In LM Studio:
- Go to Settings → GPU
- Select your GPU
- Adjust GPU memory allocation

### Server Port

If you changed the port in LM Studio, update your profile:

```yaml
model:
  base_url: http://localhost:5678/v1  # Custom port
```

### Model Selection

The `model` field in your profile should match the model name in LM Studio. Check the model name in the LM Studio interface.

### Chat Mode

LM Studio has a built-in chat interface. You can use it for testing before connecting with sele.

## System Requirements

### Minimum
- CPU: 4 cores
- RAM: 16GB
- GPU: 8GB VRAM (optional)
- Disk: 20GB

### Recommended
- CPU: 8 cores
- RAM: 32GB
- GPU: 16GB VRAM
- Disk: 50GB

## Troubleshooting

### Server Won't Start

- Check if another app is using the port
- Restart LM Studio
- Check LM Studio logs

### Connection Refused

```bash
# Check if server is running
curl http://localhost:1234/v1/models

# Verify port in LM Studio settings
```

### Slow Performance

- Increase GPU allocation in LM Studio settings
- Use a smaller model
- Close other applications

## See Also

- LM Studio documentation: https://lmstudio.ai/docs
- LM Studio Discord: https://discord.gg/aKQPXDEfDb
