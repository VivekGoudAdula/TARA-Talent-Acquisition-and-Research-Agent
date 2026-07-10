"""Orchestrates customer health analytics, profile update, and feature store writes."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.analytics.behaviour_analytics import BehaviourAnalyticsEngine
from app.analytics.customer_health_analytics import CustomerHealthAnalytics
from app.analytics.digital_channel_analytics import DigitalChannelAnalytics
from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.analytics.relationship_analytics import RelationshipAnalytics
from app.analytics.transaction_analytics import TransactionAnalytics
from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.behaviour_input import BehaviourAnalyticsInput
from app.schemas.customer360 import Customer360ProfileResponse, CustomerAggregate
from app.schemas.customer_health_analytics import CustomerHealthProfile
from app.schemas.customer_health_input import CustomerHealthAnalyticsInput
from app.schemas.digital_channel_input import DigitalChannelAnalyticsInput
from app.schemas.relationship_input import RelationshipAnalyticsInput
from app.utils.exceptions import ProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_MODULE = "customer_health_analytics"


class CustomerHealthAnalyticsService:
    """Computes CRM customer health analytics and persists results."""

    def __init__(
        self,
        profile_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
        health_engine: CustomerHealthAnalytics | None = None,
        financial_engine: FinancialAnalyticsEngine | None = None,
        transaction_engine: TransactionAnalytics | None = None,
        behaviour_engine: BehaviourAnalyticsEngine | None = None,
        relationship_engine: RelationshipAnalytics | None = None,
        digital_engine: DigitalChannelAnalytics | None = None,
    ) -> None:
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._health_engine = health_engine or CustomerHealthAnalytics()
        self._financial_engine = financial_engine or FinancialAnalyticsEngine()
        self._transaction_engine = transaction_engine or TransactionAnalytics()
        self._behaviour_engine = behaviour_engine or BehaviourAnalyticsEngine()
        self._relationship_engine = relationship_engine or RelationshipAnalytics()
        self._digital_engine = digital_engine or DigitalChannelAnalytics()

    def build_input(
        self,
        aggregate: CustomerAggregate,
        profile_row: Customer360Profile,
    ) -> CustomerHealthAnalyticsInput:
        profile_response = Customer360ProfileResponse.model_validate(profile_row)
        financial = self._financial_engine.calculate(aggregate)
        transaction = self._transaction_engine.calculate(aggregate)
        behaviour = self._behaviour_engine.calculate(
            BehaviourAnalyticsInput(
                aggregate=aggregate, financial=financial,
                transaction=transaction, profile=profile_response,
            )
        )
        relationship = self._relationship_engine.calculate(
            RelationshipAnalyticsInput(
                aggregate=aggregate, profile=profile_response,
                financial=financial, transaction=transaction, behaviour=behaviour,
            )
        )
        digital = self._digital_engine.calculate(
            DigitalChannelAnalyticsInput(
                aggregate=aggregate, profile=profile_response,
                financial=financial, transaction=transaction,
                behaviour=behaviour, relationship=relationship,
            )
        )
        return CustomerHealthAnalyticsInput(
            aggregate=aggregate,
            profile=profile_response,
            financial=financial,
            transaction=transaction,
            behaviour=behaviour,
            relationship=relationship,
            digital=digital,
        )

    def compute_and_persist(self, aggregate: CustomerAggregate) -> CustomerHealthProfile:
        customer_id = aggregate.customer.customer_id
        profile_row = self._profile_repo.get_profile_by_customer_id(customer_id)
        if profile_row is None:
            raise ProfileNotFoundError(customer_id)

        data = self.build_input(aggregate, profile_row)
        health = self._health_engine.calculate(data)

        self._apply_to_profile(profile_row, health)
        profile_row.last_updated = datetime.utcnow()
        self._profile_repo.update_profile(profile_row)
        self._write_feature_store(customer_id, health)

        logger.info(
            "Customer health persisted for customer_id=%s band=%s health=%s",
            customer_id, health.risk_band, health.customer_health_score,
        )
        return health

    def get_health_profile(self, customer_id: UUID) -> CustomerHealthProfile:
        entries = self._feature_repo.get_features_by_customer(customer_id, source_module=SOURCE_MODULE)
        if not entries:
            raise ProfileNotFoundError(customer_id)

        data = self._feature_repo.features_to_dict(entries)
        reasons_raw = data.get("reason_codes", "[]")
        reasons = json.loads(str(reasons_raw)) if reasons_raw else []

        return CustomerHealthProfile(
            customer_id=customer_id,
            customer_health_score=Decimal(str(data.get("customer_health_score", 0))),
            financial_stress_score=Decimal(str(data.get("financial_stress_score", 0))),
            churn_risk_score=Decimal(str(data.get("churn_risk_score", 0))),
            dormancy_risk=str(data.get("dormancy_risk", "Low")),
            relationship_stability=Decimal(str(data.get("relationship_stability", 0))),
            retention_score=Decimal(str(data.get("retention_score", 0))),
            cross_sell_readiness=Decimal(str(data.get("cross_sell_readiness", 0))),
            risk_band=str(data.get("risk_band", "Monitor")),
            reason_codes=reasons,
        )

    def _write_feature_store(self, customer_id: UUID, health: CustomerHealthProfile) -> None:
        features: dict[str, Decimal | int | str | None] = {
            "customer_health_score": health.customer_health_score,
            "financial_stress_score": health.financial_stress_score,
            "churn_risk_score": health.churn_risk_score,
            "dormancy_risk": health.dormancy_risk,
            "relationship_stability": health.relationship_stability,
            "retention_score": health.retention_score,
            "cross_sell_readiness": health.cross_sell_readiness,
            "risk_band": health.risk_band,
            "reason_codes": json.dumps(health.reason_codes),
        }
        self._feature_repo.upsert_features(customer_id, features, source_module=SOURCE_MODULE)

    @staticmethod
    def _apply_to_profile(row: Customer360Profile, health: CustomerHealthProfile) -> None:
        row.customer_health_score = health.customer_health_score
        row.financial_stress_score = health.financial_stress_score
        row.churn_risk_score = health.churn_risk_score
        row.dormancy_risk = health.dormancy_risk
        row.relationship_stability = health.relationship_stability
        row.retention_score = health.retention_score
        row.cross_sell_readiness = health.cross_sell_readiness
        row.risk_band = health.risk_band
        row.reason_codes = json.dumps(health.reason_codes)
        row.risk_score = health.churn_risk_score
