"""Lead Conversion Prediction API routes."""

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import model_info_from_db_run, regression_metrics_for_ui
from app.dependencies import get_conversion_service, get_db
from app.db.mongo import MongoDatabase
from app.ml.conversion.service import ConversionService
from app.schemas.conversion import (
    ConversionModelInfoResponse,
    ConversionPredictRequest,
    ConversionPredictResponse,
    ConversionTrainResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ml/conversion", tags=["Lead Conversion ML"])


@router.post(
    "/train",
    response_model=ConversionTrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Train lead conversion models",
    description=(
        "Trains Random Forest, XGBoost, and LightGBM regressors on external lead data, "
        "selects the best model by cross-validated MAE, and saves artifacts."
    ),
)
def train_conversion_model(
    service: ConversionService = Depends(get_conversion_service),
) -> ConversionTrainResponse:
    result = service.train()
    logger.info("Conversion model training complete best=%s", result.best_model)
    return result


@router.post(
    "/predict",
    response_model=ConversionPredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict lead conversion probability",
    description=(
        "Predicts conversion probability (0–100%) for a qualified lead after Voice AI outreach. "
        "Returns lead priority and marketing priority."
    ),
)
def predict_conversion(
    request: ConversionPredictRequest,
    service: ConversionService = Depends(get_conversion_service),
) -> ConversionPredictResponse:
    return service.predict(lead_id=request.lead_id, features=request.features)


@router.get(
    "/model",
    response_model=ConversionModelInfoResponse,
    summary="Get conversion model metadata",
)
def get_conversion_model(
    service: ConversionService = Depends(get_conversion_service),
) -> ConversionModelInfoResponse:
    return service.get_model_info()


@router.get(
    "/model-info",
    summary="Get conversion model metadata for frontend UI",
)
def get_conversion_model_info(
    service: ConversionService = Depends(get_conversion_service),
    db: MongoDatabase = Depends(get_db),
) -> dict:
    try:
        info = service.get_model_info()
        metrics = info.metrics or {}
        test_metrics = metrics.get("test_metrics", {}) if isinstance(metrics, dict) else {}

        return {
            "trained": True,
            "algorithm": info.best_model,
            "version": "1.0.0",
            "last_trained": info.trained_at,
            "train_samples": metrics.get("train_size", info.records_used) if isinstance(metrics, dict) else info.records_used,
            "test_samples": metrics.get("test_size", 0) if isinstance(metrics, dict) else 0,
            "metrics": regression_metrics_for_ui(test_metrics),
            "feature_importance": info.feature_importance or {},
        }
    except Exception:
        runs = list(
            db.ml_model_runs.find(
                {"model_name": {"$in": ["lead_conversion", "conversion"]}},
                {"_id": 0},
            )
        )
        if not runs:
            runs = list(
                db.ml_model_runs.find(
                    {"model_name": {"$regex": "conversion", "$options": "i"}},
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
