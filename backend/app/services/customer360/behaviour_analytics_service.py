"""Orchestrates behaviour analytics, profile update, and feature store writes."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.analytics.behaviour_analytics import BehaviourAnalyticsEngine
from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.analytics.transaction_analytics import TransactionAnalytics
from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.behaviour_input import BehaviourAnalyticsInput
from app.schemas.customer360 import Customer360ProfileResponse, CustomerAggregate
from app.schemas.financial_profile import FinancialProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile
from app.utils.exceptions import ProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_MODULE = "behaviour_analytics"

FEATURE_STORE_KEYS = (
    "shopping_score",
    "travel_score",
    "food_score",
    "investment_score",
    "fuel_score",
    "education_score",
    "healthcare_score",
    "entertainment_score",
    "top_interest",
    "lifestyle_tags",
)


class BehaviourAnalyticsService:
    """Computes behaviour analytics and persists to profile + feature store."""

    def __init__(
        self,
        profile_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
        behaviour_engine: BehaviourAnalyticsEngine | None = None,
        financial_engine: FinancialAnalyticsEngine | None = None,
        transaction_engine: TransactionAnalytics | None = None,
    ) -> None:
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._behaviour_engine = behaviour_engine or BehaviourAnalyticsEngine()
        self._financial_engine = financial_engine or FinancialAnalyticsEngine()
        self._transaction_engine = transaction_engine or TransactionAnalytics()

    def build_input(
        self,
        aggregate: CustomerAggregate,
        profile_row: Customer360Profile,
    ) -> BehaviourAnalyticsInput:
        financial = self._financial_engine.calculate(aggregate)
        transaction = self._transaction_engine.calculate(aggregate)
        profile_response = Customer360ProfileResponse.model_validate(profile_row)
        return BehaviourAnalyticsInput(
            aggregate=aggregate,
            financial=financial,
            transaction=transaction,
            profile=profile_response,
        )

    def compute_and_persist(self, aggregate: CustomerAggregate) -> BehaviourProfile:
        customer_id = aggregate.customer.customer_id
        profile_row = self._profile_repo.get_profile_by_customer_id(customer_id)
        if profile_row is None:
            raise ProfileNotFoundError(customer_id)

        data = self.build_input(aggregate, profile_row)
        behaviour = self._behaviour_engine.calculate(data)

        self._apply_to_profile(profile_row, behaviour)
        profile_row.last_updated = datetime.utcnow()
        self._profile_repo.update_profile(profile_row)
        self._write_feature_store(customer_id, behaviour)

        logger.info(
            "Behaviour analytics persisted for customer_id=%s tags=%s",
            customer_id,
            behaviour.lifestyle_tags,
        )
        return behaviour

    def get_behaviour_profile(self, customer_id: UUID) -> BehaviourProfile:
        entries = self._feature_repo.get_features_by_customer(customer_id, source_module=SOURCE_MODULE)
        if not entries:
            raise ProfileNotFoundError(customer_id)

        data = self._feature_repo.features_to_dict(entries)
        tags_raw = data.get("lifestyle_tags", "")
        tags = json.loads(str(tags_raw)) if tags_raw else []

        return BehaviourProfile(
            customer_id=customer_id,
            shopping_score=Decimal(str(data.get("shopping_score", 0))),
            travel_score=Decimal(str(data.get("travel_score", 0))),
            food_score=Decimal(str(data.get("food_score", 0))),
            healthcare_score=Decimal(str(data.get("healthcare_score", 0))),
            investment_score=Decimal(str(data.get("investment_score", 0))),
            fuel_score=Decimal(str(data.get("fuel_score", 0))),
            education_score=Decimal(str(data.get("education_score", 0))),
            entertainment_score=Decimal(str(data.get("entertainment_score", 0))),
            top_interest=str(data["top_interest"]) if data.get("top_interest") else None,
            secondary_interest=str(data["secondary_interest"]) if data.get("secondary_interest") else None,
            third_interest=str(data["third_interest"]) if data.get("third_interest") else None,
            lifestyle_tags=tags,
        )

    def _write_feature_store(self, customer_id: UUID, behaviour: BehaviourProfile) -> None:
        features: dict[str, Decimal | int | str | None] = {
            "shopping_score": behaviour.shopping_score,
            "travel_score": behaviour.travel_score,
            "food_score": behaviour.food_score,
            "investment_score": behaviour.investment_score,
            "fuel_score": behaviour.fuel_score,
            "education_score": behaviour.education_score,
            "healthcare_score": behaviour.healthcare_score,
            "entertainment_score": behaviour.entertainment_score,
            "top_interest": behaviour.top_interest,
            "secondary_interest": behaviour.secondary_interest,
            "third_interest": behaviour.third_interest,
            "lifestyle_tags": json.dumps(behaviour.lifestyle_tags),
        }
        self._feature_repo.upsert_features(customer_id, features, source_module=SOURCE_MODULE)

    @staticmethod
    def _apply_to_profile(profile: Customer360Profile, behaviour: BehaviourProfile) -> None:
        profile.shopping_score = behaviour.shopping_score
        profile.travel_score = behaviour.travel_score
        profile.food_score = behaviour.food_score
        profile.investment_score = behaviour.investment_score
        profile.healthcare_score = behaviour.healthcare_score
        profile.entertainment_score = behaviour.entertainment_score
        profile.fuel_score = behaviour.fuel_score
        profile.education_score = behaviour.education_score
        profile.top_interest = behaviour.top_interest
        profile.secondary_interest = behaviour.secondary_interest
        profile.lifestyle_tags = json.dumps(behaviour.lifestyle_tags)
