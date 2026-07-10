"""Relationship analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import adapt_relationship_profile
from app.dependencies import (
    get_aggregation_service,
    get_customer_query_repository,
    get_relationship_analytics_service,
)
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.schemas.relationship_analytics import (
    RelationshipAnalyticsResponse,
    RelationshipBuildAllResponse,
    RelationshipProfile,
)
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.relationship_analytics_service import RelationshipAnalyticsService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360/relationship", tags=["Relationship Analytics"])
frontend_router = APIRouter(prefix="/api/relationship", tags=["Relationship Analytics Frontend"])


@router.post(
    "/build-all",
    response_model=RelationshipBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute relationship analytics for all customers",
)
def build_all_relationship_analytics(
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    relationship_service: RelationshipAnalyticsService = Depends(get_relationship_analytics_service),
    customer_query: CustomerQueryRepository = Depends(get_customer_query_repository),
) -> RelationshipBuildAllResponse:
    customer_ids = customer_query.get_all_customer_ids()
    succeeded = 0
    failed = 0

    for customer_id in customer_ids:
        try:
            aggregate = aggregation_service.aggregate(customer_id)
            relationship_service.compute_and_persist(aggregate)
            succeeded += 1
        except Exception as exc:
            failed += 1
            logger.warning("Relationship analytics failed for customer_id=%s: %s", customer_id, exc)

    return RelationshipBuildAllResponse(
        message="Batch relationship analytics completed",
        customers_processed=len(customer_ids),
        customers_succeeded=succeeded,
        customers_failed=failed,
    )


@router.post(
    "/{customer_id}",
    response_model=RelationshipAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute relationship analytics for one customer",
)
def compute_relationship_analytics(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    relationship_service: RelationshipAnalyticsService = Depends(get_relationship_analytics_service),
) -> RelationshipAnalyticsResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    profile = relationship_service.compute_and_persist(aggregate)
    return RelationshipAnalyticsResponse(
        message="Relationship analytics computed and persisted successfully",
        relationship_profile=profile,
    )


@router.get(
    "/{customer_id}",
    response_model=RelationshipProfile,
    summary="Get stored relationship analytics",
)
def get_relationship_analytics(
    customer_id: UUID,
    relationship_service: RelationshipAnalyticsService = Depends(get_relationship_analytics_service),
) -> RelationshipProfile:
    return relationship_service.get_relationship_profile(customer_id)


@frontend_router.get(
    "/{customer_id}",
    summary="Get stored relationship analytics for frontend",
)
def get_relationship_analytics_frontend(
    customer_id: UUID,
    relationship_service: RelationshipAnalyticsService = Depends(get_relationship_analytics_service),
) -> dict:
    profile = relationship_service.get_relationship_profile(customer_id)
    return adapt_relationship_profile(profile.model_dump(mode="json"))

