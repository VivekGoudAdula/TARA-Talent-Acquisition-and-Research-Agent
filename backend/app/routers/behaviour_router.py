"""Behaviour analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import adapt_behaviour_profile
from app.dependencies import (
    get_aggregation_service,
    get_behaviour_analytics_service,
    get_customer_query_repository,
    get_db,
)
from app.db.mongo import MongoDatabase
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.schemas.behaviour_analytics import (
    BehaviourAnalyticsResponse,
    BehaviourBuildAllResponse,
    BehaviourProfile,
)
from app.services.customer360.behaviour_analytics_service import BehaviourAnalyticsService
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360/behaviour", tags=["Behaviour Analytics"])
frontend_router = APIRouter(prefix="/api/behaviour", tags=["Behaviour Analytics Frontend"])


@router.post(
    "/build-all",
    response_model=BehaviourBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute behaviour analytics for all customers",
)
def build_all_behaviour_analytics(
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    behaviour_service: BehaviourAnalyticsService = Depends(get_behaviour_analytics_service),
    customer_query: CustomerQueryRepository = Depends(get_customer_query_repository),
) -> BehaviourBuildAllResponse:
    customer_ids = customer_query.get_all_customer_ids()
    succeeded = 0
    failed = 0

    for customer_id in customer_ids:
        try:
            aggregate = aggregation_service.aggregate(customer_id)
            behaviour_service.compute_and_persist(aggregate)
            succeeded += 1
        except Exception as exc:
            failed += 1
            logger.warning("Behaviour analytics failed for customer_id=%s: %s", customer_id, exc)

    return BehaviourBuildAllResponse(
        message="Batch behaviour analytics completed",
        customers_processed=len(customer_ids),
        customers_succeeded=succeeded,
        customers_failed=failed,
    )


@router.post(
    "/{customer_id}",
    response_model=BehaviourAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute behaviour analytics for one customer",
)
def compute_behaviour_analytics(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    behaviour_service: BehaviourAnalyticsService = Depends(get_behaviour_analytics_service),
) -> BehaviourAnalyticsResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    profile = behaviour_service.compute_and_persist(aggregate)
    return BehaviourAnalyticsResponse(
        message="Behaviour analytics computed and persisted successfully",
        behaviour_profile=profile,
    )


@router.get(
    "/{customer_id}",
    response_model=BehaviourProfile,
    summary="Get stored behaviour profile",
)
def get_behaviour_analytics(
    customer_id: UUID,
    behaviour_service: BehaviourAnalyticsService = Depends(get_behaviour_analytics_service),
) -> BehaviourProfile:
    return behaviour_service.get_behaviour_profile(customer_id)


@frontend_router.get(
    "/{customer_id}",
    summary="Get stored behaviour profile for frontend",
)
def get_behaviour_analytics_frontend(
    customer_id: UUID,
    behaviour_service: BehaviourAnalyticsService = Depends(get_behaviour_analytics_service),
    db: MongoDatabase = Depends(get_db),
) -> dict:
    profile = behaviour_service.get_behaviour_profile(customer_id)
    profile_doc = db.customer_360_profile.find_one({"customer_id": str(customer_id)}, {"_id": 0}) or {}
    return adapt_behaviour_profile(profile.model_dump(mode="json"), profile_doc)

