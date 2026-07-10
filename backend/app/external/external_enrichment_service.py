"""Orchestrates lead enrichment and profile persistence."""

from datetime import datetime
from uuid import UUID

from app.external.excel_importer import ImportedLeadRow
from app.external.lead_enrichment import LeadEnrichmentEngine
from app.models.external_lead import ExternalLead
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.schemas.external_intelligence import (
    ExternalCustomerProfileResponse,
    ExternalLeadResponse,
)
from app.utils.exceptions import ExternalProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ExternalEnrichmentService:
    """Enriches external leads and persists external_customer_profile rows."""

    def __init__(
        self,
        lead_repository: ExternalLeadRepository,
        profile_repository: ExternalProfileRepository,
        enrichment_engine: LeadEnrichmentEngine | None = None,
    ) -> None:
        self._lead_repo = lead_repository
        self._profile_repo = profile_repository
        self._engine = enrichment_engine or LeadEnrichmentEngine()

    def enrich_all(self, limit: int | None = None) -> dict[str, int]:
        self._lead_repo._db.expire_all()
        fetch_limit = limit if limit is not None else 10000
        leads = self._lead_repo.get_all(limit=fetch_limit)
        enriched_count = 0
        failed = 0

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def enrich(lead) -> bool:
            if lead.lead_status == "ENRICHED":
                return True
            try:
                self._enrich_single(lead, commit=False)
                return True
            except Exception as exc:
                logger.warning("Enrichment failed for lead_id=%s: %s", lead.lead_id, exc)
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(enrich, l): l for l in leads}
            for fut in as_completed(futures):
                if fut.result():
                    enriched_count += 1
                else:
                    failed += 1

        if enriched_count > 0:
            self._lead_repo.commit()

        logger.info(
            "Batch enrichment complete: processed=%d enriched=%d failed=%d",
            len(leads),
            enriched_count,
            failed,
        )
        return {
            "leads_processed": len(leads),
            "leads_enriched": enriched_count,
            "leads_failed": failed,
        }

    def get_enriched_profile(self, lead_id: UUID) -> ExternalCustomerProfileResponse:
        lead = self._lead_repo.get_by_lead_id(lead_id)
        profile = self._profile_repo.get_by_lead_id(lead_id)
        if profile is None:
            raise ExternalProfileNotFoundError(lead_id)

        occupation_segment = None
        if lead and lead.occupation:
            occupation_segment = self._engine._occupation_segment(lead.occupation)

        return ExternalCustomerProfileResponse(
            profile_id=profile.profile_id,
            lead_id=profile.lead_id,
            income_segment=profile.income_segment,
            occupation_segment=occupation_segment,
            customer_persona=profile.customer_persona,
            relationship_potential=profile.relationship_potential,
            financial_stability=profile.financial_stability,
            digital_adoption=profile.digital_adoption,
            preferred_channel=profile.preferred_channel,
            preferred_contact_time=profile.preferred_contact_time,
            cross_sell_potential=profile.cross_sell_potential,
            lead_score=profile.lead_score,
            existing_bank=profile.existing_bank,
            existing_products=profile.existing_products,
            monthly_emi=profile.monthly_emi,
            home_owner=profile.home_owner,
            preferred_language=lead.preferred_language if lead else None,
            last_updated=profile.last_updated,
            lead=ExternalLeadResponse.model_validate(lead) if lead else None,
        )

    def _enrich_single(self, lead: ExternalLead, commit: bool = True) -> None:
        row = self._lead_to_imported_row(lead)
        enriched = self._engine.enrich(row)
        self._profile_repo.upsert_profile(lead.lead_id, enriched, commit=commit)
        lead.preferred_language = enriched.preferred_language
        lead.lead_status = "ENRICHED"
        lead.updated_at = datetime.utcnow()
        self._lead_repo._db.external_leads.replace_one(
            {"lead_id": str(lead.lead_id)}, lead.to_doc(), upsert=True
        )

    @staticmethod
    def _lead_to_imported_row(lead: ExternalLead) -> ImportedLeadRow:
        return ImportedLeadRow(
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
            lead_status=lead.lead_status,
            consent=lead.consent,
            lead_created_date=lead.lead_created_date or datetime.utcnow().date(),
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )
