"""Evaluation runner for agent benchmarks."""

from __future__ import annotations

import json
import signal
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from time import time

from sele.builder import build_loop
from sele.config import EvalConfig, load_profile


@dataclass
class TaskResult:
    """Result of running a single task."""

    task_id: str
    task: str
    success: bool
    output: str
    error: str | None
    duration: float
    steps: int


class EvalRunner:
    """Run the agent on a benchmark and collect results."""

    def __init__(self, profile_name: str, config: EvalConfig):
        self.profile_name = profile_name
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_benchmark(self) -> list[dict]:
        """Load benchmark tasks from JSONL file."""
        path = Path(self.config.benchmark)
        if not path.exists():
            raise FileNotFoundError(f"benchmark file not found: {path}")

        tasks = []
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                task = json.loads(line)
                tasks.append(task)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON in benchmark: {exc}") from exc

        if self.config.max_tasks:
            tasks = tasks[: self.config.max_tasks]

        return tasks

    def run_task(self, task: dict, task_id: str) -> TaskResult:
        """Run a single task and return the result."""
        task_text = task.get("task", "")
        if not task_text:
            return TaskResult(
                task_id=task_id,
                task="",
                success=False,
                output="",
                error="task has no 'task' field",
                duration=0.0,
                steps=0,
            )

        start = time()
        try:
            profile = load_profile(self.profile_name)
            loop = build_loop(profile)

            # Set up timeout
            def timeout_handler(signum, frame):
                raise FutureTimeoutError("task timed out")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(self.config.timeout))

            try:
                result = loop.run(task_text)
                steps = len([e for e in loop.ctx.memory.view() if e["role"] == "assistant"])
                success = True
                error = None
            except FutureTimeoutError:
                result = ""
                steps = 0
                success = False
                error = "task timed out"
            except Exception as exc:  # noqa: BLE001
                result = ""
                steps = 0
                success = False
                error = str(exc)
            finally:
                signal.alarm(0)  # Cancel alarm

        except Exception as exc:  # noqa: BLE001
            result = ""
            steps = 0
            success = False
            error = f"failed to build loop: {exc}"

        duration = time() - start
        return TaskResult(
            task_id=task_id,
            task=task_text,
            success=success,
            output=result,
            error=error,
            duration=duration,
            steps=steps,
        )

    def run(self) -> list[TaskResult]:
        """Run all tasks in the benchmark."""
        tasks = self.load_benchmark()
        results = []

        for idx, task in enumerate(tasks):
            task_id = task.get("id", str(idx))
            print(f"[{idx + 1}/{len(tasks)}] Running task {task_id}...")

            result = self.run_task(task, task_id)
            results.append(result)

            status = "✓" if result.success else "✗"
            print(f"  {status} {result.duration:.2f}s, {result.steps} steps")
            if not result.success:
                print(f"    error: {result.error}")

            if not result.success and not self.config.continue_on_error:
                print("Stopping due to task failure (use --continue-on-error to continue)")
                break

        # Write results
        self.write_results(results)
        return results

    def write_results(self, results: list[TaskResult]) -> None:
        """Write results to JSONL file."""
        output_path = self.output_dir / f"{self.profile_name}_results.jsonl"
        with output_path.open("w") as f:
            for r in results:
                f.write(
                    json.dumps(
                        {
                            "task_id": r.task_id,
                            "task": r.task,
                            "success": r.success,
                            "output": r.output,
                            "error": r.error,
                            "duration": r.duration,
                            "steps": r.steps,
                        }
                    )
                    + "\n"
                )
        print(f"\nResults written to {output_path}")

    def print_summary(self, results: list[TaskResult]) -> None:
        """Print a summary of the evaluation."""
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed
        avg_duration = sum(r.duration for r in results) / total if total else 0
        avg_steps = sum(r.steps for r in results) / total if total else 0

        print("\n" + "=" * 50)
        print("EVALUATION SUMMARY")
        print("=" * 50)
        print(f"Total tasks:   {total}")
        print(f"Passed:        {passed} ({passed / total * 100:.1f}%)" if total else "Passed:        0")
        print(f"Failed:        {failed}")
        print(f"Avg duration:  {avg_duration:.2f}s")
        print(f"Avg steps:     {avg_steps:.1f}")
        print("=" * 50)
