"""Orchestration for Repayment Capacity Prediction training and inference."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.ml.dataset_builder.dataset_service import DatasetService
from app.ml.dataset_builder.dataset_validator import DatasetValidator
from app.ml.repayment.predictor import RepaymentPredictor
from app.ml.repayment.registry import RepaymentModelRegistry
from app.ml.repayment.training import FEATURE_COLUMNS, RepaymentTrainer
from app.repositories.training_dataset_repository import TrainingDatasetRepository
from app.repositories.ml_scoring_repository import MLScoringRepository
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.schemas.repayment import (
    RepaymentModelInfoResponse,
    RepaymentPredictResponse,
    RepaymentTrainResponse,
)
from app.utils.exceptions import MLDatasetNotFoundError, RepaymentModelNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RepaymentCapacityService:
    """Enterprise service for repayment capacity model training and prediction."""

    def __init__(
        self,
        training_dataset_repository: TrainingDatasetRepository,
        registry: RepaymentModelRegistry | None = None,
        trainer: RepaymentTrainer | None = None,
        predictor: RepaymentPredictor | None = None,
        validator: DatasetValidator | None = None,
        scoring_repository: MLScoringRepository | None = None,
        customer360_repository: Customer360Repository | None = None,
        external_profile_repository: ExternalProfileRepository | None = None,
    ) -> None:
        self._dataset_repo = training_dataset_repository
        self._registry = registry or RepaymentModelRegistry()
        self._trainer = trainer or RepaymentTrainer()
        self._predictor = predictor or RepaymentPredictor(self._registry)
        self._validator = validator or DatasetValidator()
        self._scoring_repo = scoring_repository
        self._c360_repo = customer360_repository
        self._external_repo = external_profile_repository

    def train(self) -> RepaymentTrainResponse:
        records = self._dataset_repo.get_all()
        if not records:
            raise MLDatasetNotFoundError()

        rows = [DatasetService._record_to_row(r) for r in records]
        df = self._validator.rows_to_dataframe(rows)

        result = self._trainer.train(df)
        trained_at = datetime.now(timezone.utc).isoformat()

        metadata = {
            "best_model": result.best_model_name,
            "trained_at": trained_at,
            "feature_columns": result.feature_columns,
            "records_used": result.records_used,
            "train_size": result.train_size,
            "test_size": result.test_size,
        }

        model_path = self._registry.save_model(
            result.pipeline, metadata, label_encoder=result.label_encoder
        )
        metrics_payload = {
            "best_model": result.best_model_name,
            "trained_at": trained_at,
            "cv_scores": result.cv_scores,
            "test_metrics": result.test_metrics,
            "records_used": result.records_used,
            "train_size": result.train_size,
            "test_size": result.test_size,
        }
        metrics_path = self._registry.save_metrics(metrics_payload)
        importance_path = self._registry.save_feature_importance(result.feature_importance)

        self._predictor._artifact = None

        if self._scoring_repo:
            self._scoring_repo.save_model_run(
                model_name="repayment_capacity",
                best_model=result.best_model_name,
                records_used=result.records_used,
                train_size=result.train_size,
                test_size=result.test_size,
                cv_scores=result.cv_scores,
                test_metrics=result.test_metrics,
                model_path=model_path,
                metrics_path=metrics_path,
                feature_importance_path=importance_path,
            )

        logger.info(
            "Repayment model trained best=%s records=%d",
            result.best_model_name,
            result.records_used,
        )

        return RepaymentTrainResponse(
            message="Repayment capacity model trained successfully",
            best_model=result.best_model_name,
            records_used=result.records_used,
            train_size=result.train_size,
            test_size=result.test_size,
            cv_scores=result.cv_scores,
            test_metrics=result.test_metrics,
            model_path=model_path,
            metrics_path=metrics_path,
            feature_importance_path=importance_path,
        )

    def predict(
        self,
        features: dict[str, Any] | None = None,
        profile_id: UUID | None = None,
        profile_type: str | None = None,
    ) -> RepaymentPredictResponse:
        if not self._registry.model_exists():
            raise RepaymentModelNotFoundError()

        if features is None:
            if profile_id is None:
                raise ValueError("Either features or profile_id must be provided")
            features = self._resolve_features_from_profile(profile_id, profile_type)

        prediction = self._predictor.predict(features)
        response = RepaymentPredictResponse(**prediction)

        if self._scoring_repo and profile_id is not None:
            self._persist_prediction(profile_id, profile_type, response)

        return response

    def _persist_prediction(
        self,
        profile_id: UUID,
        profile_type: str | None,
        response: RepaymentPredictResponse,
    ) -> None:
        resolved_type = profile_type
        entity_id: UUID | None = None

        if self._c360_repo:
            internal = self._c360_repo.get_profile_by_profile_id(profile_id)
            if internal is not None:
                resolved_type = resolved_type or "Internal"
                entity_id = internal.customer_id

        if entity_id is None and self._external_repo:
            external = self._external_repo.get_profile_by_profile_id(profile_id)
            if external is not None:
                resolved_type = resolved_type or "External"
                entity_id = external.lead_id

        if entity_id is None or resolved_type is None:
            return

        self._scoring_repo.upsert_repayment_prediction(
            profile_id=profile_id,
            profile_type=resolved_type,
            entity_id=entity_id,
            repayment_capacity=response.repayment_capacity,
            confidence=response.confidence,
            probabilities=response.probabilities,
            model_used=response.model_used,
        )

    def get_model_info(self) -> RepaymentModelInfoResponse:
        if not self._registry.model_exists():
            raise RepaymentModelNotFoundError()

        artifact = self._registry.load_model()
        metadata = artifact.get("metadata", {})
        metrics = self._registry.load_metrics()
        importance = self._registry.load_feature_importance()

        return RepaymentModelInfoResponse(
            model_exists=True,
            best_model=metadata.get("best_model"),
            trained_at=metadata.get("trained_at"),
            feature_columns=metadata.get("feature_columns", FEATURE_COLUMNS),
            records_used=metadata.get("records_used"),
            model_path=str(self._registry.model_path),
            metrics_path=str(self._registry.metrics_path),
            feature_importance_path=str(self._registry.feature_importance_path),
            metrics=metrics,
            feature_importance=importance,
        )

    def _resolve_features_from_profile(
        self,
        profile_id: UUID,
        profile_type: str | None,
    ) -> dict[str, Any]:
        record = self._dataset_repo.get_by_profile_id(profile_id)
        if record is not None:
            return self._record_to_features(record)
        raise MLDatasetNotFoundError()

    @staticmethod
    def _record_to_features(record: Any) -> dict[str, Any]:
        def _get(name):
            return getattr(record, name, None)

        def _float(name):
            val = _get(name)
            return float(val) if val is not None else None

        return {
            "profile_type": record.profile_type,
            "age": _get("age"),
            "income": _float("income"),
            "credit_score": _get("credit_score"),
            "financial_health_score": _float("financial_health_score"),
            "repayment_behaviour_score": _float("repayment_behaviour_score"),
            "digital_engagement_score": _float("digital_engagement_score"),
            "financial_capacity_score": _float("financial_capacity_score"),
            "lead_score": _float("lead_score"),
            "lead_quality_score": _float("lead_quality_score"),
            "lead_authenticity_score": _float("lead_authenticity_score"),
            "income_confidence_score": _float("income_confidence_score"),
            "relationship_score": _float("relationship_score"),
            "savings_ratio": _float("savings_ratio"),
            "emi_burden": _float("emi_burden"),
            "cash_flow_score": _float("cash_flow_score"),
            "digital_adoption_score": _float("digital_adoption_score"),
            "customer_value_score": _float("customer_value_score"),
            "occupation": _get("occupation"),
            "employment_type": _get("employment_type"),
            "city": _get("city"),
        }
