"""Console tracer: pretty-prints each step to stderr."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from sele.types import Step


class ConsoleTracer:
    def __init__(self, **_: object) -> None:
        self.console = Console(stderr=True)
        self.run_id = "console"

    def start(self, profile_name: str, task: str) -> None:
        self.console.rule(f"[bold]sele[/bold] · {profile_name}")
        self.console.print(Panel(task, title="task", border_style="cyan"))

    def step(self, step: Step) -> None:
        if step.response and step.response.content:
            self.console.print(
                Panel(step.response.content, title=f"step {step.index}", border_style="green")
            )
        for r in step.tool_results:
            border = "yellow" if r.ok else "red"
            head = f"tool {r.name}" + ("" if r.ok else f" — {r.error}")
            self.console.print(Panel(r.content[:2000] or "(empty)", title=head, border_style=border))

    def end(self, status: str, message: str | None = None) -> None:
        self.console.rule(f"[bold]end[/bold] · {status}")
        if message:
            self.console.print(message)
