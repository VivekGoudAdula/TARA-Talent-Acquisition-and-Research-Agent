"""Customer health & risk analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import (
    get_aggregation_service,
    get_customer_health_analytics_service,
    get_customer_query_repository,
)
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.schemas.customer_health_analytics import (
    CustomerHealthAnalyticsResponse,
    CustomerHealthBuildAllResponse,
    CustomerHealthProfile,
)
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.customer_health_analytics_service import CustomerHealthAnalyticsService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360/customer-health", tags=["Customer Health Analytics"])


@router.post(
    "/build-all",
    response_model=CustomerHealthBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute customer health analytics for all customers",
)
def build_all_customer_health(
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    health_service: CustomerHealthAnalyticsService = Depends(get_customer_health_analytics_service),
    customer_query: CustomerQueryRepository = Depends(get_customer_query_repository),
) -> CustomerHealthBuildAllResponse:
    customer_ids = customer_query.get_all_customer_ids()
    succeeded = 0
    failed = 0

    for customer_id in customer_ids:
        try:
            aggregate = aggregation_service.aggregate(customer_id)
            health_service.compute_and_persist(aggregate)
            succeeded += 1
        except Exception as exc:
            failed += 1
            logger.warning("Customer health analytics failed for customer_id=%s: %s", customer_id, exc)

    return CustomerHealthBuildAllResponse(
        message="Batch customer health analytics completed",
        customers_processed=len(customer_ids),
        customers_succeeded=succeeded,
        customers_failed=failed,
    )


@router.post(
    "/{customer_id}",
    response_model=CustomerHealthAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute customer health analytics for one customer",
)
def compute_customer_health(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    health_service: CustomerHealthAnalyticsService = Depends(get_customer_health_analytics_service),
) -> CustomerHealthAnalyticsResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    profile = health_service.compute_and_persist(aggregate)
    return CustomerHealthAnalyticsResponse(
        message="Customer health analytics computed and persisted successfully",
        health_profile=profile,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerHealthProfile,
    summary="Get stored customer health analytics",
)
def get_customer_health(
    customer_id: UUID,
    health_service: CustomerHealthAnalyticsService = Depends(get_customer_health_analytics_service),
) -> CustomerHealthProfile:
    return health_service.get_health_profile(customer_id)
