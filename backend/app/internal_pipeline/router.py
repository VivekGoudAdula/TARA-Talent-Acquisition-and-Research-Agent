"""API routes for the Internal Customer Intelligence Pipeline."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_internal_pipeline_service
from app.internal_pipeline.pipeline_service import InternalPipelineService
from app.schemas.internal_pipeline import PipelineBuildSummary, PipelineStatusResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/internal", tags=["Internal Intelligence Pipeline"])


@router.post(
    "/build-all",
    response_model=PipelineBuildSummary,
    status_code=status.HTTP_200_OK,
    summary="Build Internal Intelligence for all customers",
    description=(
        "Runs the complete Internal Customer Intelligence pipeline for every customer: "
        "Customer360 → Financial → Transaction → Behaviour → Relationship → "
        "Digital & Channel → Customer Health → Feature Store."
    ),
)
def build_all_customers(
    pipeline_service: InternalPipelineService = Depends(get_internal_pipeline_service),
) -> PipelineBuildSummary:
    logger.info("API: build-all internal intelligence pipeline requested")
    return pipeline_service.build_all()


@router.post(
    "/build/{customer_id}",
    response_model=PipelineBuildSummary,
    status_code=status.HTTP_200_OK,
    summary="Build Internal Intelligence for one customer",
    description="Runs the full internal pipeline for a single customer. Safe to retry on failure.",
)
def build_single_customer(
    customer_id: UUID,
    pipeline_service: InternalPipelineService = Depends(get_internal_pipeline_service),
) -> PipelineBuildSummary:
    logger.info("API: build internal pipeline for customer_id=%s", customer_id)
    return pipeline_service.build_one(customer_id)


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    summary="Internal Intelligence pipeline status",
    description=(
        "Returns coverage metrics: total customers, profiles built, feature store coverage, "
        "pending and failed customers, and success percentage."
    ),
)
def get_pipeline_status(
    pipeline_service: InternalPipelineService = Depends(get_internal_pipeline_service),
) -> PipelineStatusResponse:
    return pipeline_service.get_status()
