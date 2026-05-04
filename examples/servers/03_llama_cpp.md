# llama.cpp Server Setup

llama.cpp provides a lightweight server for GGUF models. Great for offline use and resource-constrained environments.

## Installation

```bash
# Via pip
pip install llama-cpp-python[server]

# With hardware acceleration
# NVIDIA GPU:
CMAKE_ARGS="-DGGML_CUDA=on" pip install --upgrade --force-reinstall llama-cpp-python

# Apple Silicon (Metal):
CMAKE_ARGS="-DGGML_METAL=on" pip install --upgrade --force-reinstall llama-cpp-python
```

## Download a GGUF Model

```bash
# From Hugging Face
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

# Or use the built-in llama.cpp server download
# (requires llama.cpp CLI tools)
```

Popular sources:
- Hugging Face (search for "gguf")
- TheBlokke (quantized models)
- bartowski (high-quality quantizations)

## Start the Server

### Basic Server

```bash
python -m llama_cpp.server \
  --model Phi-3-mini-4k-instruct-q4.gguf \
  --host 0.0.0.0 \
  --port 8080
```

### With GPU Acceleration

```bash
python -m llama_cpp.server \
  --model Phi-3-mini-4k-instruct-q4.gguf \
  --n_gpu_layers 35 \
  --host 0.0.0.0 \
  --port 8080
```

### With Context Window

```bash
python -m llama_cpp.server \
  --model Phi-3-mini-4k-instruct-q4.gguf \
  --n_ctx 8192 \
  --n_gpu_layers 35 \
  --host 0.0.0.0 \
  --port 8080
```

## Configure sele Profile

### Using OpenAI-Compatible Server

```yaml
# ~/.config/sele/profiles/llama-cpp-server.yaml
name: llama-cpp-server
model:
  adapter: openai_compat
  base_url: http://localhost:8080/v1
  model: phi-3-mini-4k-instruct
  api_key: EMPTY
  temperature: 0.2
protocol: react_text
loop: { kind: tool_loop, max_steps: 25 }
memory: full_history
sandbox: { kind: host_direct, cwd: . }
approval: confirm_destructive
tools: [shell, fs_read, fs_write, python_exec]
tracer: { kind: jsonl, dir: .sele/runs }
```

### Using In-Process Adapter (Recommended for sele)

```yaml
# ~/.config/sele/profiles/llama-cpp-native.yaml
name: llama-cpp-native
model:
  adapter: llama_cpp_native
  model: phi-3-mini-4k-instruct
  model_path: /path/to/Phi-3-mini-4k-instruct-q4.gguf
  n_ctx: 8192
  n_gpu_layers: 35  # -1 for all layers
  chat_format: chatml  # or llama-3, qwen, etc.
  temperature: 0.2
  verbose: false
protocol: native_tools
loop: { kind: tool_loop, max_steps: 25 }
memory: full_history
sandbox: { kind: host_direct, cwd: . }
approval: confirm_destructive
tools: [shell, fs_read, fs_write, python_exec]
tracer: { kind: jsonl, dir: .sele/runs }
```

## Run sele

```bash
# With server
sele run "analyze this directory" --profile llama-cpp-server

# With in-process adapter (faster for chat)
sele chat --profile llama-cpp-native
```

## llama.cpp-Specific Tips

### Chat Formats

Different models use different chat formats:

```yaml
model:
  chat_format: chatml    # Phi-3, Mistral
  chat_format: llama-3   # Llama 3
  chat_format: qwen      # Qwen
  chat_format: functionary-v2  # Functionary models
```

### GPU Offloading

```yaml
model:
  n_gpu_layers: -1  # Offload all layers
  n_gpu_layers: 35  # Offload specific number
```

### Context Window

```yaml
model:
  n_ctx: 4096   # Default for many models
  n_ctx: 8192   # For models that support it
  n_ctx: 32768  # For larger context models
```

### Sampling Parameters

```yaml
model:
  temperature: 0.2
  top_p: 0.95
  top_k: 40
  repeat_penalty: 1.1
```

## System Requirements

### Minimum (3B model, Q4)
- CPU: 4 cores
- RAM: 8GB
- GPU: Optional (CPU-only works)
- Disk: 5GB

### Recommended (7B model, Q4)
- CPU: 8 cores
- RAM: 16GB
- GPU: 8GB VRAM (optional)
- Disk: 10GB

### Large (70B model, Q4)
- CPU: 16 cores
- RAM: 64GB
- GPU: 48GB VRAM (recommended)
- Disk: 40GB

## Troubleshooting

### Model Not Found

```bash
# Check model path is absolute
ls -la /path/to/model.gguf

# Try relative path from sele directory
model_path: ./models/phi-3.gguf
```

### Slow Performance

```bash
# Enable GPU offloading
n_gpu_layers: -1

# Use smaller model
# Try 3B instead of 7B

# Reduce context window
n_ctx: 4096
```

### Out of Memory

```bash
# Reduce GPU layers
n_gpu_layers: 20

# Use CPU-only
n_gpu_layers: 0

# Reduce context window
n_ctx: 2048
```

## Advanced Configuration

### Multiple Models

```bash
# Run multiple servers on different ports
python -m llama_cpp.server --model model1.gguf --port 8080
python -m llama_cpp.server --model model2.gguf --port 8081
```

### Custom Tokenizer

```bash
python -m llama_cpp.server \
  --model model.gguf \
  --tokenizer path/to/tokenizer.json
```

### Quantization

Models come pre-quantized (Q4, Q5, Q8). Choose based on your needs:
- Q4_K_M: Best balance of size/quality
- Q5_K_M: Higher quality, slightly larger
- Q8_0: Near-original quality, larger

## See Also

- llama.cpp documentation: https://github.com/ggerganov/llama.cpp
- GGUF model repository: https://huggingface.co/models?search=gguf
