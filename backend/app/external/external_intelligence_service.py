"""Orchestrates external lead intelligence validation engines."""

import json
from datetime import datetime
from uuid import UUID

from app.external.intelligence.fraud_screening_engine import FraudScreeningEngine
from app.external.intelligence.income_confidence_engine import IncomeConfidenceEngine
from app.external.intelligence.kyc_readiness_engine import KycReadinessEngine
from app.external.intelligence.lead_authenticity_engine import LeadAuthenticityEngine
from app.models.external_customer_profile import ExternalCustomerProfile
from app.models.external_lead import ExternalLead
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.schemas.external_intelligence_validation import ExternalLeadIntelligenceInput
from app.schemas.external_lead_intelligence import ExternalLeadIntelligenceProfile
from app.utils.exceptions import (
    ExternalIntelligenceNotFoundError,
    ExternalProfileNotFoundError,
    LeadNotFoundError,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

INTELLIGENCE_SOURCE_MODULE = "external_lead_intelligence"


class ExternalIntelligenceService:
    """Runs authenticity, income confidence, fraud screening, and KYC readiness engines."""

    def __init__(
        self,
        lead_repository: ExternalLeadRepository,
        profile_repository: ExternalProfileRepository,
        feature_store_repository: LeadFeatureStoreRepository,
        authenticity_engine: LeadAuthenticityEngine | None = None,
        income_engine: IncomeConfidenceEngine | None = None,
        fraud_engine: FraudScreeningEngine | None = None,
        kyc_engine: KycReadinessEngine | None = None,
    ) -> None:
        self._lead_repo = lead_repository
        self._profile_repo = profile_repository
        self._feature_repo = feature_store_repository
        self._authenticity_engine = authenticity_engine or LeadAuthenticityEngine()
        self._income_engine = income_engine or IncomeConfidenceEngine()
        self._fraud_engine = fraud_engine or FraudScreeningEngine()
        self._kyc_engine = kyc_engine or KycReadinessEngine()

    def compute_and_persist(self, lead_id: UUID, commit: bool = True) -> ExternalLeadIntelligenceProfile:
        lead = self._lead_repo.get_by_lead_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)

        profile = self._profile_repo.get_by_lead_id(lead_id)
        if profile is None:
            raise ExternalProfileNotFoundError(lead_id)

        data = self._build_input(lead, profile)
        intelligence = self._run_pipeline(data)
        self._persist(lead_id, lead, intelligence, commit=commit)

        logger.info(
            "External intelligence persisted lead_id=%s authenticity=%s fraud_risk=%s kyc=%s",
            lead_id,
            intelligence.lead_authenticity_score,
            intelligence.fraud_risk,
            intelligence.kyc_readiness,
        )
        return intelligence

    def build_all(self, limit: int | None = None) -> dict[str, int]:
        self._lead_repo._db.expire_all()
        fetch_limit = limit if limit is not None else 10000
        leads = self._lead_repo.get_all(limit=fetch_limit)
        succeeded = 0
        failed = 0

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def intelligence(lead) -> bool:
            try:
                profile = self._profile_repo.get_by_lead_id(lead.lead_id)
                if profile is None:
                    return False
                if getattr(profile, "lead_authenticity_score", None) is not None:
                    return True
                self.compute_and_persist(lead.lead_id, commit=False)
                return True
            except Exception as exc:
                logger.warning("External intelligence failed for lead_id=%s: %s", lead.lead_id, exc)
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(intelligence, l): l for l in leads}
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

    def get_intelligence(self, lead_id: UUID) -> ExternalLeadIntelligenceProfile:
        lead = self._lead_repo.get_by_lead_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)

        profile = self._profile_repo.get_by_lead_id(lead_id)
        if profile is None:
            raise ExternalProfileNotFoundError(lead_id)

        if profile.lead_authenticity_score is None or profile.last_validation_timestamp is None:
            raise ExternalIntelligenceNotFoundError(lead_id)

        return self._run_pipeline(self._build_input(lead, profile))

    def _build_input(self, lead: ExternalLead, profile: ExternalCustomerProfile) -> ExternalLeadIntelligenceInput:
        return ExternalLeadIntelligenceInput(
            lead_id=lead.lead_id,
            external_reference=lead.external_reference,
            full_name=lead.full_name,
            phone_number=lead.phone_number,
            email=lead.email,
            age=lead.age or 0,
            gender=lead.gender or "Unknown",
            occupation=lead.occupation or "Unknown",
            employer=lead.employer or "Unknown",
            estimated_income=lead.estimated_income or 0,
            credit_score=lead.credit_score or 0,
            city=lead.city or "Unknown",
            state=lead.state or "Unknown",
            referral_source=lead.referral_source or "Direct",
            campaign=lead.campaign or "General",
            consent=lead.consent,
            lead_created_date=lead.lead_created_date,
            income_segment=profile.income_segment,
            monthly_emi=profile.monthly_emi or 0,
            duplicate_phone=self._lead_repo.count_duplicates_by_phone(lead.phone_number, lead.lead_id) > 0,
            duplicate_email=self._lead_repo.count_duplicates_by_email(lead.email, lead.lead_id) > 0,
            duplicate_lead_reference=self._lead_repo.count_duplicates_by_reference(
                lead.external_reference, lead.lead_id
            )
            > 0,
        )

    def _run_pipeline(self, data: ExternalLeadIntelligenceInput) -> ExternalLeadIntelligenceProfile:
        authenticity = self._authenticity_engine.calculate(data)
        income = self._income_engine.calculate(data)
        fraud = self._fraud_engine.calculate(data)
        kyc = self._kyc_engine.calculate(data)

        all_reasons = (
            authenticity.reason_codes
            + income.reason_codes
            + kyc.reason_codes
        )

        return ExternalLeadIntelligenceProfile(
            lead_id=data.lead_id,
            lead_authenticity_score=authenticity.lead_authenticity_score,
            income_confidence_score=income.income_confidence_score,
            income_confidence_level=income.income_confidence_level,
            fraud_score=fraud.fraud_score,
            fraud_risk=fraud.fraud_risk,
            kyc_readiness=kyc.kyc_readiness,
            kyc_missing_items=kyc.kyc_missing_items,
            reason_codes=all_reasons,
            fraud_reason_codes=fraud.fraud_reason_codes,
            last_validation_timestamp=datetime.utcnow(),
            authenticity=authenticity,
            income_confidence=income,
            fraud_screening=fraud,
            kyc=kyc,
        )

    def _persist(
        self,
        lead_id: UUID,
        lead: ExternalLead,
        intelligence: ExternalLeadIntelligenceProfile,
        commit: bool = True,
    ) -> None:
        validated_at = intelligence.last_validation_timestamp
        self._profile_repo.apply_intelligence(
            lead_id,
            lead_authenticity_score=intelligence.lead_authenticity_score,
            income_confidence_score=intelligence.income_confidence_score,
            income_confidence_level=intelligence.income_confidence_level,
            fraud_score=intelligence.fraud_score,
            fraud_risk=intelligence.fraud_risk,
            fraud_reason_codes=json.dumps(intelligence.fraud_reason_codes),
            kyc_readiness=intelligence.kyc_readiness,
            kyc_missing_items=json.dumps(intelligence.kyc_missing_items),
            last_validation_timestamp=validated_at,
            commit=False,
        )

        features = {
            "lead_authenticity_score": intelligence.lead_authenticity_score,
            "income_confidence_score": intelligence.income_confidence_score,
            "fraud_score": intelligence.fraud_score,
            "kyc_readiness": intelligence.kyc_readiness,
        }
        self._feature_repo.upsert_features(
            lead_id,
            features,
            source_module=INTELLIGENCE_SOURCE_MODULE,
            commit=False,
        )

        lead.lead_status = "INTELLIGENCE_VALIDATED"
        lead.updated_at = datetime.utcnow()
        self._lead_repo._db.external_leads.replace_one(
            {"lead_id": str(lead_id)}, lead.to_doc(), upsert=True
        )
