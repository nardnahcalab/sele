# OpenRouter Setup

OpenRouter provides access to many models via a unified API. Great for trying different models without local setup.

## Sign Up

1. Go to https://openrouter.ai
2. Create an account
3. Get your API key from the settings

## Configure sele Profile

```yaml
# ~/.config/sele/profiles/openrouter.yaml
name: openrouter
model:
  adapter: openai_compat
  base_url: https://openrouter.ai/api/v1
  model: meta-llama/llama-3.1-70b-instruct
  api_key_env: OPENROUTER_API_KEY  # Set this environment variable
  temperature: 0.2
  extra_headers:
    HTTP-Referer: https://github.com/nardnahcalab/sele
    X-Title: sele
protocol: native_tools
loop: { kind: plan_execute, max_steps: 30 }
memory: full_history
sandbox: { kind: host_direct, cwd: . }
approval: confirm_destructive
tools: [shell, fs_read, fs_write, python_exec, http]
tracer: { kind: jsonl, dir: .sele/runs }
```

## Set API Key

```bash
# Set environment variable
export OPENROUTER_API_KEY="your-api-key-here"

# Or add to ~/.bashrc or ~/.zshrc
echo 'export OPENROUTER_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Run sele

```bash
sele run "analyze the code in src/" --profile openrouter
```

## Model Selection

OpenRouter provides access to many models. Popular choices for tool calling:

### High Quality
- `meta-llama/llama-3.1-70b-instruct` - Best overall
- `anthropic/claude-3.5-sonnet` - Excellent reasoning
- `openai/gpt-4o` - Best tool calling

### Fast
- `meta-llama/llama-3.1-8b-instruct` - Good balance
- `qwen/qwen-2.5-7b-instruct` - Fast and capable
- `mistralai/mistral-nemo` - Very fast

### Cost-Effective
- `meta-llama/llama-3.1-8b-instruct` - Good value
- `qwen/qwen-2.5-7b-instruct` - Excellent value
- `microsoft/phi-3-mini-128k-instruct` - Very cheap

## Pricing

OpenRouter uses per-token pricing. Check current prices at:
https://openrouter.ai/models

## OpenRouter-Specific Tips

### Model Routing

OpenRouter can automatically route to the best available model:

```yaml
model:
  model: auto  # Let OpenRouter choose
```

### Fallback Models

Configure fallback if primary model is unavailable:

```yaml
model:
  model: meta-llama/llama-3.1-70b-instruct
  # OpenRouter will fallback if needed
```

### Rate Limits

Free tier has rate limits. For production, consider a paid plan.

## Troubleshooting

### API Key Not Found

```bash
# Verify environment variable
echo $OPENROUTER_API_KEY

# Test the key
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### Model Not Available

```bash
# List available models
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### Rate Limit Errors

- Add delay between requests
- Upgrade to paid plan
- Use a different model

## Advanced Configuration

### Custom Headers

```yaml
model:
  extra_headers:
    HTTP-Referer: https://your-app.com
    X-Title: Your App Name
    X-Api-Key: your-api-key  # Alternative to env var
```

### Model-Specific Parameters

Some models support additional parameters:

```yaml
model:
  model: meta-llama/llama-3.1-70b-instruct
  repetition_penalty: 1.1
  top_k: 40
```

## See Also

- OpenRouter documentation: https://openrouter.ai/docs
- Model catalog: https://openrouter.ai/models
- Pricing: https://openrouter.ai/models?pricing=true
