"""External Lead Analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import adapt_external_analytics
from app.dependencies import get_external_analytics_service, get_db
from app.db.mongo import MongoDatabase
from app.external.external_analytics_service import ExternalAnalyticsService
from app.schemas.external_analytics import (
    ExternalLeadAnalyticsBuildAllResponse,
    ExternalLeadAnalyticsProfile,
    ExternalLeadAnalyticsResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/external/analytics", tags=["External Lead Analytics"])


@router.post(
    "/build-all",
    response_model=ExternalLeadAnalyticsBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute external lead analytics for all enriched leads",
)
def build_all_external_analytics(
    analytics_service: ExternalAnalyticsService = Depends(get_external_analytics_service),
) -> ExternalLeadAnalyticsBuildAllResponse:
    result = analytics_service.build_all()
    return ExternalLeadAnalyticsBuildAllResponse(
        message="External lead analytics batch completed",
        leads_processed=result["leads_processed"],
        leads_succeeded=result["leads_succeeded"],
        leads_failed=result["leads_failed"],
    )


@router.post(
    "/build/{lead_id}",
    response_model=ExternalLeadAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute external lead analytics for one lead",
    description=(
        "Runs behaviour, financial capacity, and lead quality analytics using only "
        "external_leads and external_customer_profile data. Requires prior enrichment."
    ),
)
def build_external_analytics(
    lead_id: UUID,
    analytics_service: ExternalAnalyticsService = Depends(get_external_analytics_service),
) -> ExternalLeadAnalyticsResponse:
    analytics = analytics_service.compute_and_persist(lead_id)
    return ExternalLeadAnalyticsResponse(
        message="External lead analytics computed and persisted successfully",
        analytics=analytics,
    )


@router.get(
    "/{lead_id}",
    summary="Get stored external lead analytics",
)
def get_external_analytics(
    lead_id: UUID,
    analytics_service: ExternalAnalyticsService = Depends(get_external_analytics_service),
    db: MongoDatabase = Depends(get_db),
) -> dict:
    analytics = analytics_service.get_analytics(lead_id)
    payload = analytics.model_dump(mode="json")
    conv = db.conversion_predictions.find_one({"lead_id": str(lead_id)}, {"_id": 0})
    if conv and conv.get("conversion_probability") is not None:
        payload["conversion_probability"] = conv.get("conversion_probability")
    lead = db.external_leads.find_one({"lead_id": str(lead_id)}, {"_id": 0, "campaign": 1})
    if lead:
        payload["recommended_campaign"] = lead.get("campaign")
    return adapt_external_analytics(payload)
