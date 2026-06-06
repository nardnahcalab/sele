# Skills in sele

Skills are pluggable components that augment the agent loop with specialized reasoning strategies, context management, and control over the breadth and depth of the agent's search space.

## Overview

Skills allow you to:

- **Modify the agent loop strategy** — Use custom loop strategies like reflexion, tree search, or beam search
- **Control context window** — Manage context size and enable compression for long-running tasks
- **Configure search space** — Control the breadth (parallel branches) and depth (reasoning steps) of exploration
- **Provide specialized tools or prompts** — Inject domain-specific capabilities

## Architecture

Skills are registered in the `sele.skills` entry point group and are instantiated by the builder when enabled in a profile. Each skill implements the `Skill` protocol with four lifecycle hooks:

1. **`initialize(ctx)`** — Called once before the loop starts
2. **`before_step(step_index, memory)`** — Called before each model step
3. **`after_step(step_index, response, tool_results)`** — Called after each model step
4. **`on_loop_end(final_text, total_steps)`** — Called when the loop terminates

## Configuration

Enable skills in your profile's `loop` section:

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
  max_steps: 25
  skills:
    enabled: true
    skills: [reflexion, context_manager]
    breadth: 1          # Number of parallel branches
    depth: 1            # Maximum reasoning depth
    context_window: 8000  # Max context size (chars)
    context_compression: false
    skill_settings:
      reflexion:
        reflection_threshold: 3
        max_reflections: 2
      context_manager:
        max_context_chars: 8000
        compression_ratio: 0.5
memory: full_history
sandbox:
  kind: host_direct
  cwd: .
approval: confirm_destructive
tools: [shell, fs_read, fs_write]
tracer: jsonl
system_prompt: |
  You are a careful agent.
```

## Built-in Skills

### Reflexion

The `reflexion` skill enables self-reflection and iterative improvement. It tracks progress and injects reflection prompts directly into the agent's memory when it appears stuck.

**Configuration:**

```yaml
loop:
  skills:
    enabled: true
    skills: [reflexion]
    skill_settings:
      reflexion:
        reflection_threshold: 3  # Trigger reflection after N steps without progress
        max_reflections: 2       # Maximum reflection cycles
```

**How it works:**

1. Stores a reference to `ctx.memory` during `initialize()`
2. Tracks response length as a proxy for progress
3. Detects when progress stalls (same response length for N steps)
4. Appends a `role="user"` reflection prompt into memory to encourage re-planning
5. Limits the number of reflection cycles to prevent infinite loops

### Context Manager

The `context_manager` skill manages the agent's context window to prevent exceeding model limits by trimming older messages.

**Configuration:**

```yaml
loop:
  skills:
    enabled: true
    skills: [context_manager]
    context_window: 8000  # Max context size
    skill_settings:
      context_manager:
        max_context_chars: 8000
        compression_ratio: 0.5  # Keep 50% of old messages after trim
```

**How it works:**

1. Stores a reference to `ctx.memory` during `initialize()`
2. Monitors total context size (sum of message character lengths)
3. When `max_context_chars` is exceeded, trims the oldest non-system messages
4. Preserves the system prompt and inserts a notice indicating how many messages were trimmed
5. Avoids splitting tool-call / tool-result pairs at the trim boundary
6. Can re-trigger on subsequent steps if context grows again

## Writing Custom Skills

Create a custom skill by subclassing `BaseSkill`:

```python
from sele import skill
from sele.skills import BaseSkill

@skill("my_skill")
class MySkill(BaseSkill):
    name = "my_skill"
    
    def initialize(self, ctx):
        """Called once before the loop starts."""
        # Store ctx.memory to modify the conversation in later hooks
        self._memory = ctx.memory
        print(f"Initializing {self.name}")
    
    def before_step(self, step_index, memory):
        """Called before each model step."""
        print(f"Step {step_index}: {len(memory)} messages in memory")
        # Can append to self._memory to inject prompts, or
        # mutate self._memory._messages to trim old messages
    
    def after_step(self, step_index, response, tool_results):
        """Called after each model step completes."""
        print(f"Step {step_index} completed")
        # You can inspect the step outcome
        # e.g., evaluate progress, trigger re-planning
    
    def on_loop_end(self, final_text, total_steps):
        """Called when the loop terminates."""
        # You can post-process the final output
        return final_text + f"\n[Completed in {total_steps} steps]"
```

### In-tree Registration

Register skills in your sele source tree using the `@skill` decorator:

```python
from sele import skill
from sele.skills import BaseSkill

@skill("my_skill")
class MySkill(BaseSkill):
    name = "my_skill"
    # ... implement hooks ...
```

### Out-of-tree Registration

Register skills from external packages via entry points in `pyproject.toml`:

```toml
[project.entry-points."sele.skills"]
my_skill = "my_pkg.skills:MySkill"
```

Then use in your profile:

```yaml
loop:
  skills:
    enabled: true
    skills: [my_skill]
```

## Advanced Patterns

### Breadth-First Search

Configure breadth to explore multiple branches in parallel:

```yaml
loop:
  skills:
    enabled: true
    skills: [reflexion]
    breadth: 3  # Explore 3 parallel branches
```

### Depth-Limited Search

Configure depth to limit reasoning steps:

```yaml
loop:
  skills:
    enabled: true
    skills: [reflexion]
    depth: 5  # Maximum 5 reasoning steps
```

### Custom Loop Strategy

Override the loop strategy via skills:

```yaml
loop:
  kind: tool_loop  # Default strategy
  skills:
    enabled: true
    skills: [my_custom_loop]
    loop_strategy: tree_search  # Override with custom strategy
```

The builder will use the `loop_strategy` from skills config if provided, allowing skills to dynamically select the loop implementation.

### Skill Composition

Combine multiple skills to get complementary behaviors:

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
```

Skills are initialized and called in order, so you can compose them for complex behaviors.

## Accessing Skills from Loops

Loops can access skills through the `LoopContext`. `LoopBase` provides:

- **`step_once()`** — automatically calls `before_step` and `after_step` hooks
- **`_finalize(last_text)`** — runs `on_loop_end` on all skills and returns the final text

```python
class MyLoop(LoopBase):
    def run(self, task: str) -> str:
        self.add_user(task)
        last_text = ""
        for _ in range(self.ctx.max_steps):
            text, calls, _ = self.step_once()
            last_text = text or last_text
            if not calls:
                return self._finalize(last_text)
        return self._finalize(last_text or "(max steps reached)")
```

Both `ToolLoop` and `PlanExecuteLoop` call `_finalize()` at every return point.

## CLI Commands

### List Available Skills

```bash
sele skills
```

This displays all registered skills (built-in and from entry points).

### Run with Skills

Skills are configured via profiles, so use the normal `sele run` command:

```bash
sele run "your task" -p my-profile
```

Where `my-profile.yaml` has skills enabled.

## Examples

### Reflexion Profile

```yaml
name: reflexion-ollama
description: Llama 3.1 with reflexion skill
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
        max_reflections: 3
memory: full_history
sandbox:
  kind: host_direct
  cwd: .
approval: confirm_destructive
tools: [shell, fs_read, fs_write]
tracer: jsonl
system_prompt: |
  You are a careful agent that can reflect on your progress.
  When you get stuck, think about what you've tried and what to try next.
```

### Context-Managed Profile

```yaml
name: context-managed-ollama
description: Llama 3.1 with context management
model:
  adapter: openai_compat
  base_url: http://localhost:11434/v1
  model: llama3.1:8b
  api_key: ollama
protocol: react_text
loop:
  kind: tool_loop
  max_steps: 100
  skills:
    enabled: true
    skills: [context_manager]
    context_window: 4096
    skill_settings:
      context_manager:
        max_context_chars: 4096
        compression_ratio: 0.4
memory: full_history
sandbox:
  kind: host_direct
  cwd: .
approval: confirm_destructive
tools: [shell, fs_read, fs_write]
tracer: jsonl
system_prompt: |
  You are a careful agent working on long-running tasks.
```

## Testing Skills

Test your skills using the `BaseSkill` class and mock objects:

```python
from sele.skills import BaseSkill
from sele.types import Message, ModelResponse

class TestSkill(BaseSkill):
    name = "test_skill"
    
    def __init__(self):
        self.init_called = False
    
    def initialize(self, ctx):
        self.init_called = True

# Test
skill = TestSkill()
skill.initialize(None)
assert skill.init_called is True
```

See `tests/test_skills.py` for more examples.

## Troubleshooting

### Skill not found

If you get "no skills registered as 'my_skill'", check:

1. The skill is registered with `@skill("my_skill")`
2. The skill module is imported (entry points are lazy-loaded)
3. The skill name matches exactly in your profile

### Skills not being called

Check that:

1. `loop.skills.enabled: true` in your profile
2. The skill name is in `loop.skills.skills` list
3. The loop class extends `LoopBase` (which calls the hooks)

### Context not available in skill

The `LoopContext` is passed to `initialize()`. Store references to components you need:

```python
def initialize(self, ctx):
    self.adapter = ctx.adapter
    self.memory = ctx.memory
    self.tools = ctx.tools
```

## Future Enhancements

Planned skill features:

- **Beam search** — Explore multiple branches with scoring
- **Tree search** — Structured exploration with backtracking
- **Retrieval** — Augment memory with external knowledge
- **Caching** — Cache tool results and model responses
- **Monitoring** — Track metrics and performance
- **Adaptive strategies** — Dynamically adjust based on progress
