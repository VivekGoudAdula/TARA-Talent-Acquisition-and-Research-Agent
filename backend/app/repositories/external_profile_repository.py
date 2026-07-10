"""Repository for external_customer_profile collection."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.external.lead_enrichment import EnrichedLeadProfile
from app.models.external_customer_profile import ExternalCustomerProfile
from app.utils.exceptions import ExternalProfileNotFoundError, UnifiedProfileNotFoundError


class ExternalProfileRepository:
    """Data access layer for enriched external lead profiles."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._profile_cache = {}

    def upsert_profile(
        self, lead_id: UUID, enriched: EnrichedLeadProfile, commit: bool = True
    ) -> ExternalCustomerProfile:
        existing = self.get_by_lead_id(lead_id)
        profile_id = existing.profile_id if existing else uuid4()
        now = datetime.utcnow()

        profile = ExternalCustomerProfile(
            profile_id=profile_id,
            lead_id=lead_id,
            income_segment=enriched.income_segment,
            customer_persona=enriched.customer_persona,
            relationship_potential=enriched.relationship_potential,
            financial_stability=enriched.financial_stability,
            digital_adoption=enriched.digital_adoption,
            preferred_channel=enriched.preferred_channel,
            preferred_contact_time=enriched.preferred_contact_time,
            cross_sell_potential=enriched.cross_sell_potential,
            lead_score=enriched.lead_score,
            existing_bank=enriched.existing_bank,
            existing_products=enriched.existing_products,
            monthly_emi=enriched.monthly_emi,
            home_owner=enriched.home_owner,
            last_updated=now,
        )
        if existing:
            for attr in (
                "campaign_engagement_score",
                "digital_readiness_score",
                "communication_readiness_score",
                "financial_capacity_score",
                "estimated_repayment_capacity",
                "lead_quality_score",
                "qualification_status",
                "priority_level",
                "lead_authenticity_score",
                "income_confidence_score",
                "income_confidence_level",
                "fraud_score",
                "fraud_risk",
                "fraud_reason_codes",
                "kyc_readiness",
                "kyc_missing_items",
                "last_validation_timestamp",
                "financial_health_score",
                "repayment_behaviour_score",
                "digital_engagement_score",
            ):
                if hasattr(existing, attr):
                    setattr(profile, attr, getattr(existing, attr))

        self._db.external_customer_profile.replace_one(
            {"lead_id": str(lead_id)},
            profile.to_doc(),
            upsert=True,
        )
        return profile

    def get_by_lead_id(self, lead_id: UUID) -> ExternalCustomerProfile | None:
        doc = self._db.external_customer_profile.find_one({"lead_id": str(lead_id)})
        return ExternalCustomerProfile.from_doc(doc)

    def get_by_lead_id_or_raise(self, lead_id: UUID) -> ExternalCustomerProfile:
        profile = self.get_by_lead_id(lead_id)
        if profile is None:
            raise ExternalProfileNotFoundError(lead_id)
        return profile

    def count_all(self) -> int:
        return self._db.external_customer_profile.count_documents({})

    def apply_analytics(
        self,
        lead_id: UUID,
        *,
        campaign_engagement_score: Decimal,
        digital_readiness_score: Decimal,
        communication_readiness_score: Decimal,
        financial_capacity_score: Decimal,
        estimated_repayment_capacity: Decimal,
        lead_quality_score: Decimal,
        qualification_status: str,
        priority_level: str,
        preferred_channel: str,
        preferred_contact_time: str,
        commit: bool = True,
    ) -> ExternalCustomerProfile:
        profile = self.get_by_lead_id_or_raise(lead_id)
        profile.campaign_engagement_score = campaign_engagement_score
        profile.digital_readiness_score = digital_readiness_score
        profile.communication_readiness_score = communication_readiness_score
        profile.financial_capacity_score = financial_capacity_score
        profile.estimated_repayment_capacity = estimated_repayment_capacity
        profile.lead_quality_score = lead_quality_score
        profile.qualification_status = qualification_status
        profile.priority_level = priority_level
        profile.preferred_channel = preferred_channel
        profile.preferred_contact_time = preferred_contact_time
        profile.last_updated = datetime.utcnow()
        self._db.external_customer_profile.replace_one(
            {"lead_id": str(lead_id)}, profile.to_doc(), upsert=True
        )
        return profile

    def apply_intelligence(
        self,
        lead_id: UUID,
        *,
        lead_authenticity_score: Decimal,
        income_confidence_score: Decimal,
        income_confidence_level: str,
        fraud_score: Decimal,
        fraud_risk: str,
        fraud_reason_codes: str,
        kyc_readiness: str,
        kyc_missing_items: str,
        last_validation_timestamp: datetime,
        commit: bool = True,
    ) -> ExternalCustomerProfile:
        profile = self.get_by_lead_id_or_raise(lead_id)
        profile.lead_authenticity_score = lead_authenticity_score
        profile.income_confidence_score = income_confidence_score
        profile.income_confidence_level = income_confidence_level
        profile.fraud_score = fraud_score
        profile.fraud_risk = fraud_risk
        profile.fraud_reason_codes = fraud_reason_codes
        profile.kyc_readiness = kyc_readiness
        profile.kyc_missing_items = kyc_missing_items
        profile.last_validation_timestamp = last_validation_timestamp
        profile.last_updated = datetime.utcnow()
        self._db.external_customer_profile.replace_one(
            {"lead_id": str(lead_id)}, profile.to_doc(), upsert=True
        )
        return profile

    def get_profile_by_profile_id(self, profile_id: UUID) -> ExternalCustomerProfile | None:
        key = str(profile_id)
        if key in self._profile_cache:
            return self._profile_cache[key]
        doc = self._db.external_customer_profile.find_one(
            {"profile_id": key}
        )
        profile = ExternalCustomerProfile.from_doc(doc) if doc else None
        if profile:
            self._profile_cache[key] = profile
        return profile

    def get_all_profiles(self) -> list[ExternalCustomerProfile]:
        docs = self._db.external_customer_profile.find()
        return [ExternalCustomerProfile.from_doc(d) for d in docs if d]

    def apply_behaviour_summary(
        self,
        profile_id: UUID,
        *,
        financial_health_score: Decimal,
        repayment_behaviour_score: Decimal,
        digital_engagement_score: Decimal,
        commit: bool = True,
    ) -> ExternalCustomerProfile:
        profile = self.get_profile_by_profile_id(profile_id)
        if profile is None:
            raise UnifiedProfileNotFoundError(profile_id)
        profile.financial_health_score = financial_health_score
        profile.repayment_behaviour_score = repayment_behaviour_score
        profile.digital_engagement_score = digital_engagement_score
        profile.last_updated = datetime.utcnow()
        self._db.external_customer_profile.replace_one(
            {"profile_id": str(profile_id)}, profile.to_doc(), upsert=True
        )
        return profile
