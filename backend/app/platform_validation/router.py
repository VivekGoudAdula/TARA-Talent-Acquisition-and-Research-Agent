"""API routes for enterprise platform validation and health checks."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_platform_validation_service
from app.platform_validation.validation_service import PlatformValidationService
from app.schemas.platform_validation import SystemHealthResponse, ValidationReportResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system", tags=["System Health & Validation"])


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Platform health dashboard",
    description=(
        "Returns aggregated PASS/FAIL status for database, internal/external intelligence, "
        "ML models, APIs, data integrity, and end-to-end workflows. "
        "Runs the validation suite on first request."
    ),
)
def get_system_health(
    validation_service: PlatformValidationService = Depends(get_platform_validation_service),
) -> SystemHealthResponse:
    return validation_service.get_health_summary(run_if_missing=True)


@router.post(
    "/validate",
    response_model=ValidationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Run full platform validation audit",
    description=(
        "Executes the complete enterprise validation suite and writes "
        "validation_report.json, validation_report.md, and validation_report.html "
        "to the project root."
    ),
)
def run_platform_validation(
    validation_service: PlatformValidationService = Depends(get_platform_validation_service),
) -> ValidationReportResponse:
    logger.info("API: full platform validation audit requested")
    return validation_service.run_full_validation(write_reports=True)
