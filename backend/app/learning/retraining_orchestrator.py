"""Orchestrate outcome-based model retraining and score refresh."""

from __future__ import annotations

from typing import Any

from app.db.mongo import MongoDatabase
from app.learning.feedback_collector import FeedbackCollector
from app.learning.performance_monitor import PerformanceMonitor
from app.learning.repository import LearningRepository
from app.ml.conversion.service import ConversionService
from app.ml.scoring_persistence_service import ScoringPersistenceService
from app.schemas.learning import PredictionAccuracy, RetrainResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RetrainingOrchestrator:
    def __init__(
        self,
        db: MongoDatabase,
        conversion_service: ConversionService,
        scoring_service: ScoringPersistenceService | None = None,
    ) -> None:
        self._db = db
        self._conversion = conversion_service
        self._scoring = scoring_service
        self._feedback = FeedbackCollector(db)
        self._repo = LearningRepository(db)
        self._monitor = PerformanceMonitor(db)

    def build_and_persist_labels(self, *, limit: int = 5000) -> tuple[int, int, dict[str, int]]:
        records = self._feedback.collect_entity_outcomes(limit=limit)
        distribution: dict[str, int] = {}
        for record in records:
            bucket = record.get("label_source", "unknown")
            distribution[bucket] = distribution.get(bucket, 0) + 1

        persisted = self._repo.bulk_upsert_outcome_labels(records) if records else 0
        return len(records), persisted, distribution

    def retrain(
        self,
        *,
        label_source: str = "outcomes",
        min_outcome_labels: int = 5,
        refresh_scores: bool = True,
    ) -> RetrainResponse:
        outcome_labels = self._repo.outcome_labels_by_lead_id()
        if len(outcome_labels) < min_outcome_labels:
            built, _, _ = self.build_and_persist_labels()
            outcome_labels = self._repo.outcome_labels_by_lead_id()
            logger.info("Built %d outcome labels before retrain", built)

        if label_source == "outcomes" and len(outcome_labels) < min_outcome_labels:
            return RetrainResponse(
                message=(
                    f"Insufficient outcome labels for retraining "
                    f"(need {min_outcome_labels}, have {len(outcome_labels)})"
                ),
                label_source=label_source,
                records_used=0,
                outcome_labels_used=len(outcome_labels),
            )

        train_result = self._conversion.train(
            label_source=label_source,
            outcome_labels=outcome_labels if label_source != "synthetic" else None,
        )

        accuracy = self._monitor.compute_prediction_accuracy()
        scores_refreshed = False
        if refresh_scores and self._scoring:
            try:
                self._scoring.build_all()
                scores_refreshed = True
            except Exception as exc:
                logger.warning("Score refresh after retrain failed: %s", exc)

        run_id = None
        if self._conversion._scoring_repo:
            runs = self._repo.list_model_runs(model_name="lead_conversion", limit=1)
            if runs:
                run_id = runs[0].get("run_id")

        return RetrainResponse(
            message="Conversion model retrained with outcome feedback",
            run_id=run_id,
            label_source=label_source,
            records_used=train_result.records_used,
            outcome_labels_used=len(outcome_labels),
            best_model=train_result.best_model,
            test_metrics=train_result.test_metrics,
            prediction_accuracy=accuracy,
            scores_refreshed=scores_refreshed,
        )
