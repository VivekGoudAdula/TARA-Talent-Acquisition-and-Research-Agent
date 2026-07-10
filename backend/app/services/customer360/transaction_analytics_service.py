"""Orchestrates transaction analytics, profile update, and feature store writes."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.analytics.transaction_analytics import TransactionAnalytics
from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.customer360 import CustomerAggregate
from app.schemas.transaction_analytics import TransactionAnalyticsProfile
from app.utils.exceptions import ProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# KPIs written to the feature store (per specification)
FEATURE_STORE_KPIS = (
    "average_transaction_amount",
    "monthly_transaction_count",
    "debit_transaction_count",
    "credit_transaction_count",
    "debit_credit_ratio",
    "cash_withdrawal_frequency",
    "cash_deposit_frequency",
    "upi_transaction_count",
    "card_transaction_count",
    "net_banking_transaction_count",
    "mobile_banking_transaction_count",
    "digital_payment_ratio",
    "merchant_diversity",
    "category_diversity",
    "transaction_consistency_score",
    "income_regularity_score",
    "expense_stability_score",
    "weekend_transaction_percentage",
    "night_transaction_percentage",
    "highest_transaction_amount",
    "lowest_transaction_amount",
    "largest_credit_transaction",
    "largest_debit_transaction",
)


class TransactionAnalyticsService:
    """
    Computes transaction analytics, persists KPIs to customer_360_profile
    and writes feature store entries for downstream ML/analytics pipelines.
    """

    def __init__(
        self,
        profile_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
        analytics_engine: TransactionAnalytics | None = None,
    ) -> None:
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._engine = analytics_engine or TransactionAnalytics()

    def compute_and_persist(self, aggregate: CustomerAggregate) -> TransactionAnalyticsProfile:
        """Run analytics, update profile, and write feature store entries."""
        customer_id = aggregate.customer.customer_id
        profile_row = self._profile_repo.get_profile_by_customer_id(customer_id)
        if profile_row is None:
            raise ProfileNotFoundError(customer_id)

        analytics = self._engine.calculate(aggregate)
        self._apply_to_profile(profile_row, analytics)
        profile_row.last_updated = datetime.utcnow()
        self._profile_repo.update_profile(profile_row)

        self._write_feature_store(customer_id, analytics)

        logger.info(
            "Transaction analytics persisted for customer_id=%s merchant_diversity=%s digital_ratio=%s",
            customer_id,
            analytics.merchant_diversity,
            analytics.digital_payment_ratio,
        )
        return analytics

    def get_analytics(self, customer_id: UUID) -> TransactionAnalyticsProfile:
        """Retrieve stored transaction analytics from the feature store."""
        entries = self._feature_repo.get_features_by_customer(customer_id)
        if not entries:
            raise ProfileNotFoundError(customer_id)

        data = self._feature_repo.features_to_dict(entries)
        text_fields = {"most_frequent_merchant", "most_frequent_category"}

        kwargs: dict = {}
        for field_name in TransactionAnalyticsProfile.model_fields:
            if field_name in text_fields:
                kwargs[field_name] = data.get(field_name)  # type: ignore[assignment]
            else:
                raw = data.get(field_name)
                kwargs[field_name] = Decimal(str(raw)) if raw is not None else Decimal("0")

        return TransactionAnalyticsProfile(**kwargs)

    def _write_feature_store(self, customer_id: UUID, analytics: TransactionAnalyticsProfile) -> None:
        features: dict[str, Decimal | int | str | None] = {}

        for kpi in FEATURE_STORE_KPIS:
            features[kpi] = getattr(analytics, kpi)

        features["most_frequent_merchant"] = analytics.most_frequent_merchant
        features["most_frequent_category"] = analytics.most_frequent_category

        self._feature_repo.upsert_features(customer_id, features)

    @staticmethod
    def _apply_to_profile(profile: Customer360Profile, analytics: TransactionAnalyticsProfile) -> None:
        profile.average_transaction_amount = analytics.average_transaction_amount
        profile.monthly_transaction_count = analytics.monthly_transaction_count
        profile.digital_payment_ratio = analytics.digital_payment_ratio
        profile.merchant_diversity = analytics.merchant_diversity
        profile.category_diversity = analytics.category_diversity
        profile.transaction_consistency_score = analytics.transaction_consistency_score
        profile.income_regularity_score = analytics.income_regularity_score
        profile.expense_stability_score = analytics.expense_stability_score
        profile.most_frequent_merchant = analytics.most_frequent_merchant
        profile.most_frequent_category = analytics.most_frequent_category
        profile.highest_transaction = analytics.highest_transaction_amount
        profile.largest_credit = analytics.largest_credit_transaction
        profile.largest_debit = analytics.largest_debit_transaction
        profile.weekend_transaction_percentage = analytics.weekend_transaction_percentage
        profile.night_transaction_percentage = analytics.night_transaction_percentage
