"""Behaviour Analytics Summary API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_behaviour_summary_service
from app.behaviour_summary.behaviour_summary_service import BehaviourSummaryService
from app.schemas.behaviour_summary import (
    BehaviourSummaryBuildAllResponse,
    BehaviourSummaryBuildResponse,
    BehaviourSummaryResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/behaviour", tags=["Behaviour Analytics Summary"])
frontend_router = APIRouter(prefix="/api/behaviour-summary", tags=["Behaviour Analytics Summary Frontend"])


@router.post(
    "/build-all",
    response_model=BehaviourSummaryBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Build behaviour summaries for all internal and external profiles",
)
def build_all_behaviour_summaries(
    service: BehaviourSummaryService = Depends(get_behaviour_summary_service),
) -> BehaviourSummaryBuildAllResponse:
    result = service.build_all()
    return BehaviourSummaryBuildAllResponse(
        message="Behaviour analytics summaries built successfully",
        profiles_processed=result["profiles_processed"],
        internal_succeeded=result["internal_succeeded"],
        external_succeeded=result["external_succeeded"],
        profiles_failed=result["profiles_failed"],
    )


@router.post(
    "/build/{profile_id}",
    response_model=BehaviourSummaryBuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Build behaviour summary for one profile",
    description=(
        "Aggregates existing analytics into standardized financial health, "
        "repayment behaviour, and digital engagement scores. "
        "Works for internal customer_360_profile or external_customer_profile."
    ),
)
def build_behaviour_summary(
    profile_id: UUID,
    service: BehaviourSummaryService = Depends(get_behaviour_summary_service),
) -> BehaviourSummaryBuildResponse:
    summary = service.build_summary(profile_id)
    logger.info(
        "Behaviour summary built profile_id=%s type=%s",
        profile_id,
        summary.profile_type,
    )
    return BehaviourSummaryBuildResponse(
        message="Behaviour analytics summary built successfully",
        summary=summary,
    )


@router.get(
    "/{profile_id}",
    response_model=BehaviourSummaryResponse,
    summary="Get standardized behaviour analytics summary",
)
def get_behaviour_summary(
    profile_id: UUID,
    service: BehaviourSummaryService = Depends(get_behaviour_summary_service),
) -> BehaviourSummaryResponse:
    return service.get_summary(profile_id)


@frontend_router.get(
    "/{profile_id}",
    response_model=BehaviourSummaryResponse,
    summary="Get standardized behaviour analytics summary for frontend",
)
def get_behaviour_summary_frontend(
    profile_id: UUID,
    service: BehaviourSummaryService = Depends(get_behaviour_summary_service),
) -> BehaviourSummaryResponse:
    return service.get_summary(profile_id)

