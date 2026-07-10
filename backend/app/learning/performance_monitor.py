"""Monitor prediction accuracy and outreach performance."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.mongo import MongoDatabase
from app.learning.feedback_collector import FeedbackCollector
from app.learning.repository import LearningRepository
from app.schemas.learning import (
    ChannelPerformance,
    FunnelMetrics,
    PerformanceSummaryResponse,
    PredictionAccuracy,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

RETRAIN_MIN_NEW_LABELS = 10
RETRAIN_MAE_THRESHOLD = 20.0


class PerformanceMonitor:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._feedback = FeedbackCollector(db)
        self._repo = LearningRepository(db)

    def compute_prediction_accuracy(self) -> PredictionAccuracy:
        labels = self._repo.outcome_labels_by_lead_id()
        if not labels:
            labels = self._feedback.outcome_labels_by_lead_id()

        if not labels:
            return PredictionAccuracy(labeled_leads=0)

        errors: list[float] = []
        within_15 = 0
        over = 0
        under = 0

        for lead_id, actual in labels.items():
            pred_doc = self._db.conversion_predictions.find_one({"lead_id": str(lead_id)})
            if not pred_doc:
                continue
            predicted = float(pred_doc.get("conversion_probability", 0))
            error = abs(predicted - actual)
            errors.append(error)
            if error <= 15.0:
                within_15 += 1
            if predicted > actual + 5:
                over += 1
            elif predicted < actual - 5:
                under += 1

        if not errors:
            return PredictionAccuracy(labeled_leads=len(labels))

        mae = sum(errors) / len(errors)
        return PredictionAccuracy(
            labeled_leads=len(errors),
            mean_absolute_error=round(mae, 2),
            within_15_points=round(within_15 / len(errors), 4),
            over_predicted=over,
            under_predicted=under,
        )

    def should_retrain(self) -> tuple[bool, str | None]:
        label_count = self._repo.count_outcome_labels()
        if label_count < RETRAIN_MIN_NEW_LABELS:
            return False, f"Need at least {RETRAIN_MIN_NEW_LABELS} outcome labels (have {label_count})"

        accuracy = self.compute_prediction_accuracy()
        if accuracy.labeled_leads >= 5 and accuracy.mean_absolute_error is not None:
            if accuracy.mean_absolute_error > RETRAIN_MAE_THRESHOLD:
                return True, f"Prediction MAE {accuracy.mean_absolute_error:.1f} exceeds threshold {RETRAIN_MAE_THRESHOLD}"

        return True, f"{label_count} outcome labels available for retraining"

    def build_summary(self, *, capture_snapshot: bool = False) -> PerformanceSummaryResponse:
        funnel_raw = self._feedback.funnel_stats()
        channel_raw = self._feedback.channel_stats()
        accuracy = self.compute_prediction_accuracy()
        outcome_count = self._repo.count_outcome_labels()

        retrain, reason = self.should_retrain()

        funnel = FunnelMetrics(**funnel_raw)
        channels = [ChannelPerformance(**c) for c in channel_raw]

        snapshot_id = None
        if capture_snapshot:
            snapshot_id = self._repo.save_performance_snapshot(
                {
                    "funnel": funnel.model_dump(),
                    "channels": [c.model_dump() for c in channels],
                    "prediction_accuracy": accuracy.model_dump(),
                    "outcome_labels_count": outcome_count,
                }
            )

        return PerformanceSummaryResponse(
            message="Performance summary computed",
            snapshot_id=snapshot_id,
            captured_at=datetime.utcnow(),
            funnel=funnel,
            channels=channels,
            prediction_accuracy=accuracy,
            outcome_labels_count=outcome_count,
            synthetic_labels_count=max(0, 50 - outcome_count),  # subset mode baseline
            retrain_recommended=retrain,
            retrain_reason=reason,
        )

    def evaluate_holdout_metrics(
        self,
        outcome_labels: dict[str, float],
    ) -> dict[str, Any]:
        """Compare stored predictions against outcome labels after retrain."""
        accuracy = self.compute_prediction_accuracy()
        return accuracy.model_dump()
