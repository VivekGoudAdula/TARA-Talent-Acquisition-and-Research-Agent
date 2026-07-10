"""Financial analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.ui_adapters import adapt_financial_profile
from app.dependencies import get_aggregation_service, get_financial_profile_service, get_customer360_repository, get_db
from app.db.mongo import MongoDatabase
from app.repositories.customer360_repository import Customer360Repository
from app.schemas.financial_profile import FinancialAnalyticsResponse, FinancialProfile
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.financial_profile_service import FinancialProfileService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360", tags=["Financial Analytics"])
frontend_router = APIRouter(prefix="/api/financial", tags=["Financial Analytics Frontend"])


@router.post(
    "/financial/{customer_id}",
    response_model=FinancialAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute financial KPIs",
    description=(
        "Runs the deterministic Financial Analytics Engine on aggregated banking data "
        "and updates the Customer360 profile with income, expense, savings, and score KPIs."
    ),
)
def compute_financial_profile(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    financial_service: FinancialProfileService = Depends(get_financial_profile_service),
) -> FinancialAnalyticsResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    financial_profile = financial_service.compute_and_persist(aggregate)
    logger.info("Financial profile computed for customer_id=%s", customer_id)
    return FinancialAnalyticsResponse(
        message="Financial analytics computed and profile updated successfully",
        financial_profile=FinancialProfile.model_validate(financial_profile),
    )


@frontend_router.get(
    "/{customer_id}",
    summary="Get financial KPIs for frontend",
)
def get_financial_profile_frontend(
    customer_id: UUID,
    profile_repository: Customer360Repository = Depends(get_customer360_repository),
    db: MongoDatabase = Depends(get_db),
) -> dict:
    profile = profile_repository.get_profile_by_customer_id_or_raise(customer_id)
    profile_doc = db.customer_360_profile.find_one({"customer_id": str(customer_id)}, {"_id": 0}) or {}

    monthly_income = profile.monthly_income or 0
    monthly_savings = profile.monthly_savings or 0
    savings_ratio = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0

    base = FinancialProfile(
        monthly_income=monthly_income,
        monthly_expense=profile.monthly_expense or 0,
        monthly_savings=monthly_savings,
        savings_ratio=savings_ratio,
        average_balance=profile.average_balance or 0,
        cash_flow_score=profile.cash_flow_score or 0,
        liquidity_score=profile.liquidity_score or 0,
        debt_ratio=profile.debt_ratio or 0,
        investment_ratio=profile.investment_ratio or 0,
        emi_burden=profile.emi_burden or 0,
    ).model_dump(mode="json")
    return adapt_financial_profile(base, profile_doc)

