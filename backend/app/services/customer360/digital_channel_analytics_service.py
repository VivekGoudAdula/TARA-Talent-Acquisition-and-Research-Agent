"""Orchestrates digital & channel analytics, profile update, and feature store writes."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.analytics.behaviour_analytics import BehaviourAnalyticsEngine
from app.analytics.digital_channel_analytics import DigitalChannelAnalytics
from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.analytics.relationship_analytics import RelationshipAnalytics
from app.analytics.transaction_analytics import TransactionAnalytics
from app.models.customer360_profile import Customer360Profile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.behaviour_input import BehaviourAnalyticsInput
from app.schemas.customer360 import Customer360ProfileResponse, CustomerAggregate
from app.schemas.digital_channel_analytics import DigitalChannelProfile
from app.schemas.digital_channel_input import DigitalChannelAnalyticsInput
from app.schemas.relationship_input import RelationshipAnalyticsInput
from app.utils.exceptions import ProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_MODULE = "digital_channel_analytics"


class DigitalChannelAnalyticsService:
    """Computes digital & channel analytics and persists results."""

    def __init__(
        self,
        profile_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
        channel_engine: DigitalChannelAnalytics | None = None,
        financial_engine: FinancialAnalyticsEngine | None = None,
        transaction_engine: TransactionAnalytics | None = None,
        behaviour_engine: BehaviourAnalyticsEngine | None = None,
        relationship_engine: RelationshipAnalytics | None = None,
    ) -> None:
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._channel_engine = channel_engine or DigitalChannelAnalytics()
        self._financial_engine = financial_engine or FinancialAnalyticsEngine()
        self._transaction_engine = transaction_engine or TransactionAnalytics()
        self._behaviour_engine = behaviour_engine or BehaviourAnalyticsEngine()
        self._relationship_engine = relationship_engine or RelationshipAnalytics()

    def build_input(
        self,
        aggregate: CustomerAggregate,
        profile_row: Customer360Profile,
    ) -> DigitalChannelAnalyticsInput:
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
        relationship = self._relationship_engine.calculate(
            RelationshipAnalyticsInput(
                aggregate=aggregate,
                profile=profile_response,
                financial=financial,
                transaction=transaction,
                behaviour=behaviour,
            )
        )
        return DigitalChannelAnalyticsInput(
            aggregate=aggregate,
            profile=profile_response,
            financial=financial,
            transaction=transaction,
            behaviour=behaviour,
            relationship=relationship,
        )

    def compute_and_persist(self, aggregate: CustomerAggregate) -> DigitalChannelProfile:
        customer_id = aggregate.customer.customer_id
        profile_row = self._profile_repo.get_profile_by_customer_id(customer_id)
        if profile_row is None:
            raise ProfileNotFoundError(customer_id)

        data = self.build_input(aggregate, profile_row)
        channel_profile = self._channel_engine.calculate(data)

        self._apply_to_profile(profile_row, channel_profile)
        profile_row.last_updated = datetime.utcnow()
        self._profile_repo.update_profile(profile_row)
        self._write_feature_store(customer_id, channel_profile)

        logger.info(
            "Digital channel analytics persisted for customer_id=%s channel=%s",
            customer_id,
            channel_profile.preferred_channel,
        )
        return channel_profile

    def get_channel_profile(self, customer_id: UUID) -> DigitalChannelProfile:
        entries = self._feature_repo.get_features_by_customer(customer_id, source_module=SOURCE_MODULE)
        if not entries:
            raise ProfileNotFoundError(customer_id)

        data = self._feature_repo.features_to_dict(entries)
        return DigitalChannelProfile(
            customer_id=customer_id,
            digital_adoption_score=Decimal(str(data.get("digital_adoption_score", 0))),
            digital_maturity=str(data.get("digital_maturity", "Traditional")),
            preferred_channel=str(data.get("preferred_channel", "SMS")),
            secondary_channel=str(data.get("secondary_channel", "Email")),
            preferred_contact_time=str(data.get("preferred_contact_time", "Afternoon")),
            preferred_contact_day=str(data.get("preferred_contact_day", "Weekday")),
            voice_readiness_score=Decimal(str(data.get("voice_readiness_score", 0))),
            sms_readiness_score=Decimal(str(data.get("sms_readiness_score", 0))),
            whatsapp_readiness_score=Decimal(str(data.get("whatsapp_readiness_score", 0))),
            email_readiness_score=Decimal(str(data.get("email_readiness_score", 0))),
            engagement_score=Decimal(str(data.get("engagement_score", 0))),
        )

    def _write_feature_store(self, customer_id: UUID, profile: DigitalChannelProfile) -> None:
        features: dict[str, Decimal | int | str | None] = {
            "digital_adoption_score": profile.digital_adoption_score,
            "digital_maturity": profile.digital_maturity,
            "voice_readiness_score": profile.voice_readiness_score,
            "sms_readiness_score": profile.sms_readiness_score,
            "whatsapp_readiness_score": profile.whatsapp_readiness_score,
            "email_readiness_score": profile.email_readiness_score,
            "preferred_channel": profile.preferred_channel,
            "preferred_contact_time": profile.preferred_contact_time,
            "preferred_contact_day": profile.preferred_contact_day,
            "secondary_channel": profile.secondary_channel,
            "engagement_score": profile.engagement_score,
        }
        self._feature_repo.upsert_features(customer_id, features, source_module=SOURCE_MODULE)

    @staticmethod
    def _apply_to_profile(row: Customer360Profile, profile: DigitalChannelProfile) -> None:
        row.digital_adoption_score = profile.digital_adoption_score
        row.digital_maturity = profile.digital_maturity
        row.digital_banking_score = profile.digital_adoption_score
        row.preferred_channel = profile.preferred_channel
        row.secondary_channel = profile.secondary_channel
        row.preferred_contact_time = profile.preferred_contact_time
        row.preferred_contact_day = profile.preferred_contact_day
        row.voice_readiness_score = profile.voice_readiness_score
        row.sms_readiness_score = profile.sms_readiness_score
        row.whatsapp_readiness_score = profile.whatsapp_readiness_score
        row.email_readiness_score = profile.email_readiness_score
        row.engagement_score = profile.engagement_score
