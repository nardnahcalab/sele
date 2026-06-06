"""sele command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import skills to register them
import sele.skills  # noqa: F401
from sele import __version__
from sele.builder import build_loop
from sele.config import (
    EvalConfig,
    SandboxConfig,
    list_bundled_profiles,
    load_profile,
    resolve_profile_path,
)
from sele.eval import EvalRunner
from sele.registry import REGISTRY

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="sele — a pluggable agent harness for open-source models.",
)
profiles_app = typer.Typer(no_args_is_help=True, help="Inspect bundled and user profiles.")
trace_app = typer.Typer(no_args_is_help=True, help="Inspect run traces.")
app.add_typer(profiles_app, name="profiles")
app.add_typer(trace_app, name="trace")

console = Console()
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"sele {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    pass


def _override_sandbox_cwd(profile, cwd: str | None):
    if cwd:
        profile.sandbox = SandboxConfig(**{**profile.sandbox.model_dump(), "cwd": cwd})
    return profile


@app.command("run")
def run(
    task: str = typer.Argument(..., help="The task for the agent."),
    profile: str = typer.Option("local-ollama", "--profile", "-p", help="Profile name or path."),
    cwd: str | None = typer.Option(None, "--cwd", help="Override sandbox cwd."),
    max_steps: int | None = typer.Option(None, "--max-steps", help="Override profile max_steps."),
) -> None:
    """Run the agent on a single task and exit."""

    prof = _override_sandbox_cwd(load_profile(profile), cwd)
    if max_steps is not None:
        prof.loop.max_steps = max_steps

    loop = build_loop(prof)
    loop.ctx.tracer.start(prof.name, task)
    try:
        result = loop.run(task)
    except KeyboardInterrupt:
        loop.ctx.tracer.end("interrupted")
        raise typer.Exit(code=130) from None
    except Exception as exc:  # noqa: BLE001
        loop.ctx.tracer.end("error", str(exc))
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from None
    loop.ctx.tracer.end("ok")
    console.print(Panel(result or "(no output)", title="result", border_style="green"))
    trace_path = getattr(loop.ctx.tracer, "path", None)
    if trace_path is not None:
        err_console.print(f"[dim]trace: {trace_path}[/dim]")


@app.command("chat")
def chat(
    profile: str = typer.Option("local-ollama", "--profile", "-p", help="Profile name or path."),
    cwd: str | None = typer.Option(None, "--cwd", help="Override sandbox cwd."),
) -> None:
    """Interactive REPL. Type a task; the agent runs to completion, then prompts again."""

    prof = _override_sandbox_cwd(load_profile(profile), cwd)
    console.print(f"[bold]sele chat[/bold] · profile={prof.name} · ctrl-d to exit")

    while True:
        try:
            line = console.input("[cyan]you ›[/cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if not line:
            continue
        if line in {":quit", ":q", ":exit"}:
            return

        # Each turn gets its own loop+tracer so memory across turns is clean.
        # (Persistent multi-turn memory will land with v0.2 memory backends.)
        loop = build_loop(prof)
        loop.ctx.tracer.start(prof.name, line)
        try:
            result = loop.run(line)
            loop.ctx.tracer.end("ok")
        except KeyboardInterrupt:
            loop.ctx.tracer.end("interrupted")
            console.print("[yellow](interrupted)[/yellow]")
            continue
        except Exception as exc:  # noqa: BLE001
            loop.ctx.tracer.end("error", str(exc))
            err_console.print(f"[red]error:[/red] {exc}")
            continue
        console.print(Panel(result or "(no output)", title="sele", border_style="green"))


@app.command("eval")
def eval_cmd(
    benchmark: str = typer.Argument(..., help="Path to benchmark file (JSONL)."),
    profile: str = typer.Option("local-ollama", "--profile", "-p", help="Profile name or path."),
    max_tasks: int | None = typer.Option(None, "--max-tasks", help="Limit number of tasks to run."),
    timeout: float = typer.Option(300.0, "--timeout", help="Per-task timeout in seconds."),
    continue_on_error: bool = typer.Option(
        False, "--continue-on-error", help="Keep running after task failures."
    ),
    output_dir: str = typer.Option(".sele/eval", "--output-dir", help="Directory for results."),
) -> None:
    """Run the agent on a benchmark and collect results."""

    config = EvalConfig(
        benchmark=benchmark,
        output_dir=output_dir,
        max_tasks=max_tasks,
        timeout=timeout,
        continue_on_error=continue_on_error,
    )

    runner = EvalRunner(profile, config)
    results = runner.run()
    runner.print_summary(results)


# ------------------------------------------------------------------ profiles


@profiles_app.command("list")
def profiles_list() -> None:
    """List bundled profiles."""

    table = Table(title="bundled profiles")
    table.add_column("name", style="bold")
    table.add_column("path", style="dim")
    for name in list_bundled_profiles():
        try:
            path = str(resolve_profile_path(name))
        except FileNotFoundError:
            path = "(missing)"
        table.add_row(name, path)
    console.print(table)


@profiles_app.command("show")
def profiles_show(name: str = typer.Argument(..., help="Profile name or path.")) -> None:
    """Print a profile's resolved YAML."""

    path = resolve_profile_path(name)
    console.print(Panel(path.read_text(), title=str(path), border_style="cyan"))


# ------------------------------------------------------------------ skills


@app.command("skills")
def skills_list() -> None:
    """List available skills."""

    available_skills = REGISTRY.list("skills")
    if not available_skills:
        console.print("[yellow]No skills registered.[/yellow]")
        return

    table = Table(title="available skills")
    table.add_column("name", style="bold")
    for skill_name in available_skills:
        table.add_row(skill_name)
    console.print(table)


# ------------------------------------------------------------------ traces


@trace_app.command("show")
def trace_show(
    run_id_or_path: str = typer.Argument(..., help="Run id or path to a .jsonl trace file."),
    dir: str = typer.Option(".sele/runs", "--dir", help="Default trace directory."),
) -> None:
    """Pretty-print a JSONL trace."""

    candidate = Path(run_id_or_path)
    if not candidate.exists():
        candidate = Path(dir) / f"{run_id_or_path}.jsonl"
    if not candidate.exists():
        err_console.print(f"[red]trace not found:[/red] {run_id_or_path}")
        raise typer.Exit(code=1)
    for line in candidate.read_text().splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            console.print(line)
            continue
        kind = event.get("kind", "?")
        console.rule(f"[bold]{kind}[/bold] · t={event.get('t')}")
        console.print_json(data=event)


if __name__ == "__main__":  # pragma: no cover
    app()
