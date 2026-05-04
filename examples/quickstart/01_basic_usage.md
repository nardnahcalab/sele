# Basic Usage

## Quick Start with Ollama

### 1. Install Ollama

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com/download
```

### 2. Pull a Model

```bash
ollama pull llama3.1:8b
```

### 3. Start Ollama Server

```bash
ollama serve
```

### 4. Run sele

```bash
# Install sele
git clone https://github.com/nardnahcalab/sele
cd sele
uv venv
uv pip install -e ".[dev]"

# Run a simple task
sele run "list the files in this directory" --profile local-ollama

# Interactive chat
sele chat --profile local-ollama
```

## Example Tasks

### File Operations

```bash
# Read a file
sele run "read the README.md and summarize it" --profile local-ollama

# Write a file
sele run "create a file called notes.md with a summary of this project" --profile local-ollama

# Analyze code
sele run "look at the Python files in src/ and explain the architecture" --profile local-ollama
```

### Shell Commands

```bash
# System inspection
sele run "check what Python version is installed and list installed packages" --profile local-ollama

# Git operations
sele run "show the last 5 git commits and explain what changed" --profile local-ollama
```

### Data Processing

```bash
# Process CSV
sele run "read data.csv, calculate the average of the value column, and save the result to summary.txt" --profile local-ollama

# JSON manipulation
sele run "read config.json, update the version to 2.0, and write it back" --profile local-ollama
```

## Interactive Chat

```bash
sele chat --profile local-ollama
```

In the REPL:
```
you › list the files in this directory
sele: [runs task and shows result]

you › read the README and tell me what this project does
sele: [runs task and shows result]

you › :quit  # or ctrl-d to exit
```

## Inspecting Profiles

```bash
# List available profiles
sele profiles list

# Show a profile's configuration
sele profiles show local-ollama

# Show trace of last run
sele trace show .sele/runs/<run-id>.jsonl
```

## Common Options

```bash
# Override sandbox working directory
sele run "task" --profile local-ollama --cwd /tmp/work

# Override max steps
sele run "complex task" --profile local-ollama --max-steps 50

# Use a custom profile
sele run "task" --profile /path/to/my-profile.yaml
```

## Safety Tips

- Use `--cwd` to confine operations to a scratch directory
- The default `confirm_destructive` policy will prompt before shell/fs_write operations
- Inspect traces in `.sele/runs/` to see exactly what was attempted
- For real isolation on Linux, use the `bubblewrap-local` profile
