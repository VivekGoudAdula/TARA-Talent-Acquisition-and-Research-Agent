"""Persists financial KPIs onto the Customer360 profile."""

from datetime import datetime

from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.schemas.customer360 import CustomerAggregate
from app.schemas.financial_profile import FinancialProfile
from app.utils.exceptions import ProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FinancialProfileService:
    """
    Orchestrates financial analytics computation and profile persistence.

    Requires an existing Customer360 profile (built via Phase 2.1 build endpoint).
    """

    def __init__(
        self,
        profile_repository: Customer360Repository,
        analytics_engine: FinancialAnalyticsEngine | None = None,
    ) -> None:
        self._profile_repo = profile_repository
        self._engine = analytics_engine or FinancialAnalyticsEngine()

    def compute_and_persist(
        self,
        aggregate: CustomerAggregate,
    ) -> FinancialProfile:
        """Calculate financial KPIs and update the customer_360_profile row."""
        customer_id = aggregate.customer.customer_id
        profile = self._profile_repo.get_profile_by_customer_id(customer_id)
        if profile is None:
            raise ProfileNotFoundError(customer_id)

        financial = self._engine.calculate(aggregate)
        self._apply_financial_fields(profile, financial)
        profile.last_updated = datetime.utcnow()
        self._profile_repo.update_profile(profile)

        logger.info(
            "Financial KPIs persisted for customer_id=%s cash_flow=%s liquidity=%s",
            customer_id,
            financial.cash_flow_score,
            financial.liquidity_score,
        )
        return financial

    @staticmethod
    def _apply_financial_fields(profile: Customer360Profile, financial: FinancialProfile) -> None:
        profile.monthly_income = financial.monthly_income
        profile.monthly_expense = financial.monthly_expense
        profile.monthly_savings = financial.monthly_savings
        profile.average_balance = financial.average_balance
        profile.cash_flow_score = financial.cash_flow_score
        profile.liquidity_score = financial.liquidity_score
        profile.debt_ratio = financial.debt_ratio
        profile.investment_ratio = financial.investment_ratio
        profile.emi_burden = financial.emi_burden
