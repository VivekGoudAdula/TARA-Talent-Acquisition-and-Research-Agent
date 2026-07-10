"""Orchestrates external lead analytics computation and persistence."""

from datetime import datetime
from uuid import UUID

from app.external.analytics.financial_capacity_analytics import FinancialCapacityAnalytics
from app.external.analytics.lead_behaviour_analytics import LeadBehaviourAnalytics
from app.external.analytics.lead_quality_analytics import LeadQualityAnalytics
from app.models.external_customer_profile import ExternalCustomerProfile
from app.models.external_lead import ExternalLead
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.schemas.external_analytics import ExternalLeadAnalyticsProfile
from app.schemas.external_analytics_input import ExternalLeadAnalyticsInput
from app.utils.exceptions import ExternalAnalyticsNotFoundError, ExternalProfileNotFoundError, LeadNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ExternalAnalyticsService:
    """Computes and persists external lead analytics from CRM lead data only."""

    def __init__(
        self,
        lead_repository: ExternalLeadRepository,
        profile_repository: ExternalProfileRepository,
        feature_store_repository: LeadFeatureStoreRepository,
        behaviour_engine: LeadBehaviourAnalytics | None = None,
        financial_engine: FinancialCapacityAnalytics | None = None,
        quality_engine: LeadQualityAnalytics | None = None,
    ) -> None:
        self._lead_repo = lead_repository
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._behaviour_engine = behaviour_engine or LeadBehaviourAnalytics()
        self._financial_engine = financial_engine or FinancialCapacityAnalytics()
        self._quality_engine = quality_engine or LeadQualityAnalytics()

    def compute_and_persist(self, lead_id: UUID, commit: bool = True) -> ExternalLeadAnalyticsProfile:
        lead = self._lead_repo.get_by_lead_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)

        profile = self._profile_repo.get_by_lead_id(lead_id)
        if profile is None:
            raise ExternalProfileNotFoundError(lead_id)

        analytics = self._run_pipeline(self._build_input(lead, profile))
        self._persist(lead_id, lead, profile, analytics, commit=commit)

        logger.info(
            "External analytics persisted for lead_id=%s quality=%s capacity=%s",
            lead_id,
            analytics.lead_quality_score,
            analytics.financial_capacity_score,
        )
        return analytics

    def build_all(self, limit: int | None = None) -> dict[str, int]:
        self._lead_repo._db.expire_all()
        fetch_limit = limit if limit is not None else 10000
        leads = self._lead_repo.get_all(limit=fetch_limit)
        succeeded = 0
        failed = 0

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def analytics(lead) -> bool:
            try:
                profile = self._profile_repo.get_by_lead_id(lead.lead_id)
                if profile is None:
                    return False
                if getattr(profile, "financial_capacity_score", None) is not None:
                    return True
                self.compute_and_persist(lead.lead_id, commit=False)
                return True
            except Exception as exc:
                logger.warning("External analytics failed for lead_id=%s: %s", lead.lead_id, exc)
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(analytics, l): l for l in leads}
            for fut in as_completed(futures):
                if fut.result():
                    succeeded += 1
                else:
                    failed += 1

        if succeeded > 0:
            self._lead_repo.commit()

        return {
            "leads_processed": len(leads),
            "leads_succeeded": succeeded,
            "leads_failed": failed,
        }

    def get_analytics(self, lead_id: UUID) -> ExternalLeadAnalyticsProfile:
        lead = self._lead_repo.get_by_lead_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)

        profile = self._profile_repo.get_by_lead_id(lead_id)
        if profile is None:
            raise ExternalProfileNotFoundError(lead_id)

        if profile.lead_quality_score is None:
            raise ExternalAnalyticsNotFoundError(lead_id)

        return self._run_pipeline(self._build_input(lead, profile))

    def _run_pipeline(self, data: ExternalLeadAnalyticsInput) -> ExternalLeadAnalyticsProfile:
        behaviour = self._behaviour_engine.calculate(data)
        financial = self._financial_engine.calculate(data)
        quality = self._quality_engine.calculate(data, behaviour, financial)

        preferred_channel = behaviour.preferred_contact_channel
        preferred_time = behaviour.preferred_contact_time

        return ExternalLeadAnalyticsProfile(
            lead_id=data.lead_id,
            lead_quality_score=quality.lead_quality_score,
            financial_capacity_score=financial.financial_capacity_score,
            campaign_engagement_score=behaviour.campaign_engagement_score,
            digital_readiness_score=behaviour.digital_readiness_score,
            communication_readiness_score=behaviour.communication_readiness_score,
            qualification_status=quality.qualification_status,
            priority_level=quality.priority_level,
            preferred_channel=preferred_channel,
            preferred_contact_time=preferred_time,
            estimated_repayment_capacity=financial.estimated_repayment_capacity,
            conversion_readiness=quality.conversion_readiness,
            sales_readiness=quality.sales_readiness,
            income_stability=financial.income_stability,
            emi_burden=financial.emi_burden,
            credit_quality=financial.credit_quality,
            affordability_level=financial.affordability_level,
            referral_quality_score=behaviour.referral_quality_score,
            marketing_responsiveness_score=behaviour.marketing_responsiveness_score,
            customer_persona_confidence=behaviour.customer_persona_confidence,
            behaviour=behaviour,
            financial_capacity=financial,
            lead_quality=quality,
        )

    def _persist(
        self,
        lead_id: UUID,
        lead: ExternalLead,
        profile: ExternalCustomerProfile,
        analytics: ExternalLeadAnalyticsProfile,
        commit: bool = True,
    ) -> None:
        self._profile_repo.apply_analytics(
            lead_id,
            campaign_engagement_score=analytics.campaign_engagement_score,
            digital_readiness_score=analytics.digital_readiness_score,
            communication_readiness_score=analytics.communication_readiness_score,
            financial_capacity_score=analytics.financial_capacity_score,
            estimated_repayment_capacity=analytics.estimated_repayment_capacity,
            lead_quality_score=analytics.lead_quality_score,
            qualification_status=analytics.qualification_status,
            priority_level=analytics.priority_level,
            preferred_channel=analytics.preferred_channel,
            preferred_contact_time=analytics.preferred_contact_time,
            commit=False,
        )

        features = {
            "lead_score": profile.lead_score,
            "financial_capacity_score": analytics.financial_capacity_score,
            "campaign_engagement_score": analytics.campaign_engagement_score,
            "digital_readiness_score": analytics.digital_readiness_score,
            "lead_quality_score": analytics.lead_quality_score,
            "credit_quality": analytics.credit_quality,
            "preferred_channel": analytics.preferred_channel,
            "preferred_contact_time": analytics.preferred_contact_time,
        }
        self._feature_repo.upsert_features(lead_id, features, commit=False)

        lead.lead_status = "ANALYTICS_READY"
        lead.updated_at = datetime.utcnow()
        self._lead_repo._db.external_leads.replace_one(
            {"lead_id": str(lead_id)}, lead.to_doc(), upsert=True
        )

    @staticmethod
    def _build_input(lead: ExternalLead, profile: ExternalCustomerProfile) -> ExternalLeadAnalyticsInput:
        return ExternalLeadAnalyticsInput(
            lead_id=lead.lead_id,
            external_reference=lead.external_reference,
            full_name=lead.full_name,
            phone_number=lead.phone_number,
            email=lead.email,
            age=lead.age or 30,
            gender=lead.gender or "Unknown",
            occupation=lead.occupation or "Unknown",
            employer=lead.employer or "Unknown",
            estimated_income=lead.estimated_income or 0,
            credit_score=lead.credit_score or 650,
            city=lead.city or "Unknown",
            state=lead.state or "Unknown",
            preferred_language=lead.preferred_language or "English",
            referral_source=lead.referral_source or "Direct",
            campaign=lead.campaign or "General",
            consent=lead.consent,
            lead_status=lead.lead_status,
            lead_created_date=lead.lead_created_date,
            income_segment=profile.income_segment,
            customer_persona=profile.customer_persona,
            relationship_potential=profile.relationship_potential or 0,
            financial_stability=profile.financial_stability or 0,
            digital_adoption=profile.digital_adoption or 0,
            preferred_channel=profile.preferred_channel,
            preferred_contact_time=profile.preferred_contact_time,
            cross_sell_potential=profile.cross_sell_potential or 0,
            lead_score=profile.lead_score or 0,
            existing_bank=profile.existing_bank,
            existing_products=profile.existing_products,
            monthly_emi=profile.monthly_emi or 0,
            home_owner=profile.home_owner or False,
        )
