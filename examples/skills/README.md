# Skills Examples

This directory contains examples of using and creating skills in sele.

## What are Skills?

Skills are pluggable components that augment the agent loop with specialized reasoning strategies, context management, and control over the breadth and depth of the agent's search space.

## Examples

### 1. Using Built-in Skills

The simplest way to use skills is to enable them in your profile:

```yaml
name: my-profile
model:
  adapter: openai_compat
  base_url: http://localhost:11434/v1
  model: llama3.1:8b
  api_key: ollama
protocol: react_text
loop:
  kind: tool_loop
  max_steps: 50
  skills:
    enabled: true
    skills: [reflexion]
    skill_settings:
      reflexion:
        reflection_threshold: 3
        max_reflections: 2
memory: full_history
sandbox:
  kind: host_direct
  cwd: .
approval: confirm_destructive
tools: [shell, fs_read, fs_write]
tracer: jsonl
system_prompt: |
  You are a careful agent that can reflect on your progress.
```

Then run:

```bash
sele run "your task" -p my-profile
```

### 2. Combining Multiple Skills

You can combine multiple skills for complementary behaviors:

```yaml
loop:
  skills:
    enabled: true
    skills: [reflexion, context_manager]
    skill_settings:
      reflexion:
        reflection_threshold: 3
        max_reflections: 2
      context_manager:
        max_context_chars: 8000
        compression_ratio: 0.5
```

### 3. Creating a Custom Skill

See `custom_skill_example.py` for a complete example of a custom skill that tracks progress.

To use it:

1. Copy the skill code to your project
2. Register it with `@skill("progress_tracker")`
3. Enable it in your profile:

```yaml
loop:
  skills:
    enabled: true
    skills: [progress_tracker]
```

### 4. Bundled Skill Profiles

sele includes several pre-configured profiles with skills:

- `reflexion-ollama` — Enables reflexion for self-improvement
- `context-managed-ollama` — Enables context management for long tasks
- `skills-combined-ollama` — Combines reflexion and context management

Try them:

```bash
sele run "explore this directory" -p reflexion-ollama
sele run "write a long document" -p context-managed-ollama
```

## Skill Lifecycle

Skills have four lifecycle hooks:

1. **`initialize(ctx)`** — Called once before the loop starts
2. **`before_step(step_index, memory)`** — Called before each model step
3. **`after_step(step_index, response, tool_results)`** — Called after each model step
4. **`on_loop_end(final_text, total_steps)`** — Called when the loop terminates

## Built-in Skills

### Reflexion

Enables self-reflection and iterative improvement. Tracks progress and injects reflection prompts when stuck.

**Configuration:**

```yaml
skill_settings:
  reflexion:
    reflection_threshold: 3  # Steps before reflection
    max_reflections: 2       # Max reflection cycles
```

### Context Manager

Manages context window to prevent exceeding model limits.

**Configuration:**

```yaml
context_window: 8000  # Max context size
skill_settings:
  context_manager:
    max_context_chars: 8000
    compression_ratio: 0.5
```

## Advanced Configuration

### Breadth and Depth

Control the search space:

```yaml
loop:
  skills:
    enabled: true
    skills: [reflexion]
    breadth: 3  # Explore 3 parallel branches
    depth: 5    # Maximum 5 reasoning steps
```

### Custom Loop Strategy

Override the loop strategy via skills:

```yaml
loop:
  kind: tool_loop
  skills:
    enabled: true
    skills: [my_custom_loop]
    loop_strategy: tree_search  # Use custom loop
```

## Testing Skills

Test your skills using pytest:

```python
from sele.skills import BaseSkill
from sele.types import Message, ModelResponse

def test_my_skill():
    skill = MySkill()
    skill.initialize(None)
    
    memory = [Message(role="user", content="test")]
    skill.before_step(0, memory)
    
    response = ModelResponse(content="response")
    skill.after_step(0, response, [])
    
    result = skill.on_loop_end("final", 1)
    assert result is not None
```

See `../../tests/test_skills.py` for more examples.

## Next Steps

1. Read `../../SKILLS.md` for comprehensive documentation
2. Explore the built-in skills in `../../src/sele/skills/`
3. Create your own skill using `custom_skill_example.py` as a template
4. Try the bundled profiles: `reflexion-ollama`, `context-managed-ollama`, `skills-combined-ollama`
