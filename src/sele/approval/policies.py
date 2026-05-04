"""Human-in-the-loop approval policies."""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.prompt import Confirm

from sele.types import ToolSpec


class AutoApproval:
    """No prompts. Trust the agent."""

    def __init__(self, **_: object) -> None:
        pass

    def check(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> bool:  # noqa: ARG002
        return True


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompt(spec: ToolSpec, arguments: dict[str, Any]) -> bool:
    console = Console(stderr=True)
    console.print(f"[yellow]sele:[/yellow] approve tool [bold]{spec.name}[/bold]?")
    if arguments:
        console.print(f"  args: {arguments}")
    if not _is_interactive():
        console.print("[red]non-interactive session; denying.[/red]")
        return False
    try:
        return Confirm.ask("  approve?", default=False)
    except (EOFError, KeyboardInterrupt):
        return False


class ConfirmAllApproval:
    """Prompt before every tool invocation."""

    def __init__(self, **_: object) -> None:
        pass

    def check(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> bool:
        return _prompt(tool_spec, arguments)


class ConfirmDestructiveApproval:
    """Prompt only when the tool spec is marked ``destructive``."""

    def __init__(self, **_: object) -> None:
        pass

    def check(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> bool:
        if not tool_spec.destructive:
            return True
        return _prompt(tool_spec, arguments)
