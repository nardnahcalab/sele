# CI/CD Integration

Use sele in automated workflows for code review, testing, and more.

## GitHub Actions

### Code Review Bot

```yaml
# .github/workflows/code-review.yml
name: Code Review

on:
  pull_request:
    paths:
      - 'src/**/*.py'

jobs:
  review:
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
      - name: Review code
        run: |
          sele run "Review the changed files in this PR for bugs, security issues, and style problems. Focus on src/." \
            --profile local-ollama \
            --cwd . \
            > review.txt
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('review.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Code Review\n\n${review}`
            });
```

### Automated Testing

```yaml
# .github/workflows/agent-tests.yml
name: Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install sele
        run: pip install -e ".[dev]"
      - name: Run unit tests
        run: pytest
      - name: Install Ollama
        run: curl -fsSL https://ollama.com/install.sh | sh
      - name: Pull model
        run: ollama pull llama3.1:8b
      - name: Start Ollama
        run: ollama serve &
      - name: Run agent tests
        run: sele eval benchmarks/agent-tests.jsonl --profile local-ollama
```

## GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - review

code_review:
  stage: review
  script:
    - pip install -e .
    - curl -fsSL https://ollama.com/install.sh | sh
    - ollama pull llama3.1:8b
    - ollama serve &
    - sele run "Review the changes in this MR" --profile local-ollama
  only:
    - merge_requests
```

## Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any
    stages {
        stage('Code Review') {
            steps {
                sh '''
                    pip install -e .
                    curl -fsSL https://ollama.com/install.sh | sh
                    ollama pull llama3.1:8b
                    ollama serve &
                    sele run "Review this PR" --profile local-ollama
                '''
            }
        }
    }
}
```

## Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Run sele on changed files
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -n "$CHANGED_FILES" ]; then
    echo "Running sele on changed files..."
    sele run "Review these changed files for issues: $CHANGED_FILES" \
        --profile local-ollama \
        --cwd . || echo "Review found issues"
fi
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

## Docker Integration

```dockerfile
# Dockerfile
FROM python:3.12

RUN pip install sele
RUN curl -fsSL https://ollama.com/install.sh | sh
RUN ollama pull llama3.1:8b

COPY . /app
WORKDIR /app

CMD ["sele", "run", "Analyze this codebase", "--profile", "local-ollama"]
```

Build and run:

```bash
docker build -t sele-agent .
docker run -v $(pwd):/app sele-agent
```

## Kubernetes CronJob

```yaml
# k8s-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-code-review
spec:
  schedule: "0 9 * * *"  # Daily at 9 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: sele
            image: sele-agent:latest
            command:
            - sele
            - run
            - "Review the codebase for issues"
            - --profile
            - local-ollama
          restartPolicy: OnFailure
```

## Monitoring and Alerts

```yaml
# .github/workflows/monitor.yml
name: Monitor

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install sele
        run: pip install -e .
      - name: Run health check
        run: sele eval benchmarks/health.jsonl --profile local-ollama
      - name: Check results
        run: |
          passed=$(jq '[.success] | map(select(.) == true) | length' results/local-ollama_results.jsonl)
          total=$(jq 'length' results/local-ollama_results.jsonl)
          if [ $passed -lt $((total * 8 / 10)) ]; then
            echo "Health check failed: $passed/$total passed"
            exit 1
          fi
```

## Best Practices

### Security

- Don't commit API keys
- Use environment variables for secrets
- Use sandboxing in CI (bubblewrap if on Linux)
- Review traces before approving

### Performance

- Use smaller models in CI for speed
- Limit max steps to prevent runaway tasks
- Set appropriate timeouts
- Cache model weights between runs

### Reliability

- Handle model unavailability gracefully
- Retry failed requests
- Log all actions for debugging
- Set up alerts for failures

## Example: Full CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run unit tests
        run: pytest
      - name: Run lint
        run: ruff check

  agent-test:
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
      - name: Run agent tests
        run: sele eval benchmarks/ci.jsonl --profile local-ollama

  review:
    if: github.event_name == 'pull_request'
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
      - name: Code review
        run: sele run "Review this PR for bugs and security issues" --profile local-ollama
```

## See Also

- ARCHITECTURE.md - System architecture
- Examples/servers/ - Server setup guides
