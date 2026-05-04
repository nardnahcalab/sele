# vLLM Setup

vLLM is a high-performance LLM inference server optimized for production workloads.

## Installation

### With GPU (Recommended)

```bash
pip install vllm
```

### CPU-Only

```bash
pip install vllm
# Note: CPU-only is significantly slower
```

## Start the Server

### Basic Setup

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

### With GPU Configuration

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192 \
  --host 0.0.0.0 \
  --port 8000
```

### Multi-GPU

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768 \
  --host 0.0.0.0 \
  --port 8000
```

## Configure sele Profile

```yaml
# ~/.config/sele/profiles/vllm-production.yaml
name: vllm-production
model:
  adapter: openai_compat
  base_url: http://localhost:8000/v1
  model: Qwen/Qwen2.5-7B-Instruct
  api_key: EMPTY
  temperature: 0.0
  max_tokens: 2048
  timeout: 120.0
protocol: native_tools
loop: { kind: tool_loop, max_steps: 25 }
memory: full_history
sandbox: { kind: host_direct, cwd: . }
approval: confirm_destructive
tools: [shell, fs_read, fs_write, python_exec, http]
tracer: { kind: jsonl, dir: .sele/runs }
```

## Run sele

```bash
sele run "analyze the code in src/" --profile vllm-production
```

## vLLM-Specific Tips

### Model Selection

Recommended models for tool calling:
- `Qwen/Qwen2.5-7B-Instruct` - Excellent tool calling
- `meta-llama/Llama-3.1-8B-Instruct` - Good all-rounder
- `mistralai/Mistral-Nemo` - Fast and capable

### Performance Tuning

```bash
# Increase throughput
--max-num-seqs 256

# Enable prefix caching
--enable-prefix-caching

# Use specific quantization
--quantization awq
--quantization bits 4
```

### Monitoring

```bash
# Check server health
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics
```

## Production Deployment

### Docker Deployment

```dockerfile
FROM vllm/vllm-openai:latest

EXPOSE 8000

CMD ["python", "-m", "vllm.entrypoints.openai.api_server",
     "--model", "Qwen/Qwen2.5-7B-Instruct",
     "--host", "0.0.0.0",
     "--port", "8000"]
```

```bash
docker build -t vllm-server .
docker run -p 8000:8000 --gpus all vllm-server
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model
        - Qwen/Qwen2.5-7B-Instruct
        - --host
        - 0.0.0.0
        - --port
        - 8000
```

## System Requirements

### Minimum (7B model)
- CPU: 8 cores
- RAM: 32GB
- GPU: 1x A10G (24GB VRAM) or similar
- Disk: 20GB

### Recommended (70B model)
- CPU: 16 cores
- RAM: 64GB
- GPU: 4x A100 (40GB VRAM each)
- Disk: 100GB

## Troubleshooting

### Out of Memory

```bash
# Reduce GPU memory utilization
--gpu-memory-utilization 0.7

# Use a smaller model
--model Qwen/Qwen2.5-3B-Instruct

# Enable CPU offload
--max-model-len 4096
```

### Slow Inference

```bash
# Increase batch size
--max-num-batched-tokens 4096

# Use tensor parallelism
--tensor-parallel-size 2

# Enable prefix caching
--enable-prefix-caching
```

### Connection Refused

```bash
# Check if server is running
curl http://localhost:8000/health

# Check firewall
sudo ufw allow 8000/tcp
```

## Advanced Configuration

### Custom LoRA Adapters

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --enable-lora \
  --lora-modules my-lora=/path/to/lora
```

### Speculative Decoding

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --speculative-model meta-llama/Llama-3.1-8B-Instruct \
  --num-speculative-tokens 5
```

## See Also

- vLLM documentation: https://docs.vllm.ai
- Model support: https://docs.vllm.ai/en/latest/models/supported_models.html
