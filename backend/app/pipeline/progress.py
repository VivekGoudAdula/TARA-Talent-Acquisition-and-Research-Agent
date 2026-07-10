"""In-memory live progress for pipeline runs (polled by the admin UI)."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any


class LivePipelineProgress:
    """Thread-safe tracker for the active pipeline run."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.is_running = False
            self.run_id: str | None = None
            self.pipeline_type: str | None = None
            self.started_at: datetime | None = None
            self.current_step: str | None = None
            self.success: bool | None = None
            self.steps: list[dict[str, Any]] = []

    def begin(self, *, run_id: str, pipeline_type: str, step_names: list[str]) -> None:
        with self._lock:
            self.is_running = True
            self.run_id = run_id
            self.pipeline_type = pipeline_type
            self.started_at = datetime.utcnow()
            self.current_step = None
            self.success = None
            self.steps = [{"step": name, "status": "pending", "detail": None, "duration_ms": 0} for name in step_names]

    def start_step(self, name: str) -> None:
        with self._lock:
            self.current_step = name
            for step in self.steps:
                if step["step"] == name:
                    step["status"] = "running"
                    break

    def complete_step(
        self,
        name: str,
        *,
        status: str,
        detail: str | None = None,
        duration_ms: int = 0,
    ) -> None:
        with self._lock:
            for step in self.steps:
                if step["step"] == name:
                    step["status"] = status
                    step["detail"] = detail
                    step["duration_ms"] = duration_ms
                    break
            if self.current_step == name:
                self.current_step = None

    def finish(self, *, success: bool) -> None:
        with self._lock:
            self.is_running = False
            self.current_step = None
            self.success = success

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "is_running": self.is_running,
                "run_id": self.run_id,
                "pipeline_type": self.pipeline_type,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "current_step": self.current_step,
                "success": self.success,
                "steps": [dict(s) for s in self.steps],
            }


live_pipeline_progress = LivePipelineProgress()


def subset_step_names(*, target: str, train_models: bool) -> list[str]:
    steps: list[str] = []
    if target in ("external", "both"):
        steps.extend(["external_enrich", "external_analytics", "external_intelligence"])
    if target in ("internal", "both"):
        steps.append("internal_build_all")
    steps.append("behaviour_summary")
    if train_models:
        steps.extend(["ml_dataset", "repayment_train"])
        if target in ("external", "both"):
            steps.append("conversion_train")
        steps.append("scoring_persist")
    steps.append("explainability")
    return steps
