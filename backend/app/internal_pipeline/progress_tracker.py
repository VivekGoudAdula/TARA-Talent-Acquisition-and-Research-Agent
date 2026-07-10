"""In-memory tracker for pipeline run progress and failures."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class PipelineRunState:
    """Mutable state for the current or most recent pipeline run."""

    is_running: bool = False
    total: int = 0
    completed: int = 0
    failed_customer_ids: list[UUID] = field(default_factory=list)
    succeeded_customer_ids: list[UUID] = field(default_factory=list)


class PipelineProgressTracker:
    """
    Thread-safe tracker for pipeline execution.

    Persists failed customer IDs across runs so they can be retried via build-one.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = PipelineRunState()

    def start_run(self, total: int) -> None:
        with self._lock:
            self._state.is_running = True
            self._state.total = total
            self._state.completed = 0
            self._state.failed_customer_ids = []
            self._state.succeeded_customer_ids = []

    def record_success(self, customer_id: UUID) -> None:
        with self._lock:
            self._state.completed += 1
            self._state.succeeded_customer_ids.append(customer_id)
            if customer_id in self._state.failed_customer_ids:
                self._state.failed_customer_ids.remove(customer_id)

    def record_failure(self, customer_id: UUID) -> None:
        with self._lock:
            self._state.completed += 1
            if customer_id not in self._state.failed_customer_ids:
                self._state.failed_customer_ids.append(customer_id)

    def finish_run(self) -> PipelineRunState:
        with self._lock:
            self._state.is_running = False
            return PipelineRunState(
                is_running=False,
                total=self._state.total,
                completed=self._state.completed,
                failed_customer_ids=list(self._state.failed_customer_ids),
                succeeded_customer_ids=list(self._state.succeeded_customer_ids),
            )

    def get_failed_customer_ids(self) -> list[UUID]:
        with self._lock:
            return list(self._state.failed_customer_ids)

    def is_running(self) -> bool:
        with self._lock:
            return self._state.is_running

    def clear_failures(self) -> None:
        with self._lock:
            self._state.failed_customer_ids = []
