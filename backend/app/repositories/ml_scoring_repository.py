"""Persistence for ML scoring outputs (repayment, product-fit, conversion, model runs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLScoringRepository:
    """Data access for repayment predictions, product recommendations, conversion, model runs."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def upsert_repayment_prediction(
        self,
        *,
        profile_id: UUID,
        profile_type: str,
        entity_id: UUID,
        repayment_capacity: str,
        confidence: float,
        probabilities: dict[str, float],
        model_used: str,
    ) -> None:
        now = datetime.utcnow()
        self._db.repayment_predictions.update_one(
            {"profile_id": str(profile_id)},
            {
                "$set": {
                    "profile_type": profile_type,
                    "entity_id": str(entity_id),
                    "repayment_capacity": repayment_capacity,
                    "confidence": confidence,
                    "probabilities": probabilities,
                    "model_used": model_used,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "prediction_id": str(uuid4()),
                    "created_at": now,
                }
            },
            upsert=True
        )
        self._apply_profile_repayment(profile_id, profile_type, repayment_capacity, confidence)
        logger.debug("Persisted repayment prediction profile_id=%s", profile_id)

    def upsert_product_recommendation(
        self,
        *,
        profile_id: UUID,
        profile_type: str,
        entity_id: UUID,
        repayment_capacity: str,
        repayment_confidence: float,
        top_recommendation: str | None,
        recommendations: list[dict[str, Any]],
    ) -> None:
        now = datetime.utcnow()
        self._db.product_recommendations.update_one(
            {"profile_id": str(profile_id)},
            {
                "$set": {
                    "profile_type": profile_type,
                    "entity_id": str(entity_id),
                    "repayment_capacity": repayment_capacity,
                    "repayment_confidence": repayment_confidence,
                    "top_recommendation": top_recommendation,
                    "recommendations": recommendations,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "recommendation_id": str(uuid4()),
                    "created_at": now,
                }
            },
            upsert=True
        )
        self._apply_profile_product(profile_id, profile_type, top_recommendation, recommendations)
        logger.debug("Persisted product recommendation profile_id=%s", profile_id)

    def upsert_conversion_prediction(
        self,
        *,
        lead_id: UUID,
        profile_id: UUID | None,
        conversion_probability: float,
        lead_priority: str,
        marketing_priority: str,
        model_used: str,
    ) -> None:
        now = datetime.utcnow()
        self._db.conversion_predictions.update_one(
            {"lead_id": str(lead_id)},
            {
                "$set": {
                    "profile_id": str(profile_id) if profile_id else None,
                    "conversion_probability": conversion_probability,
                    "lead_priority": lead_priority,
                    "marketing_priority": marketing_priority,
                    "model_used": model_used,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "prediction_id": str(uuid4()),
                    "created_at": now,
                }
            },
            upsert=True
        )
        if profile_id:
            self._db.external_customer_profile.update_one(
                {"profile_id": str(profile_id)},
                {
                    "$set": {
                        "conversion_probability": conversion_probability,
                        "lead_priority": lead_priority,
                        "marketing_priority": marketing_priority,
                        "last_updated": now,
                    }
                },
            )
        logger.debug("Persisted conversion prediction lead_id=%s", lead_id)

    def save_model_run(
        self,
        *,
        model_name: str,
        best_model: str,
        records_used: int,
        train_size: int,
        test_size: int,
        cv_scores: dict[str, float],
        test_metrics: dict[str, Any],
        model_path: str,
        metrics_path: str,
        feature_importance_path: str,
        label_source: str | None = None,
        outcome_labels_used: int | None = None,
    ) -> str:
        run_id = str(uuid4())
        import json
        from pathlib import Path

        feature_importance: dict[str, Any] = {}
        if feature_importance_path:
            path = Path(feature_importance_path)
            if path.is_file():
                try:
                    feature_importance = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    feature_importance = {}

        doc = {
            "run_id": run_id,
            "model_name": model_name,
            "best_model": best_model,
            "records_used": records_used,
            "train_size": train_size,
            "test_size": test_size,
            "cv_scores": cv_scores,
            "test_metrics": test_metrics,
            "model_path": model_path,
            "metrics_path": metrics_path,
            "feature_importance_path": feature_importance_path,
            "feature_importance": feature_importance,
            "label_source": label_source,
            "outcome_labels_used": outcome_labels_used,
            "created_at": datetime.utcnow(),
        }
        self._db.ml_model_runs.insert_one(doc)
        logger.info("Saved ML model run model_name=%s run_id=%s", model_name, run_id)
        return run_id

    def list_model_runs(
        self,
        *,
        model_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if model_name:
            query["model_name"] = model_name
        docs = list(self._db.ml_model_runs.find(query, {"_id": 0}))
        docs.sort(key=lambda d: d.get("created_at") or datetime.min, reverse=True)
        return docs[:limit]

    def get_repayment_by_profile_id(self, profile_id: UUID) -> dict[str, Any] | None:
        return self._db.repayment_predictions.find_one({"profile_id": str(profile_id)})

    def get_product_by_profile_id(self, profile_id: UUID) -> dict[str, Any] | None:
        return self._db.product_recommendations.find_one({"profile_id": str(profile_id)})

    def get_conversion_by_lead_id(self, lead_id: UUID) -> dict[str, Any] | None:
        return self._db.conversion_predictions.find_one({"lead_id": str(lead_id)})

    def _apply_profile_repayment(
        self,
        profile_id: UUID,
        profile_type: str,
        repayment_capacity: str,
        confidence: float,
    ) -> None:
        now = datetime.utcnow()
        fields = {
            "repayment_capacity_predicted": repayment_capacity,
            "repayment_confidence": confidence,
            "last_updated": now,
        }
        if profile_type == "Internal":
            self._db.customer_360_profile.update_one(
                {"profile_id": str(profile_id)}, {"$set": fields}
            )
        else:
            self._db.external_customer_profile.update_one(
                {"profile_id": str(profile_id)}, {"$set": fields}
            )

    def _apply_profile_product(
        self,
        profile_id: UUID,
        profile_type: str,
        top_recommendation: str | None,
        recommendations: list[dict[str, Any]],
    ) -> None:
        now = datetime.utcnow()
        top_score = None
        if recommendations:
            top_score = recommendations[0].get("confidence_score")
        fields = {
            "top_recommended_product": top_recommendation,
            "top_product_confidence": top_score,
            "last_updated": now,
        }
        if profile_type == "Internal":
            self._db.customer_360_profile.update_one(
                {"profile_id": str(profile_id)}, {"$set": fields}
            )
        else:
            self._db.external_customer_profile.update_one(
                {"profile_id": str(profile_id)}, {"$set": fields}
            )
