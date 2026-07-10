"""External Lead Intelligence validation API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import adapt_external_intelligence
from app.dependencies import get_external_intelligence_service, get_external_lead_repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.external.external_intelligence_service import ExternalIntelligenceService
from app.schemas.external_lead_intelligence import (
    ExternalLeadIntelligenceBuildAllResponse,
    ExternalLeadIntelligenceProfile,
    ExternalLeadIntelligenceResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/external/intelligence", tags=["External Lead Intelligence"])


@router.post(
    "/build-all",
    response_model=ExternalLeadIntelligenceBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Run intelligence validation for all enriched leads",
)
def build_all_external_intelligence(
    intelligence_service: ExternalIntelligenceService = Depends(get_external_intelligence_service),
) -> ExternalLeadIntelligenceBuildAllResponse:
    result = intelligence_service.build_all()
    return ExternalLeadIntelligenceBuildAllResponse(
        message="External lead intelligence validation completed",
        leads_processed=result["leads_processed"],
        leads_succeeded=result["leads_succeeded"],
        leads_failed=result["leads_failed"],
    )


@router.post(
    "/build/{lead_id}",
    response_model=ExternalLeadIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Run all four intelligence engines for one lead",
    description=(
        "Executes Lead Authenticity, Income Confidence, Fraud Screening, and "
        "KYC Readiness engines using only external_leads and external_customer_profile data."
    ),
)
def build_external_intelligence(
    lead_id: UUID,
    intelligence_service: ExternalIntelligenceService = Depends(get_external_intelligence_service),
) -> ExternalLeadIntelligenceResponse:
    intelligence = intelligence_service.compute_and_persist(lead_id)
    logger.info("Intelligence built for lead_id=%s", lead_id)
    return ExternalLeadIntelligenceResponse(
        message="External lead intelligence computed and persisted successfully",
        intelligence=intelligence,
    )


@router.get(
    "/{lead_id}",
    summary="Get complete external lead intelligence",
)
def get_external_intelligence(
    lead_id: UUID,
    intelligence_service: ExternalIntelligenceService = Depends(get_external_intelligence_service),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
) -> dict:
    intelligence = intelligence_service.get_intelligence(lead_id)
    lead = lead_repo.get_by_lead_id(lead_id)
    lead_doc = lead.__dict__ if lead else {}
    return adapt_external_intelligence(intelligence.model_dump(mode="json"), lead_doc)
