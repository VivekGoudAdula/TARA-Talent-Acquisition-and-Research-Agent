"""Orchestrates relationship analytics, profile update, and feature store writes."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.analytics.behaviour_analytics import BehaviourAnalyticsEngine
from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.analytics.relationship_analytics import RelationshipAnalytics
from app.analytics.transaction_analytics import TransactionAnalytics
from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.behaviour_input import BehaviourAnalyticsInput
from app.schemas.customer360 import Customer360ProfileResponse, CustomerAggregate
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.relationship_input import RelationshipAnalyticsInput
from app.utils.exceptions import ProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_MODULE = "relationship_analytics"


class RelationshipAnalyticsService:
    """Computes banking relationship analytics and persists results."""

    def __init__(
        self,
        profile_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
        relationship_engine: RelationshipAnalytics | None = None,
        financial_engine: FinancialAnalyticsEngine | None = None,
        transaction_engine: TransactionAnalytics | None = None,
        behaviour_engine: BehaviourAnalyticsEngine | None = None,
    ) -> None:
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._relationship_engine = relationship_engine or RelationshipAnalytics()
        self._financial_engine = financial_engine or FinancialAnalyticsEngine()
        self._transaction_engine = transaction_engine or TransactionAnalytics()
        self._behaviour_engine = behaviour_engine or BehaviourAnalyticsEngine()

    def build_input(
        self,
        aggregate: CustomerAggregate,
        profile_row: Customer360Profile,
    ) -> RelationshipAnalyticsInput:
        profile_response = Customer360ProfileResponse.model_validate(profile_row)
        financial = self._financial_engine.calculate(aggregate)
        transaction = self._transaction_engine.calculate(aggregate)
        behaviour = self._behaviour_engine.calculate(
            BehaviourAnalyticsInput(
                aggregate=aggregate,
                financial=financial,
                transaction=transaction,
                profile=profile_response,
            )
        )
        return RelationshipAnalyticsInput(
            aggregate=aggregate,
            profile=profile_response,
            financial=financial,
            transaction=transaction,
            behaviour=behaviour,
        )

    def compute_and_persist(self, aggregate: CustomerAggregate) -> RelationshipProfile:
        customer_id = aggregate.customer.customer_id
        profile_row = self._profile_repo.get_profile_by_customer_id(customer_id)
        if profile_row is None:
            raise ProfileNotFoundError(customer_id)

        data = self.build_input(aggregate, profile_row)
        relationship = self._relationship_engine.calculate(data)

        self._apply_to_profile(profile_row, relationship)
        profile_row.last_updated = datetime.utcnow()
        self._profile_repo.update_profile(profile_row)
        self._write_feature_store(customer_id, relationship)

        logger.info(
            "Relationship analytics persisted for customer_id=%s tier=%s",
            customer_id,
            relationship.relationship_tier,
        )
        return relationship

    def get_relationship_profile(self, customer_id: UUID) -> RelationshipProfile:
        entries = self._feature_repo.get_features_by_customer(customer_id, source_module=SOURCE_MODULE)
        if not entries:
            raise ProfileNotFoundError(customer_id)

        data = self._feature_repo.features_to_dict(entries)
        missing_raw = data.get("missing_products", "[]")
        missing = json.loads(str(missing_raw)) if missing_raw else []

        return RelationshipProfile(
            customer_id=customer_id,
            number_of_accounts=int(data.get("number_of_accounts", 0)),
            number_of_products=int(data.get("number_of_products", 0)),
            relationship_age=Decimal(str(data.get("relationship_age", 0))),
            relationship_strength_score=Decimal(str(data.get("relationship_strength_score", 0))),
            loyalty_score=Decimal(str(data.get("loyalty_score", 0))),
            product_penetration_score=Decimal(str(data.get("product_penetration_score", 0))),
            product_diversity_score=Decimal(str(data.get("product_diversity_score", 0))),
            bank_dependency_score=Decimal(str(data.get("bank_dependency_score", 0))),
            relationship_tier=str(data.get("relationship_tier", "Bronze")),
            estimated_customer_value=Decimal(str(data.get("estimated_customer_value", 0))),
            missing_products=missing,
            engagement_score=Decimal(str(data.get("engagement_score", 0))),
            relationship_stability=Decimal(str(data.get("relationship_stability", 0))),
            primary_banking_score=Decimal(str(data.get("primary_banking_score", 0))),
        )

    def _write_feature_store(self, customer_id: UUID, relationship: RelationshipProfile) -> None:
        features: dict[str, Decimal | int | str | None] = {
            "relationship_strength_score": relationship.relationship_strength_score,
            "loyalty_score": relationship.loyalty_score,
            "product_penetration_score": relationship.product_penetration_score,
            "product_diversity_score": relationship.product_diversity_score,
            "bank_dependency_score": relationship.bank_dependency_score,
            "engagement_score": relationship.engagement_score,
            "relationship_age": relationship.relationship_age,
            "relationship_tier": relationship.relationship_tier,
            "estimated_customer_value": relationship.estimated_customer_value,
            "number_of_accounts": relationship.number_of_accounts,
            "number_of_products": relationship.number_of_products,
            "missing_products": json.dumps(relationship.missing_products),
            "relationship_stability": relationship.relationship_stability,
            "primary_banking_score": relationship.primary_banking_score,
        }
        self._feature_repo.upsert_features(customer_id, features, source_module=SOURCE_MODULE)

    @staticmethod
    def _apply_to_profile(profile: Customer360Profile, relationship: RelationshipProfile) -> None:
        profile.relationship_age = relationship.relationship_age
        profile.relationship_strength_score = relationship.relationship_strength_score
        profile.loyalty_score = relationship.loyalty_score
        profile.product_penetration_score = relationship.product_penetration_score
        profile.product_diversity_score = relationship.product_diversity_score
        profile.bank_dependency_score = relationship.bank_dependency_score
        profile.relationship_tier = relationship.relationship_tier
        profile.estimated_customer_value = relationship.estimated_customer_value
        profile.number_of_accounts = relationship.number_of_accounts
        profile.number_of_products = relationship.number_of_products
        profile.missing_products = json.dumps(relationship.missing_products)
        profile.engagement_score = relationship.engagement_score
