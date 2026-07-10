"""Orchestration for Lead Conversion Prediction."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.ml.conversion.predictor import ConversionPredictor
from app.ml.conversion.training import (
    FEATURE_COLUMNS,
    TARGET_COL,
    ConversionModelRegistry,
    ConversionTrainer,
    categorize_lead_source,
    label_conversion_probability,
)
from app.models.external_customer_profile import ExternalCustomerProfile
from app.models.external_lead import ExternalLead
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.repositories.ml_scoring_repository import MLScoringRepository
from app.schemas.conversion import (
    ConversionModelInfoResponse,
    ConversionPredictRequest,
    ConversionPredictResponse,
    ConversionTrainResponse,
)
from app.utils.exceptions import ConversionDataNotFoundError, ConversionModelNotFoundError, LeadNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def lead_priority(probability: float) -> str:
    if probability >= 75.0:
        return "High"
    if probability >= 50.0:
        return "Medium"
    return "Low"


def marketing_priority(probability: float, consent: bool) -> str:
    adjusted = probability
    if not consent:
        adjusted *= 0.7
    if adjusted >= 70.0:
        return "High"
    if adjusted >= 45.0:
        return "Medium"
    return "Low"


class ConversionService:
    """
    Enterprise Lead Conversion Prediction service (Model 3).

    Predicts qualified-lead conversion probability after Voice AI outreach.
    Does not recommend products or predict repayment capacity.
    """

    def __init__(
        self,
        lead_repository: ExternalLeadRepository,
        external_profile_repository: ExternalProfileRepository,
        lead_feature_store_repository: LeadFeatureStoreRepository,
        registry: ConversionModelRegistry | None = None,
        trainer: ConversionTrainer | None = None,
        predictor: ConversionPredictor | None = None,
        scoring_repository: MLScoringRepository | None = None,
    ) -> None:
        self._lead_repo = lead_repository
        self._profile_repo = external_profile_repository
        self._feature_repo = lead_feature_store_repository
        self._registry = registry or ConversionModelRegistry()
        self._trainer = trainer or ConversionTrainer()
        self._predictor = predictor or ConversionPredictor(self._registry)
        self._scoring_repo = scoring_repository

    def train(
        self,
        *,
        label_source: str = "synthetic",
        outcome_labels: dict[str, float] | None = None,
        limit: int | None = 500,
    ) -> ConversionTrainResponse:
        import pandas as pd

        df = self._build_training_dataframe(
            label_source=label_source,
            outcome_labels=outcome_labels,
            limit=limit,
        )
        if df.empty:
            raise ConversionDataNotFoundError()

        outcome_count = 0
        if outcome_labels and label_source != "synthetic":
            lead_ids = {str(lead.lead_id) for lead in self._lead_repo.get_all(limit=10000)}
            outcome_count = sum(1 for lid in outcome_labels if lid in lead_ids)

        result = self._trainer.train(df)
        trained_at = datetime.now(timezone.utc).isoformat()

        metadata = {
            "best_model": result.best_model_name,
            "trained_at": trained_at,
            "feature_columns": result.feature_columns,
            "records_used": result.records_used,
            "train_size": result.train_size,
            "test_size": result.test_size,
            "label_source": label_source,
            "outcome_labels_used": outcome_count,
        }

        model_path = self._registry.save_model(result.pipeline, metadata)
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
                model_name="lead_conversion",
                best_model=result.best_model_name,
                records_used=result.records_used,
                train_size=result.train_size,
                test_size=result.test_size,
                cv_scores=result.cv_scores,
                test_metrics=result.test_metrics,
                model_path=model_path,
                metrics_path=metrics_path,
                feature_importance_path=importance_path,
                label_source=label_source,
                outcome_labels_used=outcome_count,
            )

        logger.info(
            "Conversion model trained best=%s records=%d",
            result.best_model_name,
            result.records_used,
        )

        return ConversionTrainResponse(
            message="Lead conversion model trained successfully",
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
        lead_id: UUID | None = None,
        features: dict[str, Any] | None = None,
    ) -> ConversionPredictResponse:
        if not self._registry.model_exists():
            raise ConversionModelNotFoundError()

        if features is None:
            if lead_id is None:
                raise ValueError("Either lead_id or features must be provided")
            lead = self._lead_repo.get_by_lead_id(lead_id)
            if lead is None:
                raise LeadNotFoundError(lead_id)
            profile = self._profile_repo.get_by_lead_id(lead_id)
            feature_map = self._feature_repo.features_to_dict(
                self._feature_repo.get_all_features_by_lead(lead_id)
            )
            features = self._build_features(lead, profile, feature_map)

        prediction = self._predictor.predict(features)
        consent = bool(features.get("consent", 0))
        probability = prediction["conversion_probability"]

        response = ConversionPredictResponse(
            lead_id=lead_id,
            conversion_probability=probability,
            lead_priority=lead_priority(probability),
            marketing_priority=marketing_priority(probability, consent),
            model_used=prediction["model_used"],
        )

        if self._scoring_repo and lead_id is not None:
            profile = self._profile_repo.get_by_lead_id(lead_id)
            self._scoring_repo.upsert_conversion_prediction(
                lead_id=lead_id,
                profile_id=profile.profile_id if profile else None,
                conversion_probability=response.conversion_probability,
                lead_priority=response.lead_priority,
                marketing_priority=response.marketing_priority,
                model_used=response.model_used,
            )

        return response

    def get_model_info(self) -> ConversionModelInfoResponse:
        if not self._registry.model_exists():
            raise ConversionModelNotFoundError()

        artifact = self._registry.load_model()
        metadata = artifact.get("metadata", {})

        return ConversionModelInfoResponse(
            model_exists=True,
            best_model=metadata.get("best_model"),
            trained_at=metadata.get("trained_at"),
            feature_columns=metadata.get("feature_columns", FEATURE_COLUMNS),
            records_used=metadata.get("records_used"),
            model_path=str(self._registry.model_path),
            metrics_path=str(self._registry.metrics_path),
            feature_importance_path=str(self._registry.feature_importance_path),
            metrics=self._registry.load_metrics(),
            feature_importance=self._registry.load_feature_importance(),
        )

    def _build_training_dataframe(
        self,
        *,
        label_source: str = "synthetic",
        outcome_labels: dict[str, float] | None = None,
        limit: int | None = 500,
    ):
        import pandas as pd

        leads = self._lead_repo.get_all(limit=limit or 10000)
        if not leads:
            return pd.DataFrame()

        records: list[dict[str, Any]] = []
        for lead in leads:
            profile = self._profile_repo.get_by_lead_id(lead.lead_id)
            feature_map = self._feature_repo.features_to_dict(
                self._feature_repo.get_all_features_by_lead(lead.lead_id)
            )
            row = self._build_features(lead, profile, feature_map)
            lead_key = str(lead.lead_id)
            outcome_label = (outcome_labels or {}).get(lead_key)

            if label_source == "outcomes":
                if outcome_label is None:
                    continue
                row[TARGET_COL] = outcome_label
            elif label_source == "blended" and outcome_label is not None:
                synthetic = label_conversion_probability(row)
                row[TARGET_COL] = round(outcome_label * 0.7 + synthetic * 0.3, 2)
            else:
                row[TARGET_COL] = label_conversion_probability(row)

            records.append(row)

        return pd.DataFrame(records)

    def _build_features(
        self,
        lead: ExternalLead,
        profile: ExternalCustomerProfile | None,
        feature_map: dict[str, Decimal | str],
    ) -> dict[str, Any]:
        def _p(name: str):
            return getattr(profile, name, None) if profile else None

        lead_quality = self._coalesce_decimal(
            _p("lead_quality_score"),
            feature_map.get("lead_quality_score"),
        )
        behaviour = self._coalesce_decimal(
            _p("campaign_engagement_score"),
            feature_map.get("campaign_engagement_score"),
        )
        digital = self._coalesce_decimal(
            _p("digital_engagement_score"),
            feature_map.get("digital_readiness_score"),
        )
        communication = self._coalesce_decimal(_p("communication_readiness_score"), None)
        previous_response = self._feature_decimal(feature_map, "marketing_responsiveness_score")
        lead_score = _p("lead_score")
        if previous_response is None and lead_score is not None:
            previous_response = float(lead_score)

        return {
            "lead_source": categorize_lead_source(lead.referral_source),
            "campaign": lead.campaign,
            "referral_source": lead.referral_source,
            "occupation": lead.occupation,
            "employer": lead.employer,
            "estimated_income": float(lead.estimated_income) if lead.estimated_income else None,
            "credit_score": lead.credit_score,
            "lead_quality_score": lead_quality,
            "behaviour_score": behaviour,
            "digital_engagement_score": digital,
            "consent": 1 if lead.consent else 0,
            "previous_campaign_response": previous_response,
            "communication_readiness": communication,
        }

    @staticmethod
    def _coalesce_decimal(primary, fallback) -> float | None:
        if primary is not None:
            return float(primary)
        if fallback is not None:
            try:
                return float(fallback)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _feature_decimal(features: dict, name: str) -> float | None:
        value = features.get(name)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

