"""Behaviour Analytics Summary service — aggregation and persistence only."""

from decimal import Decimal
from uuid import UUID

from app.behaviour_summary.external_aggregator import (
    ExternalBehaviourSummaryAggregator,
    ExternalSummaryInput,
)
from app.behaviour_summary.internal_aggregator import (
    InternalBehaviourSummaryAggregator,
    InternalSummaryInput,
)
from app.models.customer360_profile import Customer360Profile
from app.models.external_customer_profile import ExternalCustomerProfile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.feature_store_repository import (
    BEHAVIOUR_SUMMARY_SOURCE,
    FeatureStoreRepository,
)
from app.repositories.lead_feature_store_repository import (
    BEHAVIOUR_SUMMARY_SOURCE as LEAD_BEHAVIOUR_SUMMARY_SOURCE,
    LeadFeatureStoreRepository,
)
from app.schemas.behaviour_summary import BehaviourSummaryResponse
from app.utils.exceptions import (
    BehaviourSummaryNotFoundError,
    UnifiedProfileNotFoundError,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class BehaviourSummaryService:
    """
    Enterprise Behaviour Analytics Summary Layer.

    Standardizes outputs by aggregating pre-computed analytics — no duplicate business logic.
    """

    def __init__(
        self,
        customer360_repository: Customer360Repository,
        external_profile_repository: ExternalProfileRepository,
        feature_store_repository: FeatureStoreRepository,
        lead_feature_store_repository: LeadFeatureStoreRepository,
        external_lead_repository: ExternalLeadRepository,
        internal_aggregator: InternalBehaviourSummaryAggregator | None = None,
        external_aggregator: ExternalBehaviourSummaryAggregator | None = None,
    ) -> None:
        self._internal_repo = customer360_repository
        self._external_repo = external_profile_repository
        self._feature_repo = feature_store_repository
        self._lead_feature_repo = lead_feature_store_repository
        self._lead_repo = external_lead_repository
        self._internal_agg = internal_aggregator or InternalBehaviourSummaryAggregator()
        self._external_agg = external_aggregator or ExternalBehaviourSummaryAggregator()

    def build_summary(self, profile_id: UUID, commit: bool = True) -> BehaviourSummaryResponse:
        internal = self._internal_repo.get_profile_by_profile_id(profile_id)
        if internal is not None:
            summary = self._build_internal(internal)
            self._persist_internal(internal, summary, commit=commit)
            return summary

        external = self._external_repo.get_profile_by_profile_id(profile_id)
        if external is not None:
            summary = self._build_external(external)
            self._persist_external(external, summary, commit=commit)
            return summary

        raise UnifiedProfileNotFoundError(profile_id)

    def build_all(
        self, limit_internal: int | None = None, limit_external: int | None = None
    ) -> dict[str, int]:
        from datetime import datetime
        from app.models.feature_store import FeatureStoreEntry
        from app.models.lead_feature_store import LeadFeatureStoreEntry
        import collections
        from pymongo import UpdateOne, ReplaceOne
        from uuid import uuid4

        # 1. Load profiles
        internal_profiles = self._internal_repo.get_all_profiles()
        if limit_internal is not None:
            internal_profiles = internal_profiles[:limit_internal]
        external_profiles = self._external_repo.get_all_profiles()
        if limit_external is not None:
            external_profiles = external_profiles[:limit_external]

        # 2. Batch load feature store entries
        customer_ids = [str(p.customer_id) for p in internal_profiles]
        features_by_customer = collections.defaultdict(list)
        if customer_ids:
            for i in range(0, len(customer_ids), 500):
                batch_cids = customer_ids[i:i+500]
                docs = self._feature_repo._db.feature_store.find({"customer_id": {"$in": batch_cids}})
                for doc in docs:
                    if doc:
                        features_by_customer[doc["customer_id"]].append(FeatureStoreEntry.from_doc(doc))

        lead_ids = [str(p.lead_id) for p in external_profiles]
        features_by_lead = collections.defaultdict(list)
        leads_by_id = {}
        if lead_ids:
            for i in range(0, len(lead_ids), 500):
                batch_lids = lead_ids[i:i+500]
                docs = self._lead_feature_repo._db.lead_feature_store.find({"lead_id": {"$in": batch_lids}})
                for doc in docs:
                    if doc:
                        features_by_lead[doc["lead_id"]].append(LeadFeatureStoreEntry.from_doc(doc))
                
                lead_docs = self._lead_repo._db.external_leads.find({"lead_id": {"$in": batch_lids}})
                from app.models.external_lead import ExternalLead
                for doc in lead_docs:
                    if doc:
                        leads_by_id[doc["lead_id"]] = ExternalLead.from_doc(doc)

        internal_ok = 0
        external_ok = 0
        failed = 0

        profile_ops = []
        feature_ops = []

        # Process internal
        for profile in internal_profiles:
            try:
                entries = features_by_customer.get(str(profile.customer_id), [])
                features = self._feature_repo.features_to_dict(entries)
                upi_score = self._normalize_txn_count(features.get("upi_transaction_count"))
                net_score = self._normalize_txn_count(features.get("net_banking_transaction_count"))

                data = InternalSummaryInput(
                    customer_health_score=getattr(profile, "customer_health_score", None),
                    financial_stress_score=getattr(profile, "financial_stress_score", None),
                    monthly_income=getattr(profile, "monthly_income", None),
                    monthly_savings=getattr(profile, "monthly_savings", None),
                    cash_flow_score=getattr(profile, "cash_flow_score", None),
                    liquidity_score=getattr(profile, "liquidity_score", None),
                    debt_ratio=getattr(profile, "debt_ratio", None),
                    income_regularity_score=getattr(profile, "income_regularity_score", None),
                    emi_burden=getattr(profile, "emi_burden", None),
                    expense_stability_score=getattr(profile, "expense_stability_score", None),
                    digital_payment_ratio=getattr(profile, "digital_payment_ratio", None),
                    digital_adoption_score=getattr(profile, "digital_adoption_score", None),
                    voice_readiness_score=getattr(profile, "voice_readiness_score", None),
                    sms_readiness_score=getattr(profile, "sms_readiness_score", None),
                    whatsapp_readiness_score=getattr(profile, "whatsapp_readiness_score", None),
                    email_readiness_score=getattr(profile, "email_readiness_score", None),
                    upi_usage_score=upi_score,
                    net_banking_usage_score=net_score,
                )
                financial, repayment, digital = self._internal_agg.aggregate(data)
                
                now = datetime.utcnow()
                profile_ops.append(
                    UpdateOne(
                        {"profile_id": str(profile.profile_id)},
                        {
                            "$set": {
                                "financial_health_score": str(financial) if financial is not None else None,
                                "repayment_behaviour_score": str(repayment) if repayment is not None else None,
                                "digital_engagement_score": str(digital) if digital is not None else None,
                                "last_updated": now,
                            }
                        }
                    )
                )

                for k, v in [
                    ("financial_health_score", financial),
                    ("repayment_behaviour_score", repayment),
                    ("digital_engagement_score", digital)
                ]:
                    feature_ops.append(
                        ReplaceOne(
                            {"customer_id": str(profile.customer_id), "feature_name": k},
                            {
                                "feature_id": str(uuid4()),
                                "customer_id": str(profile.customer_id),
                                "feature_name": k,
                                "feature_value_numeric": str(v),
                                "feature_value_text": None,
                                "source_module": BEHAVIOUR_SUMMARY_SOURCE,
                                "last_updated": now,
                            },
                            upsert=True
                        )
                    )
                internal_ok += 1
            except Exception as exc:
                failed += 1
                logger.warning("Internal behaviour summary failed profile_id=%s: %s", profile.profile_id, exc)

        # Process external
        ext_profile_ops = []
        lead_feature_ops = []
        for profile in external_profiles:
            try:
                lead = leads_by_id.get(str(profile.lead_id))
                estimated_income = lead.estimated_income if lead else None

                entries = features_by_lead.get(str(profile.lead_id), [])
                features = self._lead_feature_repo.features_to_dict(entries)
                credit_quality = str(features.get("credit_quality", "")) or None

                data = ExternalSummaryInput(
                    financial_capacity_score=getattr(profile, "financial_capacity_score", None) or Decimal("0"),
                    lead_quality_score=getattr(profile, "lead_quality_score", None) or Decimal("0"),
                    income_confidence_score=getattr(profile, "income_confidence_score", None) or Decimal("0"),
                    estimated_repayment_capacity=getattr(profile, "estimated_repayment_capacity", None) or Decimal("0"),
                    estimated_income=estimated_income or Decimal("0"),
                    income_stability_score=getattr(profile, "income_confidence_score", None) or Decimal("0"),
                    credit_quality=credit_quality,
                    lead_authenticity_score=getattr(profile, "lead_authenticity_score", None) or Decimal("0"),
                    digital_readiness_score=getattr(profile, "digital_readiness_score", None) or Decimal("0"),
                    communication_readiness_score=getattr(profile, "communication_readiness_score", None) or Decimal("0"),
                    campaign_engagement_score=getattr(profile, "campaign_engagement_score", None) or Decimal("0"),
                    preferred_channel=getattr(profile, "preferred_channel", None) or "Unknown",
                )
                financial, repayment, digital = self._external_agg.aggregate(data)

                now = datetime.utcnow()
                ext_profile_ops.append(
                    UpdateOne(
                        {"profile_id": str(profile.profile_id)},
                        {
                            "$set": {
                                "financial_health_score": str(financial) if financial is not None else None,
                                "repayment_behaviour_score": str(repayment) if repayment is not None else None,
                                "digital_engagement_score": str(digital) if digital is not None else None,
                                "last_updated": now,
                            }
                        }
                    )
                )

                for k, v in [
                    ("financial_health_score", financial),
                    ("repayment_behaviour_score", repayment),
                    ("digital_engagement_score", digital)
                ]:
                    lead_feature_ops.append(
                        ReplaceOne(
                            {"lead_id": str(profile.lead_id), "feature_name": k},
                            {
                                "feature_id": str(uuid4()),
                                "lead_id": str(profile.lead_id),
                                "feature_name": k,
                                "feature_value_numeric": str(v),
                                "feature_value_text": None,
                                "source_module": LEAD_BEHAVIOUR_SUMMARY_SOURCE,
                                "last_updated": now,
                            },
                            upsert=True
                        )
                    )
                external_ok += 1
            except Exception as exc:
                failed += 1
                logger.warning("External behaviour summary failed profile_id=%s: %s", profile.profile_id, exc)

        def run_chunked_bulk_write(collection, ops):
            chunk_size = 500
            for i in range(0, len(ops), chunk_size):
                collection.bulk_write(ops[i : i + chunk_size])

        if profile_ops:
            run_chunked_bulk_write(self._internal_repo._db.customer_360_profile, profile_ops)
        if feature_ops:
            run_chunked_bulk_write(self._feature_repo._db.feature_store, feature_ops)
        if ext_profile_ops:
            run_chunked_bulk_write(self._external_repo._db.external_customer_profile, ext_profile_ops)
        if lead_feature_ops:
            run_chunked_bulk_write(self._lead_feature_repo._db.lead_feature_store, lead_feature_ops)

        return {
            "profiles_processed": len(internal_profiles) + len(external_profiles),
            "internal_succeeded": internal_ok,
            "external_succeeded": external_ok,
            "profiles_failed": failed,
        }

    def get_summary(self, profile_id: UUID) -> BehaviourSummaryResponse:
        internal = self._internal_repo.get_profile_by_profile_id(profile_id)
        if internal is not None:
            if internal.financial_health_score is None:
                raise BehaviourSummaryNotFoundError(profile_id)
            return BehaviourSummaryResponse(
                profile_id=profile_id,
                profile_type="Internal",
                entity_id=internal.customer_id,
                financial_health_score=internal.financial_health_score,
                repayment_behaviour_score=internal.repayment_behaviour_score or Decimal("0"),
                digital_engagement_score=internal.digital_engagement_score or Decimal("0"),
            )

        external = self._external_repo.get_profile_by_profile_id(profile_id)
        if external is not None:
            if external.financial_health_score is None:
                raise BehaviourSummaryNotFoundError(profile_id)
            return BehaviourSummaryResponse(
                profile_id=profile_id,
                profile_type="External",
                entity_id=external.lead_id,
                financial_health_score=external.financial_health_score,
                repayment_behaviour_score=external.repayment_behaviour_score or Decimal("0"),
                digital_engagement_score=external.digital_engagement_score or Decimal("0"),
            )

        raise UnifiedProfileNotFoundError(profile_id)

    def _build_internal(self, profile: Customer360Profile) -> BehaviourSummaryResponse:
        features = self._feature_repo.features_to_dict(
            self._feature_repo.get_all_features_by_customer(profile.customer_id)
        )
        upi_score = self._normalize_txn_count(features.get("upi_transaction_count"))
        net_score = self._normalize_txn_count(features.get("net_banking_transaction_count"))

        data = InternalSummaryInput(
            customer_health_score=getattr(profile, "customer_health_score", None),
            financial_stress_score=getattr(profile, "financial_stress_score", None),
            monthly_income=getattr(profile, "monthly_income", None),
            monthly_savings=getattr(profile, "monthly_savings", None),
            cash_flow_score=getattr(profile, "cash_flow_score", None),
            liquidity_score=getattr(profile, "liquidity_score", None),
            debt_ratio=getattr(profile, "debt_ratio", None),
            income_regularity_score=getattr(profile, "income_regularity_score", None),
            emi_burden=getattr(profile, "emi_burden", None),
            expense_stability_score=getattr(profile, "expense_stability_score", None),
            digital_payment_ratio=getattr(profile, "digital_payment_ratio", None),
            digital_adoption_score=getattr(profile, "digital_adoption_score", None),
            voice_readiness_score=getattr(profile, "voice_readiness_score", None),
            sms_readiness_score=getattr(profile, "sms_readiness_score", None),
            whatsapp_readiness_score=getattr(profile, "whatsapp_readiness_score", None),
            email_readiness_score=getattr(profile, "email_readiness_score", None),
            upi_usage_score=upi_score,
            net_banking_usage_score=net_score,
        )
        financial, repayment, digital = self._internal_agg.aggregate(data)
        return BehaviourSummaryResponse(
            profile_id=profile.profile_id,
            profile_type="Internal",
            entity_id=profile.customer_id,
            financial_health_score=financial,
            repayment_behaviour_score=repayment,
            digital_engagement_score=digital,
        )

    def _build_external(self, profile: ExternalCustomerProfile) -> BehaviourSummaryResponse:
        lead = self._lead_repo.get_by_lead_id(profile.lead_id)
        estimated_income = lead.estimated_income if lead else None

        features = self._lead_feature_repo.features_to_dict(
            self._lead_feature_repo.get_all_features_by_lead(profile.lead_id)
        )
        credit_quality = str(features.get("credit_quality", "")) or None

        data = ExternalSummaryInput(
            financial_capacity_score=getattr(profile, "financial_capacity_score", None) or Decimal("0"),
            lead_quality_score=getattr(profile, "lead_quality_score", None) or Decimal("0"),
            income_confidence_score=getattr(profile, "income_confidence_score", None) or Decimal("0"),
            estimated_repayment_capacity=getattr(profile, "estimated_repayment_capacity", None) or Decimal("0"),
            estimated_income=estimated_income or Decimal("0"),
            income_stability_score=getattr(profile, "income_confidence_score", None) or Decimal("0"),
            credit_quality=credit_quality,
            lead_authenticity_score=getattr(profile, "lead_authenticity_score", None) or Decimal("0"),
            digital_readiness_score=getattr(profile, "digital_readiness_score", None) or Decimal("0"),
            communication_readiness_score=getattr(profile, "communication_readiness_score", None) or Decimal("0"),
            campaign_engagement_score=getattr(profile, "campaign_engagement_score", None) or Decimal("0"),
            preferred_channel=getattr(profile, "preferred_channel", None) or "Unknown",
        )
        financial, repayment, digital = self._external_agg.aggregate(data)
        return BehaviourSummaryResponse(
            profile_id=profile.profile_id,
            profile_type="External",
            entity_id=profile.lead_id,
            financial_health_score=financial,
            repayment_behaviour_score=repayment,
            digital_engagement_score=digital,
        )

    def _persist_internal(
        self,
        profile: Customer360Profile,
        summary: BehaviourSummaryResponse,
        commit: bool,
    ) -> None:
        self._internal_repo.apply_behaviour_summary(
            profile.profile_id,
            financial_health_score=summary.financial_health_score,
            repayment_behaviour_score=summary.repayment_behaviour_score,
            digital_engagement_score=summary.digital_engagement_score,
            commit=False,
        )
        self._feature_repo.upsert_features(
            profile.customer_id,
            {
                "financial_health_score": summary.financial_health_score,
                "repayment_behaviour_score": summary.repayment_behaviour_score,
                "digital_engagement_score": summary.digital_engagement_score,
            },
            source_module=BEHAVIOUR_SUMMARY_SOURCE,
            commit=False,
        )
        if commit:
            self._internal_repo._db.commit()

    def _persist_external(
        self,
        profile: ExternalCustomerProfile,
        summary: BehaviourSummaryResponse,
        commit: bool,
    ) -> None:
        self._external_repo.apply_behaviour_summary(
            profile.profile_id,
            financial_health_score=summary.financial_health_score,
            repayment_behaviour_score=summary.repayment_behaviour_score,
            digital_engagement_score=summary.digital_engagement_score,
            commit=False,
        )
        self._lead_feature_repo.upsert_features(
            profile.lead_id,
            {
                "financial_health_score": summary.financial_health_score,
                "repayment_behaviour_score": summary.repayment_behaviour_score,
                "digital_engagement_score": summary.digital_engagement_score,
            },
            source_module=LEAD_BEHAVIOUR_SUMMARY_SOURCE,
            commit=False,
        )
        if commit:
            self._external_repo._db.commit()

    @staticmethod
    def _normalize_txn_count(raw: Decimal | str | None) -> Decimal | None:
        if raw is None:
            return None
        count = Decimal(str(raw))
        return min(Decimal("100"), count / Decimal("12") * Decimal("5"))
