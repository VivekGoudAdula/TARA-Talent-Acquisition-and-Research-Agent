"""ML Dataset Builder API routes."""

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_dataset_service
from app.ml.dataset_builder.dataset_service import DatasetService
from app.schemas.ml_dataset import (
    MLDatasetBuildResponse,
    MLDatasetPreviewResponse,
    MLDatasetStatsResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ml/dataset", tags=["ML Dataset Builder"])


@router.post(
    "/build",
    response_model=MLDatasetBuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Build unified ML training dataset",
    description=(
        "Reads feature_store, lead_feature_store, customer_360_profile, and "
        "external_customer_profile; validates, deduplicates, assigns temporary "
        "target labels, persists to training_dataset, and exports CSV + Parquet."
    ),
)
def build_ml_dataset(
    service: DatasetService = Depends(get_dataset_service),
) -> MLDatasetBuildResponse:
    result = service.build_dataset()
    logger.info(
        "ML dataset built records=%d internal=%d external=%d",
        result.records_persisted,
        result.internal_records,
        result.external_records,
    )
    return result


@router.get(
    "",
    response_model=MLDatasetPreviewResponse,
    summary="Preview ML training dataset",
)
def preview_ml_dataset(
    limit: int = Query(default=50, ge=1, le=500),
    service: DatasetService = Depends(get_dataset_service),
) -> MLDatasetPreviewResponse:
    return service.preview_dataset(limit=limit)


@router.get(
    "/stats",
    response_model=MLDatasetStatsResponse,
    summary="ML training dataset statistics",
)
def ml_dataset_stats(
    service: DatasetService = Depends(get_dataset_service),
) -> MLDatasetStatsResponse:
    return service.dataset_stats()
