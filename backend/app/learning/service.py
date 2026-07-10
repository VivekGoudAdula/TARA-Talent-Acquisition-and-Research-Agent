"""Layer 6 facade — feedback, monitoring, and continuous improvement."""

from __future__ import annotations

from datetime import datetime

from app.db.mongo import MongoDatabase
from app.learning.feedback_collector import FeedbackCollector
from app.learning.outcome_labels import build_label_record
from app.learning.performance_monitor import PerformanceMonitor
from app.learning.repository import LearningRepository
from app.learning.retraining_orchestrator import RetrainingOrchestrator
from app.ml.conversion.service import ConversionService
from app.ml.scoring_persistence_service import ScoringPersistenceService
from app.schemas.learning import (
    BuildOutcomeLabelsResponse,
    IngestOutcomeRequest,
    ModelRunSummary,
    OutcomeLabelRecord,
    PerformanceSnapshotResponse,
    PerformanceSummaryResponse,
    RetrainResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class LearningService:
    """Continuous Performance Improvement — Layer 6."""

    def __init__(
        self,
        db: MongoDatabase,
        conversion_service: ConversionService | None = None,
        scoring_service: ScoringPersistenceService | None = None,
    ) -> None:
        self._db = db
        self._repo = LearningRepository(db)
        self._feedback = FeedbackCollector(db)
        self._monitor = PerformanceMonitor(db)
        self._conversion = conversion_service
        self._scoring = scoring_service

    def get_performance_summary(self, *, capture_snapshot: bool = False) -> PerformanceSummaryResponse:
        summary = self._monitor.build_summary(capture_snapshot=capture_snapshot)
        summary.captured_at = datetime.utcnow()
        return summary

    def build_outcome_labels(self, *, limit: int = 5000, persist: bool = True) -> BuildOutcomeLabelsResponse:
        records = self._feedback.collect_entity_outcomes(limit=limit)
        persisted = self._repo.bulk_upsert_outcome_labels(records) if persist and records else 0
        distribution: dict[str, int] = {}
        for record in records:
            src = record.get("label_source", "unknown")
            distribution[src] = distribution.get(src, 0) + 1
        return BuildOutcomeLabelsResponse(
            message=f"Built {len(records)} outcome labels",
            labels_built=len(records),
            labels_persisted=persisted,
            label_distribution=distribution,
        )

    def ingest_outcome(self, request: IngestOutcomeRequest) -> OutcomeLabelRecord | None:
        """Called after Layer 5 captures a response — keeps labels fresh."""
        journey = self._db.onboarding_journeys.find_one({"entity_id": request.entity_id})
        handoffs = list(self._db.rm_handoffs.find({"entity_id": request.entity_id}, {"_id": 0}))
        handoffs.sort(key=lambda d: d.get("created_at") or datetime.min, reverse=True)
        handoff = handoffs[0] if handoffs else None
        lead_id = self._feedback._resolve_lead_id(request.entity_id)
        record = build_label_record(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            lead_id=lead_id,
            response_type=request.response_type or (journey or {}).get("last_response_type"),
            journey_status=request.journey_status or (journey or {}).get("status"),
            handoff_status=(handoff or {}).get("status"),
            channel=request.channel or (journey or {}).get("last_channel"),
        )
        if not record:
            return None
        self._repo.upsert_outcome_label(record)
        return OutcomeLabelRecord(**record, updated_at=datetime.utcnow())

    def retrain_models(
        self,
        *,
        label_source: str = "outcomes",
        min_outcome_labels: int = 5,
        refresh_scores: bool = True,
    ) -> RetrainResponse:
        if not self._conversion:
            return RetrainResponse(
                message="Conversion service not configured",
                label_source=label_source,
                records_used=0,
                outcome_labels_used=0,
            )
        orchestrator = RetrainingOrchestrator(
            self._db, self._conversion, self._scoring
        )
        return orchestrator.retrain(
            label_source=label_source,
            min_outcome_labels=min_outcome_labels,
            refresh_scores=refresh_scores,
        )

    def list_outcome_labels(self, *, limit: int = 100) -> list[OutcomeLabelRecord]:
        docs = self._repo.list_outcome_labels(limit=limit)
        return [OutcomeLabelRecord(**d) for d in docs]

    def list_model_runs(self, *, model_name: str | None = None, limit: int = 20) -> list[ModelRunSummary]:
        docs = self._repo.list_model_runs(model_name=model_name, limit=limit)
        return [ModelRunSummary(**d) for d in docs]

    def list_snapshots(self, *, limit: int = 20) -> list[PerformanceSnapshotResponse]:
        docs = self._repo.list_performance_snapshots(limit=limit)
        return [
            PerformanceSnapshotResponse(
                snapshot_id=d["snapshot_id"],
                captured_at=d["captured_at"],
                funnel=d["funnel"],
                channels=d.get("channels", []),
                prediction_accuracy=d["prediction_accuracy"],
                outcome_labels_count=d.get("outcome_labels_count", 0),
                notes=d.get("notes"),
            )
            for d in docs
        ]
