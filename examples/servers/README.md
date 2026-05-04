# Inference Server Setup

This directory contains setup guides for various inference servers that work with sele.

## Supported Servers

- **Ollama** - Easiest to get started, runs locally
- **vLLM** - High-performance, production-ready
- **llama.cpp server** - Lightweight, for GGUF models
- **LM Studio** - GUI-based local inference
- **OpenRouter** - Cloud API with many models

## Quick Comparison

| Server | Ease of Setup | Performance | Offline | Production | Tool Calling |
|--------|--------------|-------------|---------|------------|-------------|
| Ollama | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | ⚠️ | ✅ |
| vLLM | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ✅ | ✅ |
| llama.cpp | ⭐⭐⭐⭐ | ⭐⭐ | ✅ | ⚠️ | ⭐⭐ |
| LM Studio | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | ⚠️ | ✅ |
| OpenRouter | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ✅ | ✅ |

## Choosing a Server

- **Local development**: Ollama or LM Studio
- **Production**: vLLM or OpenRouter
- **Offline/Privacy**: llama.cpp or Ollama
- **Maximum performance**: vLLM with GPU

## Examples

See individual setup guides:
- `01_ollama.md` - Ollama setup and configuration
- `02_vllm.md` - vLLM setup for production
- `03_llama_cpp.md` - llama.cpp server setup
- `04_lm_studio.md` - LM Studio setup
- `05_openrouter.md` - OpenRouter API configuration
