# Custom Model Adapters

Add support for new model backends by implementing the ModelAdapter interface.

## Interface Definition

```python
from sele.interfaces import ModelAdapter
from sele.types import Message, ModelResponse, ToolSpec


class MyAdapter(ModelAdapter):
    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse:
        # Convert messages to model's format
        # Call the model
        # Convert response back to ModelResponse
        pass
```

## Example: Hugging Face Transformers

```python
# src/sele/models/transformers_native.py
from __future__ import annotations

from typing import Any

from transformers import AutoModelForCausalLM, AutoTokenizer

from sele.config import ModelConfig
from sel.interfaces import ModelAdapter
from sele.models._chat_compat import (
    msg_to_openai_dict,
    parse_openai_choice,
    tool_to_openai_dict,
)
from sele.types import Message, ModelResponse, ToolSpec


class TransformersNativeAdapter(ModelAdapter):
    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.tokenizer = AutoTokenizer.from_pretrained(config.model)
        self.model = AutoModelForCausalLM.from_pretrained(config.model)

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse:
        # Convert messages to chat format
        text = self.tokenizer.apply_chat_template(
            [msg_to_openai_dict(m) for m in messages],
            tokenize=False,
            add_generation_prompt=True,
        )

        # Tokenize
        inputs = self.tokenizer(text, return_tensors="pt")

        # Generate
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.config.max_tokens or 512,
            temperature=self.config.temperature or 0.7,
            do_sample=True,
        )

        # Decode
        generated = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:])

        # Return response (tool calling would require more work)
        return ModelResponse(content=generated)
```

Register in `pyproject.toml`:

```toml
[project.entry-points."sele.adapters"]
transformers_native = "sele.models.transformers_native:TransformersNativeAdapter"
```

Use in profile:

```yaml
model:
  adapter: transformers_native
  model: Qwen/Qwen2.5-7B-Instruct
  max_tokens: 1024
  temperature: 0.2
```

## Example: Anthropic Claude

```python
# src/sele/models/anthropic.py
import anthropic

from sele.config import ModelConfig
from sel.interfaces import ModelAdapter
from sele.types import Message, ModelResponse, ToolSpec


class AnthropicAdapter(ModelAdapter):
    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        *,
        tool_choice: str | None = None,
    ) -> ModelResponse:
        # Convert messages to Anthropic format
        system = next((m.content for m in messages if m.role == "system"), "")
        msgs = [m for m in messages if m.role != "system"]

        # Call Anthropic
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens or 1024,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in msgs],
            temperature=self.config.temperature or 0.7,
        )

        # Return response
        return ModelResponse(content=response.content[0].text)
```

## Tool Calling Support

For native tool calling, you need to:

1. Convert `ToolSpec` to model's format
2. Parse tool calls from model response
3. Handle tool_choice parameter

See `src/sele/models/_chat_compat.py` for helper functions used by existing adapters.

## Caching

For expensive model loading, implement caching:

```python
from functools import lru_cache

@lru_cache(maxsize=8)
def _load_model(model_path: str, **kwargs):
    return load_expensive_model(model_path, **kwargs)
```

## Configuration

Add adapter-specific config fields to `ModelConfig` in `src/sele/config.py`:

```python
class ModelConfig(_Lax):
    # ... existing fields ...
    my_adapter_param: str | None = None
```

## Testing

Test your adapter with a mock or fake model:

```python
# tests/test_my_adapter.py
class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def generate(self, **kwargs):
        return ["test output"]

def test_adapter_uses_config():
    config = ModelConfig(adapter="my_adapter", model="test")
    adapter = MyAdapter(config)
    assert adapter.model is not None
```

## See Also

- ARCHITECTURE.md - Adapter interface definition
- Existing adapters in `src/sele/models/`
- _chat_compat.py for OpenAI-shape conversion helpers
