"""Complete L1→L6 architecture flow — single orchestrated run."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.pipeline.master_orchestrator import (
    MasterPipelineOrchestrator,
    PipelineRunResult,
    PipelineStepResult,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CompleteFlowRequest:
    profile_types: list[str] | None = None
    outreach_limit: int = 10
    outreach_dry_run: bool = False
    outreach_channel: str | None = None
    min_conversion_probability: float | None = None
    process_sequences: bool = True
    build_learning_labels: bool = True
    auto_retrain: bool = True
    refresh_scores_after_retrain: bool = True


class CompleteFlowOrchestrator:
    """
    IDBI Innovate 2026 end-to-end flow:

    L1 Data (already in Mongo) → L2 Intelligence → L3 Scoring →
    L4 Engagement (+ sequences) → L5 ready (responses via webhooks) →
    L6 Learning labels + retrain → L3 score refresh
    """

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._pipeline = MasterPipelineOrchestrator(db)

    def run(self, request: CompleteFlowRequest | None = None) -> PipelineRunResult:
        req = request or CompleteFlowRequest()
        run = PipelineRunResult(
            run_id=str(uuid4()),
            pipeline_type="complete_l1_l6",
            started_at=datetime.utcnow(),
        )
        try:
            # L2 + L3
            ext = self._pipeline.run_external_pipeline(train_models=True)
            run.steps.extend(ext.steps)
            if not ext.success:
                run.success = False
                run.completed_at = datetime.utcnow()
                self._db.pipeline_runs.insert_one(run.to_doc())
                return run

            # L4 Engagement
            self._step(run, "engagement_outreach", lambda: self._run_outreach(req))
            if req.process_sequences:
                self._step(run, "engagement_sequences", lambda: self._run_sequences(req))

            # L6 Learning loop back to L3
            if req.build_learning_labels:
                self._step(run, "learning_build_labels", self._run_build_labels)
            if req.auto_retrain:
                self._step(run, "learning_retrain", lambda: self._run_retrain(req))

            run.success = all(s.status == "ok" for s in run.steps)
        except Exception as exc:
            logger.exception("Complete flow failed")
            run.steps.append(PipelineStepResult(step="complete_flow", status="error", detail=str(exc)))
            run.success = False

        run.completed_at = datetime.utcnow()
        self._db.pipeline_runs.insert_one(run.to_doc())
        return run

    def _step(self, run: PipelineRunResult, name: str, fn) -> None:
        import time

        t0 = time.perf_counter()
        try:
            detail = fn()
            ms = int((time.perf_counter() - t0) * 1000)
            run.steps.append(
                PipelineStepResult(step=name, status="ok", detail=str(detail)[:500], duration_ms=ms)
            )
        except Exception as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            run.steps.append(
                PipelineStepResult(step=name, status="error", detail=str(exc), duration_ms=ms)
            )
            raise

    def _run_outreach(self, req: CompleteFlowRequest) -> str:
        from app.engagement.service import EngagementService
        from app.engagement.voice_bridge import VoiceBridge
        from app.schemas.engagement import OutreachRequest

        svc = EngagementService(self._db, VoiceBridge())
        result = svc.run_outreach(
            OutreachRequest(
                profile_types=req.profile_types or ["External"],
                limit=req.outreach_limit,
                min_conversion_probability=req.min_conversion_probability,
                channel=req.outreach_channel,
                dry_run=req.outreach_dry_run,
                auto_sequence=True,
            )
        )
        return f"total={result.total} ok={result.succeeded} sequences={result.sequences_created}"

    def _run_sequences(self, req: CompleteFlowRequest) -> str:
        from app.engagement.service import EngagementService
        from app.engagement.voice_bridge import VoiceBridge

        svc = EngagementService(self._db, VoiceBridge())
        r = svc.process_due_sequences(dry_run=req.outreach_dry_run, limit=req.outreach_limit)
        return f"processed={r.get('processed', 0)}"

    def _run_build_labels(self) -> str:
        from app.learning.service import LearningService

        r = LearningService(self._db).build_outcome_labels(limit=5000, persist=True)
        return f"labels={r.labels_built}"

    def _run_retrain(self, req: CompleteFlowRequest) -> str:
        from app.dependencies import get_conversion_service, get_scoring_persistence_service
        from app.learning.service import LearningService
        from app.utils.database import new_session

        session = new_session()
        learning = LearningService(
            session,
            get_conversion_service(session),
            get_scoring_persistence_service(session),
        )
        result = learning.retrain_models(
            label_source="blended",
            min_outcome_labels=1,
            refresh_scores=req.refresh_scores_after_retrain,
        )
        return f"records={result.records_used} best={result.best_model}"
