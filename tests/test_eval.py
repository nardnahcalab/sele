"""Tests for the evaluation runner."""

from __future__ import annotations

import json

from sele.config import EvalConfig
from sele.eval import EvalRunner, TaskResult


def test_load_benchmark(tmp_path) -> None:
    benchmark_file = tmp_path / "benchmark.jsonl"
    benchmark_file.write_text(
        '{"id": "task1", "task": "list files"}\n'
        '{"id": "task2", "task": "read README"}\n'
    )

    config = EvalConfig(benchmark=str(benchmark_file), output_dir=str(tmp_path / "output"))
    runner = EvalRunner("local-ollama", config)
    tasks = runner.load_benchmark()

    assert len(tasks) == 2
    assert tasks[0]["id"] == "task1"
    assert tasks[0]["task"] == "list files"
    assert tasks[1]["id"] == "task2"
    assert tasks[1]["task"] == "read README"


def test_load_benchmark_with_max_tasks(tmp_path) -> None:
    benchmark_file = tmp_path / "benchmark.jsonl"
    benchmark_file.write_text(
        '{"id": "task1", "task": "list files"}\n'
        '{"id": "task2", "task": "read README"}\n'
        '{"id": "task3", "task": "write file"}\n'
    )

    config = EvalConfig(
        benchmark=str(benchmark_file),
        output_dir=str(tmp_path / "output"),
        max_tasks=2,
    )
    runner = EvalRunner("local-ollama", config)
    tasks = runner.load_benchmark()

    assert len(tasks) == 2


def test_load_benchmark_missing_file(tmp_path) -> None:
    config = EvalConfig(benchmark=str(tmp_path / "nonexistent.jsonl"), output_dir=str(tmp_path / "output"))
    runner = EvalRunner("local-ollama", config)

    try:
        runner.load_benchmark()
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass


def test_load_benchmark_invalid_json(tmp_path) -> None:
    benchmark_file = tmp_path / "benchmark.jsonl"
    benchmark_file.write_text('{"id": "task1", "task": "list files"}\ninvalid json\n')

    config = EvalConfig(benchmark=str(benchmark_file), output_dir=str(tmp_path / "output"))
    runner = EvalRunner("local-ollama", config)

    try:
        runner.load_benchmark()
        raise AssertionError("expected ValueError for invalid JSON")
    except ValueError:
        pass


def test_task_result_dataclass() -> None:
    result = TaskResult(
        task_id="task1",
        task="list files",
        success=True,
        output="file1.txt\nfile2.txt",
        error=None,
        duration=1.5,
        steps=3,
    )

    assert result.task_id == "task1"
    assert result.success
    assert result.duration == 1.5
    assert result.steps == 3


def test_write_results(tmp_path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = EvalConfig(benchmark="dummy.jsonl", output_dir=str(output_dir))
    runner = EvalRunner("local-ollama", config)

    results = [
        TaskResult(
            task_id="task1",
            task="list files",
            success=True,
            output="file1.txt",
            error=None,
            duration=1.0,
            steps=2,
        ),
        TaskResult(
            task_id="task2",
            task="read README",
            success=False,
            output="",
            error="file not found",
            duration=0.5,
            steps=1,
        ),
    ]

    runner.write_results(results)

    output_file = output_dir / "local-ollama_results.jsonl"
    assert output_file.exists()

    lines = output_file.read_text().splitlines()
    assert len(lines) == 2

    result1 = json.loads(lines[0])
    assert result1["task_id"] == "task1"
    assert result1["success"] is True
    assert result1["duration"] == 1.0

    result2 = json.loads(lines[1])
    assert result2["task_id"] == "task2"
    assert result2["success"] is False
    assert result2["error"] == "file not found"


def test_print_summary(capsys) -> None:
    results = [
        TaskResult(
            task_id="task1",
            task="list files",
            success=True,
            output="file1.txt",
            error=None,
            duration=1.0,
            steps=2,
        ),
        TaskResult(
            task_id="task2",
            task="read README",
            success=False,
            output="",
            error="file not found",
            duration=0.5,
            steps=1,
        ),
    ]

    config = EvalConfig(benchmark="dummy.jsonl", output_dir="/tmp")
    runner = EvalRunner("local-ollama", config)
    runner.print_summary(results)

    captured = capsys.readouterr()
    assert "Total tasks:   2" in captured.out
    assert "Passed:        1" in captured.out
    assert "Failed:        1" in captured.out
    assert "Avg duration:" in captured.out
