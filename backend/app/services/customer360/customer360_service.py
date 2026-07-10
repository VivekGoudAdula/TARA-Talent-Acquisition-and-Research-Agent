"""Customer360 Service — builds unified profiles from aggregated data."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.schemas.customer360 import CustomerAggregate
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class Customer360Service:
    """
    Builds and persists Customer360 profiles from CustomerAggregate objects.

    Milestone 1 scope: populate only direct values sourced from core banking
    tables. All analytics and scoring fields remain NULL.
    """

    def __init__(self, profile_repository: Customer360Repository) -> None:
        self._profile_repo = profile_repository

    def build_profile(self, aggregate: CustomerAggregate) -> Customer360Profile:
        """
        Create or refresh a Customer360Profile from aggregated banking data.

        Direct fields populated:
            age, gender, occupation, annual_income, city, state,
            preferred_language, customer_since, average_balance, monthly_income

        Analytics fields left NULL:
            monthly_expense, monthly_savings, all scores, segment, channel, risk
        """
        customer = aggregate.customer
        customer_id = customer.customer_id

        average_balance = self._calculate_average_balance(aggregate)
        monthly_income = self._calculate_monthly_income(customer.annual_income)

        existing = self._profile_repo.get_profile_by_customer_id(customer_id)
        now = datetime.utcnow()

        if existing:
            logger.info("Updating existing Customer360 profile for customer_id=%s", customer_id)
            profile = existing
        else:
            logger.info("Creating new Customer360 profile for customer_id=%s", customer_id)
            profile = Customer360Profile(profile_id=uuid4(), customer_id=customer_id)

        profile.age = customer.age
        profile.gender = customer.gender
        profile.occupation = customer.occupation
        profile.annual_income = customer.annual_income
        profile.city = customer.city
        profile.state = customer.state
        profile.preferred_language = customer.preferred_language
        profile.customer_since = customer.created_at.date()
        profile.average_balance = average_balance
        profile.monthly_income = monthly_income
        profile.last_updated = now

        if existing:
            return self._profile_repo.update_profile(profile)
        return self._profile_repo.create_profile(profile)

    @staticmethod
    def _calculate_average_balance(aggregate: CustomerAggregate) -> Decimal | None:
        if not aggregate.accounts:
            return None
        total = sum(account.balance for account in aggregate.accounts)
        return (total / len(aggregate.accounts)).quantize(Decimal("0.01"))

    @staticmethod
    def _calculate_monthly_income(annual_income: Decimal) -> Decimal:
        return (annual_income / Decimal("12")).quantize(Decimal("0.01"))
