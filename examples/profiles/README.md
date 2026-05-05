# Profile Configuration Examples

This directory contains example profile configurations for different scenarios.

## Bundled Profiles

The following profiles are bundled with sele:

- `local-ollama` - Local Ollama with ReAct text protocol
- `local-llamacpp` - In-process llama.cpp for GGUF models
- `openrouter` - OpenRouter API with plan-execute loop
- `vllm` - Generic vLLM/OpenAI-compatible server
- `bubblewrap-local` - Ollama with bubblewrap sandbox
- `openshell-local` - Ollama with OpenShell Docker-based sandbox
- `summarize-ollama` - Ollama with summarize memory

## Custom Profiles

Create custom profiles in:
- `./.sele/profiles/<name>.yaml` (project-specific)
- `~/.config/sele/profiles/<name>.yaml` (user-specific)

Custom profiles override bundled profiles with the same name.

## Examples

### 01_minimal_profile.yaml

A minimal profile with only essential settings.

### 02_custom_model.yaml

Using a different model backend with custom parameters.

### 03_bubblewrap_secure.yaml

Secure configuration with bubblewrap sandbox and egress control.

### 04_summarize_memory.yaml

Profile with summarize memory for long-running tasks.

### 05_custom_tools.yaml

Profile with custom tool selection and approval policy.

### 06_production.yaml

Production-ready configuration with timeouts and resource limits.

### 07_openshell_secure.yaml

Secure configuration with OpenShell Docker-based sandbox for stronger isolation.
