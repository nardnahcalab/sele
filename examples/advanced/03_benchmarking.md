# Benchmarking with sele eval

Use `sele eval` to measure agent performance on benchmarks.

## Creating a Benchmark

Create a JSONL file with tasks:

```jsonl
{"id": "task1", "task": "list the files in the current directory"}
{"id": "task2", "task": "read the README.md and summarize it in one sentence"}
{"id": "task3", "task": "create a file called notes.md with a list of Python files"}
```

Save as `benchmark.jsonl`.

## Running an Evaluation

```bash
sele eval benchmark.jsonl --profile local-ollama
```

## Options

```bash
# Limit to first N tasks
sele eval benchmark.jsonl --profile local-ollama --max-tasks 10

# Per-task timeout
sele eval benchmark.jsonl --profile local-ollama --timeout 120

# Continue after failures
sele eval benchmark.jsonl --profile local-ollama --continue-on-error

# Custom output directory
sele eval benchmark.jsonl --profile local-ollama --output-dir ./results
```

## Result Format

Results are written to `<output_dir>/<profile>_results.jsonl`:

```json
{"task_id": "task1", "task": "list files", "success": true, "output": "file1.txt\nfile2.py", "error": null, "duration": 2.5, "steps": 3}
{"task_id": "task2", "task": "read README", "success": false, "output": "", "error": "file not found", "duration": 1.2, "steps": 2}
```

## Summary Output

```
==================================================
EVALUATION SUMMARY
==================================================
Total tasks:   3
Passed:        2 (66.7%)
Failed:        1
Avg duration:  2.0s
Avg steps:     2.5
==================================================
```

## Comparing Profiles

Run the same benchmark with different profiles:

```bash
# Profile A
sele eval benchmark.jsonl --profile profile-a --output-dir ./results-a

# Profile B
sele eval benchmark.jsonl --profile profile-b --output-dir ./results-b

# Compare results
python -c "
import json
a = [json.loads(l) for l in open('results-a/local-ollama_results.jsonl')]
b = [json.loads(l) for l in open('results-b/vllm_results.jsonl')]
print(f'Profile A: {sum(1 for r in a if r[\"success\"])}/{len(a)} passed')
print(f'Profile B: {sum(1 for r in b if r[\"success\"])}/{len(b)} passed')
"
```

## Benchmark Categories

### Functional Testing

Test core capabilities:

```jsonl
{"id": "fs1", "task": "read README.md"}
{"id": "fs2", "task": "write hello.txt with content 'hello world'"}
{"id": "fs3", "task": "list files in src/"}
{"id": "sh1", "task": "check Python version"}
{"id": "sh2", "task": "show git log --oneline -5"}
```

### Domain-Specific

Test domain knowledge:

```jsonl
{"id": "code1", "task": "explain the architecture of this Python project"}
{"id": "code2", "task": "find all functions that take a 'path' parameter"}
{"id": "code3", "task": "identify potential security issues in the code"}
```

### Regression Testing

Catch regressions:

```jsonl
{"id": "reg1", "task": "run the test suite and report failures"}
{"id": "reg2", "task": "build the project and report errors"}
{"id": "reg3", "task": "check for linting issues"}
```

## Advanced: Automated Benchmarking

Create a script to run multiple benchmarks:

```bash
#!/bin/bash
# run_benchmarks.sh

PROFILES=("local-ollama" "vllm" "openrouter")
BENCHMARKS=("basic.jsonl" "code.jsonl" "security.jsonl")

for profile in "${PROFILES[@]}"; do
  for benchmark in "${BENCHMARKS[@]}"; do
    echo "Running $benchmark with $profile"
    sele eval "$benchmark" --profile "$profile" \
      --output-dir "./results/${profile}/${benchmark%.jsonl}"
  done
done
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/eval.yml
name: Evaluation

on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install sele
        run: pip install -e .
      - name: Install Ollama
        run: curl -fsSL https://ollama.com/install.sh | sh
      - name: Pull model
        run: ollama pull llama3.1:8b
      - name: Start Ollama
        run: ollama serve &
      - name: Run evaluation
        run: sele eval benchmarks/basic.jsonl --profile local-ollama
```

## Performance Metrics

Track metrics over time:

```python
# analyze_results.py
import json
from pathlib import Path

def analyze_results(results_dir):
    results = []
    for file in Path(results_dir).glob("*.jsonl"):
        for line in file.read_text().splitlines():
            results.append(json.loads(line))

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    avg_duration = sum(r["duration"] for r in results) / total
    avg_steps = sum(r["steps"] for r in results) / total

    print(f"Total: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Avg duration: {avg_duration:.2f}s")
    print(f"Avg steps: {avg_steps:.1f}")

if __name__ == "__main__":
    analyze_results("./results")
```

## See Also

- EVAL.md - Test documentation
- CLI help: `sele eval --help`
