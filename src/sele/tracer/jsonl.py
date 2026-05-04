"""JSONL tracer: writes one event per line to ``<dir>/<run_id>.jsonl``."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sele.config import TracerConfig
from sele.types import Step


class JsonlTracer:
    def __init__(self, config: TracerConfig | None = None):
        self.config = config or TracerConfig()
        self.run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
        self._path = Path(self.config.dir).expanduser() / f"{self.run_id}.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self._path.open("a", encoding="utf-8")
        self._t0 = time.monotonic()

    @property
    def path(self) -> Path:
        return self._path

    def _write(self, event: dict[str, Any]) -> None:
        event["t"] = round(time.monotonic() - self._t0, 4)
        event["ts"] = datetime.now(UTC).isoformat()
        self._fp.write(json.dumps(event, default=str) + "\n")
        self._fp.flush()

    def start(self, profile_name: str, task: str) -> None:
        self._write({"kind": "start", "run_id": self.run_id, "profile": profile_name, "task": task})

    def step(self, step: Step) -> None:
        self._write({"kind": "step", "step": step.model_dump()})

    def end(self, status: str, message: str | None = None) -> None:
        self._write({"kind": "end", "status": status, "message": message})
        try:
            self._fp.close()
        except Exception:  # noqa: BLE001
            pass
