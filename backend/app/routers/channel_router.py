"""Digital & channel analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import (
    get_aggregation_service,
    get_customer_query_repository,
    get_digital_channel_analytics_service,
)
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.schemas.digital_channel_analytics import (
    DigitalChannelAnalyticsResponse,
    DigitalChannelBuildAllResponse,
    DigitalChannelProfile,
)
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.digital_channel_analytics_service import DigitalChannelAnalyticsService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360/channel", tags=["Digital & Channel Analytics"])


@router.post(
    "/build-all",
    response_model=DigitalChannelBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute digital & channel analytics for all customers",
)
def build_all_channel_analytics(
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    channel_service: DigitalChannelAnalyticsService = Depends(get_digital_channel_analytics_service),
    customer_query: CustomerQueryRepository = Depends(get_customer_query_repository),
) -> DigitalChannelBuildAllResponse:
    customer_ids = customer_query.get_all_customer_ids()
    succeeded = 0
    failed = 0

    for customer_id in customer_ids:
        try:
            aggregate = aggregation_service.aggregate(customer_id)
            channel_service.compute_and_persist(aggregate)
            succeeded += 1
        except Exception as exc:
            failed += 1
            logger.warning("Channel analytics failed for customer_id=%s: %s", customer_id, exc)

    return DigitalChannelBuildAllResponse(
        message="Batch digital & channel analytics completed",
        customers_processed=len(customer_ids),
        customers_succeeded=succeeded,
        customers_failed=failed,
    )


@router.post(
    "/{customer_id}",
    response_model=DigitalChannelAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute digital & channel analytics for one customer",
)
def compute_channel_analytics(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    channel_service: DigitalChannelAnalyticsService = Depends(get_digital_channel_analytics_service),
) -> DigitalChannelAnalyticsResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    profile = channel_service.compute_and_persist(aggregate)
    return DigitalChannelAnalyticsResponse(
        message="Digital & channel analytics computed and persisted successfully",
        channel_profile=profile,
    )


@router.get(
    "/{customer_id}",
    response_model=DigitalChannelProfile,
    summary="Get stored digital & channel analytics",
)
def get_channel_analytics(
    customer_id: UUID,
    channel_service: DigitalChannelAnalyticsService = Depends(get_digital_channel_analytics_service),
) -> DigitalChannelProfile:
    return channel_service.get_channel_profile(customer_id)
