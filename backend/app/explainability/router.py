"""Explainable AI API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_explainability_service
from app.explainability.service import ExplainabilityService
from app.schemas.explainability import (
    ExplainabilityGenerateRequest,
    ExplainabilityReportResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/explain", tags=["Explainable AI"])


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate ML explanation report",
    description=(
        "Collects outputs from Repayment, Product Recommendation, and Lead Conversion models, "
        "generates deterministic reason codes, and produces a human-readable explanation via Azure OpenAI. "
        "Does not alter any ML predictions."
    ),
)
def generate_explanation(
    request: ExplainabilityGenerateRequest,
    service: ExplainabilityService = Depends(get_explainability_service),
) -> dict:
    result = service.generate(request)
    logger.info("Explanation generated report_id=%s", result["report_id"])
    return result


@router.post(
    "/build-all",
    status_code=status.HTTP_200_OK,
    summary="Generate explanation reports for all profiles",
    description=(
        "Runs Explainable AI for every internal customer and external lead profile "
        "using Azure OpenAI GPT-4o and persists reports to explainability_reports."
    ),
)
def build_all_explanations(
    limit_internal: int = 50,
    limit_external: int = 0,
    service: ExplainabilityService = Depends(get_explainability_service),
) -> dict:
    result = service.build_all(
        limit_internal=limit_internal,
        limit_external=limit_external,
    )
    logger.info("Explainability build-all complete: %s", result)
    return result


@router.get(
    "/report/{customer_id}",
    include_in_schema=False,
)
@router.get(
    "/{customer_id}",
    summary="Get latest explanation for a customer",
    description=(
        "Returns the most recent explainability report. "
        "customer_id is the internal banking customer_id or external lead_id."
    ),
)
def get_latest_explanation(
    customer_id: UUID,
    service: ExplainabilityService = Depends(get_explainability_service),
) -> dict:
    return service.get_latest(customer_id)
