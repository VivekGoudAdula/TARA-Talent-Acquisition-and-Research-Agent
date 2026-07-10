"""Customer360 API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import adapt_customer360_view
from app.dependencies import (
    get_aggregation_service,
    get_customer360_repository,
    get_customer360_service,
    get_db,
)
from app.db.mongo import MongoDatabase
from app.repositories.customer360_repository import Customer360Repository
from app.schemas.customer360 import Customer360BuildResponse, Customer360ProfileResponse
from app.services.customer360.customer360_service import Customer360Service
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360", tags=["Customer360"])


@router.post(
    "/build/{customer_id}",
    response_model=Customer360BuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Build Customer360 profile",
    description=(
        "Aggregates data from core banking tables (customers, accounts, transactions, "
        "customer_products, consent) and creates or refreshes a Customer360 profile."
    ),
)
def build_customer360_profile(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    customer360_service: Customer360Service = Depends(get_customer360_service),
) -> Customer360BuildResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    profile = customer360_service.build_profile(aggregate)
    logger.info("Customer360 profile built for customer_id=%s profile_id=%s", customer_id, profile.profile_id)
    return Customer360BuildResponse(
        message="Customer360 profile built successfully",
        profile=Customer360ProfileResponse.model_validate(profile),
    )


@router.get(
    "/{customer_id}",
    summary="Get Customer360 profile",
    description="Returns the persisted Customer360 profile for a customer with UI-friendly nesting.",
)
def get_customer360_profile(
    customer_id: UUID,
    profile_repository: Customer360Repository = Depends(get_customer360_repository),
    db: MongoDatabase = Depends(get_db),
) -> dict:
    profile = profile_repository.get_profile_by_customer_id_or_raise(customer_id)
    customer_doc = db.customers.find_one({"customer_id": str(customer_id)}, {"_id": 0})
    first = (customer_doc or {}).get("first_name") or ""
    last = (customer_doc or {}).get("last_name") or ""
    full_name = f"{first} {last}".strip() or None
    base = Customer360ProfileResponse.model_validate(profile).model_dump(mode="json")
    return adapt_customer360_view({**base, **profile.__dict__}, full_name=full_name, customer_doc=customer_doc)
