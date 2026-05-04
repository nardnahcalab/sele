# Custom Tools

Create custom tools to extend sele's capabilities.

## In-Tree Tools

Create a tool in the sele codebase:

```python
# src/sele/tools/my_tool.py
from __future__ import annotations

from typing import Any

from sele.interfaces import Sandbox
from sele.types import ToolResult, ToolSpec


class _MyTool:
    spec = ToolSpec(
        name="my_tool",
        description="Does something useful.",
        parameters={
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "The input to process."},
            },
            "required": ["input"],
        },
        destructive=False,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        input_val = arguments.get("input")
        if not isinstance(input_val, str):
            return ToolResult(
                call_id=arguments.get("_call_id", ""),
                name=self.spec.name,
                ok=False,
                content="",
                error="input must be a string",
            )

        # Do something useful
        result = f"Processed: {input_val.upper()}"

        return ToolResult(
            call_id=arguments.get("_call_id", ""),
            name=self.spec.name,
            ok=True,
            content=result,
            error=None,
        )


my_tool = _MyTool()
```

Register in `src/sele/tools/__init__.py`:

```python
from sele.tools.my_tool import my_tool
```

Add to `pyproject.toml`:

```toml
[project.entry-points."sele.tools"]
my_tool = "sele.tools.my_tool:my_tool"
```

## Out-of-Tree Tools

Create a separate package:

```python
# my_sele_tools/tools.py
from sele.interfaces import Sandbox
from sele.types import ToolResult, ToolSpec


class _CustomTool:
    spec = ToolSpec(
        name="custom_tool",
        description="A custom tool.",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
        destructive=False,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        # Implementation
        return ToolResult(
            call_id=arguments.get("_call_id", ""),
            name="custom_tool",
            ok=True,
            content="Done",
            error=None,
        )


custom_tool = _CustomTool()
```

Register in `pyproject.toml`:

```toml
[project.entry-points."sele.tools"]
custom_tool = "my_sele_tools.tools:custom_tool"
```

Install your package:

```bash
pip install -e /path/to/my_sele_tools
```

Use in profile:

```yaml
tools: [shell, fs_read, fs_write, custom_tool]
```

## Tool Best Practices

### Descriptions

Write clear, actionable descriptions:

```python
spec = ToolSpec(
    name="git_commit",
    description="Commit changes with a message. Creates a commit if there are staged changes.",
    parameters={...},
)
```

### Parameters

Use JSON Schema for validation:

```python
spec = ToolSpec(
    name="git_commit",
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Commit message.",
                "minLength": 1,
                "maxLength": 200,
            },
            "amend": {
                "type": "boolean",
                "description": "Amend the previous commit.",
                "default": False,
            },
        },
        "required": ["message"],
    },
)
```

### Destructive Flag

Mark tools as destructive if they have side effects:

```python
spec = ToolSpec(
    name="git_push",
    destructive=True,  # Requires confirmation with confirm_destructive
    parameters={...},
)
```

### Error Handling

Return clear error messages:

```python
def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
    try:
        result = do_work(arguments)
        return ToolResult(..., ok=True, content=result, error=None)
    except PermissionError as exc:
        return ToolResult(..., ok=False, content="", error=f"Permission denied: {exc}")
    except ValueError as exc:
        return ToolResult(..., ok=False, content="", error=f"Invalid input: {exc}")
```

## Example: Database Tool

```python
class _DatabaseQuery:
    spec = ToolSpec(
        name="db_query",
        description="Execute a SQL query on the configured database.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute.",
                },
            },
            "required": ["query"],
        },
        destructive=True,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        import sqlite3

        query = arguments.get("query")
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute(query)
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                result = "\n".join(str(row) for row in rows)
            else:
                conn.commit()
                result = f"Query affected {cursor.rowcount} rows"
            conn.close()
            return ToolResult(..., ok=True, content=result, error=None)
        except Exception as exc:
            return ToolResult(..., ok=False, content="", error=str(exc))
```

## Example: Web Scraping Tool

```python
class _WebScrape:
    spec = ToolSpec(
        name="web_scrape",
        description="Scrape text content from a web page.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape."},
            },
            "required": ["url"],
        },
        destructive=False,
    )

    def __call__(self, sandbox: Sandbox, arguments: dict[str, Any]) -> ToolResult:
        from bs4 import BeautifulSoup
        import requests

        url = arguments.get("url")
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            return ToolResult(..., ok=True, content=text[:10000], error=None)
        except Exception as exc:
            return ToolResult(..., ok=False, content="", error=str(exc))
```

## See Also

- ARCHITECTURE.md - Plugin development guide
- Tool interface definition in `src/sele/interfaces.py`
