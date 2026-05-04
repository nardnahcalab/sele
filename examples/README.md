# sele Examples

This directory contains examples for using the sele agent harness.

## Directory Structure

- `quickstart/` - Basic getting started examples
- `profiles/` - Example profile configurations for different scenarios
- `servers/` - Setup guides for inference servers (Ollama, vLLM, etc.)
- `advanced/` - Advanced usage patterns and customizations

## Quick Start

1. Choose an inference server from `servers/` and set it up
2. Pick a profile from `profiles/` or create your own
3. Run sele: `sele run "your task" --profile <profile-name>`

## Common Use Cases

- **Local development**: Use Ollama or llama.cpp for offline inference
- **Production**: Use vLLM or OpenRouter for scalable inference
- **Isolation**: Use bubblewrap sandbox for secure execution
- **Long tasks**: Use summarize memory for context window management
- **Benchmarking**: Use `sele eval` to measure performance

## Next Steps

See the individual subdirectories for detailed examples.
