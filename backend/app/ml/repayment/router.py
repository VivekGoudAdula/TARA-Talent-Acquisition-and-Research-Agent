"""Repayment Capacity Prediction API routes."""

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import model_info_from_db_run
from app.dependencies import get_db, get_repayment_capacity_service
from app.db.mongo import MongoDatabase
from app.ml.repayment.service import RepaymentCapacityService
from app.schemas.repayment import (
    RepaymentModelInfoResponse,
    RepaymentPredictRequest,
    RepaymentPredictResponse,
    RepaymentTrainResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ml/repayment", tags=["Repayment Capacity ML"])


@router.post(
    "/train",
    response_model=RepaymentTrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Train repayment capacity models",
    description=(
        "Trains Random Forest, XGBoost, and LightGBM on the unified training dataset, "
        "selects the best model by cross-validated F1, and saves artifacts."
    ),
)
def train_repayment_model(
    service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
) -> RepaymentTrainResponse:
    result = service.train()
    logger.info("Repayment model training complete best=%s", result.best_model)
    return result


@router.post(
    "/predict",
    response_model=RepaymentPredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict repayment capacity",
    description=(
        "Predicts repayment capacity (Very High / High / Medium / Low) from "
        "engineered features or a profile_id lookup in the training dataset."
    ),
)
def predict_repayment_capacity(
    request: RepaymentPredictRequest,
    service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
) -> RepaymentPredictResponse:
    return service.predict(
        features=request.features,
        profile_id=request.profile_id,
        profile_type=request.profile_type,
    )


@router.get(
    "/model",
    response_model=RepaymentModelInfoResponse,
    summary="Get repayment model metadata",
    description="Returns best model info, evaluation metrics, and feature importance.",
)
def get_repayment_model(
    service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
) -> RepaymentModelInfoResponse:
    return service.get_model_info()


@router.get(
    "/model-info",
    summary="Get repayment model metadata for frontend UI",
)
def get_repayment_model_info(
    service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
    db: MongoDatabase = Depends(get_db),
) -> dict:
    try:
        info = service.get_model_info()
        metrics = info.metrics or {}
        test_metrics = metrics.get("test_metrics", {}) if isinstance(metrics, dict) else {}
        
        # Extract accuracy, f1 (or f1_macro), and roc_auc
        accuracy = test_metrics.get("accuracy")
        f1 = test_metrics.get("f1_macro") or test_metrics.get("f1")
        roc_auc = test_metrics.get("roc_auc")
        
        return {
            "trained": True,
            "algorithm": info.best_model,
            "version": "1.0.0",
            "last_trained": info.trained_at,
            "train_samples": metrics.get("train_size", info.records_used) if isinstance(metrics, dict) else info.records_used,
            "test_samples": metrics.get("test_size", 0) if isinstance(metrics, dict) else 0,
            "metrics": {
                "accuracy": accuracy,
                "f1": f1,
                "roc_auc": roc_auc,
            },
            "feature_importance": info.feature_importance or {},
        }
    except Exception:
        runs = list(
            db.ml_model_runs.find(
                {"model_name": {"$in": ["repayment_capacity", "repayment"]}},
                {"_id": 0},
            )
        )
        if not runs:
            runs = list(
                db.ml_model_runs.find(
                    {"model_name": {"$regex": "repay", "$options": "i"}},
                    {"_id": 0},
                )
            )
        if runs:
            runs.sort(key=lambda d: d.get("created_at") or "", reverse=True)
            return model_info_from_db_run(runs[0])
        return {
            "trained": False,
            "algorithm": None,
            "version": "1.0.0",
            "last_trained": None,
            "train_samples": 0,
            "test_samples": 0,
            "metrics": {},
            "feature_importance": {},
        }
