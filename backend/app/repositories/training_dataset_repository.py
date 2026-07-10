"""Repository for training_dataset collection."""

from datetime import datetime
from uuid import UUID

from typing import Any
from app.db.mongo import MongoDatabase
from app.models.training_dataset import TrainingDatasetRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TrainingDatasetRepository:
    """Data access layer for the unified ML training_dataset collection."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def replace_all(self, rows: list, commit: bool = True) -> int:
        from app.ml.dataset_builder.dataset_generator import DatasetRow
        self._db.training_dataset.delete_many({})
        if rows:
            docs = [self._to_model(row).to_doc() for row in rows]
            self._db.training_dataset.insert_many(docs)
        count = len(rows)
        logger.info("Persisted %d training dataset records", count)
        return count

    def count_all(self) -> int:
        return self._db.training_dataset.count_documents({})

    def get_preview(self, limit: int = 50) -> list[TrainingDatasetRecord]:
        docs = self._db.training_dataset.find().limit(limit)
        return [TrainingDatasetRecord.from_doc(d) for d in docs if d]

    def get_all(self) -> list[TrainingDatasetRecord]:
        docs = self._db.training_dataset.find()
        return [TrainingDatasetRecord.from_doc(d) for d in docs if d]

    def get_by_profile_id(self, profile_id: UUID) -> TrainingDatasetRecord | None:
        doc = self._db.training_dataset.find_one({"profile_id": str(profile_id)})
        return TrainingDatasetRecord.from_doc(doc) if doc else None

    @staticmethod
    def _to_model(row: Any) -> TrainingDatasetRecord:
        return TrainingDatasetRecord(
            record_id=row.record_id,
            profile_type=row.profile_type,
            profile_id=row.profile_id,
            age=row.age,
            income=row.income,
            credit_score=row.credit_score,
            financial_health_score=row.financial_health_score,
            repayment_behaviour_score=row.repayment_behaviour_score,
            digital_engagement_score=row.digital_engagement_score,
            financial_capacity_score=row.financial_capacity_score,
            lead_score=row.lead_score,
            lead_quality_score=row.lead_quality_score,
            lead_authenticity_score=row.lead_authenticity_score,
            income_confidence_score=row.income_confidence_score,
            relationship_score=row.relationship_score,
            savings_ratio=row.savings_ratio,
            emi_burden=row.emi_burden,
            cash_flow_score=row.cash_flow_score,
            digital_adoption_score=row.digital_adoption_score,
            customer_value_score=row.customer_value_score,
            occupation=row.occupation,
            employment_type=row.employment_type,
            city=row.city,
            target_repayment_capacity=row.target_repayment_capacity,
            created_at=row.created_at or datetime.utcnow(),
        )
