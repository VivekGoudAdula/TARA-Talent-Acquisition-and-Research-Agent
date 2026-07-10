"""Decision summary assembly from ML models and profile data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.explainability.reason_engine import ReasonCodeEngine, ReasonCodeInput
from app.ml.conversion.service import ConversionService
from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
from app.ml.repayment.service import RepaymentCapacityService
from app.models.customer360_profile import Customer360Profile
from app.models.external_customer_profile import ExternalCustomerProfile
from app.models.external_lead import ExternalLead
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.schemas.conversion import ConversionPredictResponse
from app.schemas.product_recommendation import ProductRecommendResponse
from app.schemas.repayment import RepaymentPredictResponse
from app.utils.exceptions import RepaymentModelNotFoundError, UnifiedProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DecisionSummary:
    """Unified structured input for the Explainable AI layer."""

    customer_name: str
    profile_id: UUID
    customer_id: UUID
    profile_type: str
    repayment_capacity: str
    repayment_confidence: float
    recommended_product: str | None
    product_confidence: float | None
    conversion_probability: float | None
    lead_priority: str | None
    marketing_priority: str | None
    financial_health_score: float | None
    repayment_behaviour_score: float | None
    digital_engagement_score: float | None
    credit_score: int | None
    income: float | None
    emi_burden: float | None
    savings_ratio: float | None
    consent: bool | None
    top_reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionSummaryBuilder:
    """
    Collects ML model outputs and profile features into one Decision Summary.

    Does not alter any ML predictions — only reads existing API/service outputs.
    """

    def __init__(
        self,
        customer360_repository: Customer360Repository,
        external_profile_repository: ExternalProfileRepository,
        external_lead_repository: ExternalLeadRepository,
        feature_store_repository: FeatureStoreRepository,
        lead_feature_store_repository: LeadFeatureStoreRepository,
        repayment_service: RepaymentCapacityService,
        product_recommendation_service: ProductRecommendationService,
        conversion_service: ConversionService,
        reason_engine: ReasonCodeEngine | None = None,
    ) -> None:
        self._internal_repo = customer360_repository
        self._external_repo = external_profile_repository
        self._lead_repo = external_lead_repository
        self._feature_repo = feature_store_repository
        self._lead_feature_repo = lead_feature_store_repository
        self._repayment_service = repayment_service
        self._product_service = product_recommendation_service
        self._conversion_service = conversion_service
        self._reason_engine = reason_engine or ReasonCodeEngine()

    def build_by_profile_id(self, profile_id: UUID) -> DecisionSummary:
        internal = self._internal_repo.get_profile_by_profile_id(profile_id)
        if internal is not None:
            return self._build_internal(internal)

        external = self._external_repo.get_profile_by_profile_id(profile_id)
        if external is not None:
            return self._build_external(external)

        raise UnifiedProfileNotFoundError(profile_id)

    def build_by_customer_id(self, customer_id: UUID) -> DecisionSummary:
        internal = self._internal_repo.get_profile_by_customer_id(customer_id)
        if internal is not None:
            return self._build_internal(internal)

        lead = self._lead_repo.get_by_lead_id(customer_id)
        if lead is not None:
            profile = self._external_repo.get_by_lead_id(customer_id)
            if profile is None:
                raise UnifiedProfileNotFoundError(customer_id)
            return self._build_external(profile, lead)

        raise UnifiedProfileNotFoundError(customer_id)

    def _build_internal(self, profile: Customer360Profile) -> DecisionSummary:
        features = self._feature_repo.features_to_dict(
            self._feature_repo.get_all_features_by_customer(profile.customer_id)
        )
        repayment_features = self._internal_repayment_features(profile, features)
        repayment = self._predict_repayment_safe(repayment_features)
        products = self._product_service.recommend(
            self._product_request(profile.profile_id)
        )
        customer_name = self._resolve_internal_customer_name(profile)
        return self._assemble(
            customer_name=customer_name,
            profile=profile,
            customer_id=profile.customer_id,
            profile_type="Internal",
            repayment=repayment,
            products=products,
            conversion=None,
            credit_score=self._feature_int(features, "credit_score"),
            income=self._attr(profile, "monthly_income"),
            emi_burden=self._attr(profile, "emi_burden"),
            savings_ratio=self._savings_ratio(
                self._attr(profile, "monthly_income"),
                self._attr(profile, "monthly_savings"),
            ),
            consent=None,
            lead_quality=None,
        )

    def _build_external(
        self,
        profile: ExternalCustomerProfile,
        lead: ExternalLead | None = None,
    ) -> DecisionSummary:
        lead = lead or self._lead_repo.get_by_lead_id(profile.lead_id)
        feature_map = self._lead_feature_repo.features_to_dict(
            self._lead_feature_repo.get_all_features_by_lead(profile.lead_id)
        )
        repayment_features = self._external_repayment_features(profile, lead, feature_map)
        repayment = self._predict_repayment_safe(repayment_features)
        products = self._product_service.recommend(
            self._product_request(profile.profile_id)
        )
        conversion: ConversionPredictResponse | None = None
        try:
            conversion = self._conversion_service.predict(lead_id=profile.lead_id)
        except Exception as exc:
            logger.warning("Conversion prediction unavailable for lead_id=%s: %s", profile.lead_id, exc)

        monthly_income = None
        if lead and lead.estimated_income:
            monthly_income = lead.estimated_income / Decimal("12")

        emi_ratio = None
        monthly_emi = self._attr(profile, "monthly_emi")
        if monthly_emi and monthly_income and monthly_income > 0:
            emi_ratio = (monthly_emi / monthly_income) * Decimal("100")

        name = lead.full_name if lead else f"Lead {str(profile.lead_id)[:8]}"

        return self._assemble(
            customer_name=name,
            profile=profile,
            customer_id=profile.lead_id,
            profile_type="External",
            repayment=repayment,
            products=products,
            conversion=conversion,
            credit_score=lead.credit_score if lead else None,
            income=monthly_income,
            emi_burden=emi_ratio,
            savings_ratio=None,
            consent=lead.consent if lead else None,
            lead_quality=self._attr(profile, "lead_quality_score"),
        )

    def _assemble(
        self,
        *,
        customer_name: str,
        profile: Any,
        customer_id: UUID,
        profile_type: str,
        repayment: RepaymentPredictResponse,
        products: ProductRecommendResponse,
        conversion: ConversionPredictResponse | None,
        credit_score: int | None,
        income: Decimal | None,
        emi_burden: Decimal | None,
        savings_ratio: Decimal | None,
        consent: bool | None,
        lead_quality: Decimal | None,
    ) -> DecisionSummary:
        top_product = products.recommendations[0] if products.recommendations else None

        reason_input = ReasonCodeInput(
            monthly_income=float(income) if income is not None else None,
            emi_burden=float(emi_burden) if emi_burden is not None else None,
            credit_score=credit_score,
            financial_health_score=self._attr(profile, "financial_health_score"),
            digital_engagement_score=self._attr(profile, "digital_engagement_score"),
            savings_ratio=float(savings_ratio) if savings_ratio is not None else None,
            repayment_capacity=repayment.repayment_capacity,
            repayment_confidence=repayment.confidence,
            consent=consent,
            lead_quality_score=lead_quality,
        )
        reason_codes = self._reason_engine.generate(reason_input)

        return DecisionSummary(
            customer_name=customer_name,
            profile_id=profile.profile_id,
            customer_id=customer_id,
            profile_type=profile_type,
            repayment_capacity=repayment.repayment_capacity,
            repayment_confidence=round(repayment.confidence * 100, 1)
            if repayment.confidence <= 1.0
            else round(repayment.confidence, 1),
            recommended_product=top_product.product_name if top_product else products.top_recommendation,
            product_confidence=top_product.confidence_score if top_product else None,
            conversion_probability=conversion.conversion_probability if conversion else None,
            lead_priority=conversion.lead_priority if conversion else None,
            marketing_priority=conversion.marketing_priority if conversion else None,
            financial_health_score=self._to_float(self._attr(profile, "financial_health_score")),
            repayment_behaviour_score=self._to_float(self._attr(profile, "repayment_behaviour_score")),
            digital_engagement_score=self._to_float(self._attr(profile, "digital_engagement_score")),
            credit_score=credit_score,
            income=float(income) if income is not None else None,
            emi_burden=float(emi_burden) if emi_burden is not None else None,
            savings_ratio=float(savings_ratio) if savings_ratio is not None else None,
            consent=consent,
            top_reason_codes=reason_codes,
        )

    @staticmethod
    def _attr(obj: Any, name: str, default=None):
        return getattr(obj, name, default) if obj is not None else default

    def _predict_repayment_safe(self, features: dict) -> RepaymentPredictResponse:
        try:
            return self._repayment_service.predict(features=features)
        except RepaymentModelNotFoundError:
            from app.ml.repayment.fallback import rule_based_repayment_predict

            return rule_based_repayment_predict(features)

    def _resolve_internal_customer_name(self, profile: Customer360Profile) -> str:
        doc = self._internal_repo._db.customers.find_one(
            {"customer_id": str(profile.customer_id)},
            {"first_name": 1, "last_name": 1},
        )
        if doc:
            first = (doc.get("first_name") or "").strip()
            last = (doc.get("last_name") or "").strip()
            full = f"{first} {last}".strip()
            if full:
                return full
        return f"Customer {str(profile.customer_id)[:8]}"

    @staticmethod
    def _product_request(profile_id: UUID):
        from app.schemas.product_recommendation import ProductRecommendRequest

        return ProductRecommendRequest(profile_id=profile_id, top_n=5)

    @staticmethod
    def _savings_ratio(income: Decimal | None, savings: Decimal | None) -> Decimal | None:
        if income is None or income <= 0 or savings is None:
            return None
        return (savings / income) * Decimal("100")

    @staticmethod
    def _feature_int(features: dict, name: str) -> int | None:
        value = features.get(name)
        if value is None:
            return None
        try:
            return int(Decimal(str(value)))
        except Exception:
            return None

    @staticmethod
    def _to_float(value: Decimal | None) -> float | None:
        return float(value) if value is not None else None

    @staticmethod
    def _internal_repayment_features(profile: Customer360Profile, features: dict) -> dict:
        income = DecisionSummaryBuilder._attr(profile, "monthly_income")
        customer_value = DecisionSummaryBuilder._attr(profile, "engagement_score")
        estimated_value = DecisionSummaryBuilder._attr(profile, "estimated_customer_value")
        if customer_value is None and estimated_value is not None:
            customer_value = min(
                Decimal("100"),
                (estimated_value / Decimal("50000")) * Decimal("10"),
            )
        monthly_income = DecisionSummaryBuilder._attr(profile, "monthly_income")
        monthly_savings = DecisionSummaryBuilder._attr(profile, "monthly_savings")
        savings_ratio = None
        if monthly_income and monthly_income > 0 and monthly_savings:
            savings_ratio = float((monthly_savings / monthly_income) * Decimal("100"))
        return {
            "profile_type": "Internal",
            "age": DecisionSummaryBuilder._attr(profile, "age"),
            "income": float(income) if income is not None else None,
            "credit_score": DecisionSummaryBuilder._feature_int(features, "credit_score"),
            "financial_health_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "financial_health_score")
            ),
            "repayment_behaviour_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "repayment_behaviour_score")
            ),
            "digital_engagement_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "digital_engagement_score")
            ),
            "financial_capacity_score": None,
            "lead_score": None,
            "lead_quality_score": None,
            "lead_authenticity_score": None,
            "income_confidence_score": None,
            "relationship_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "relationship_strength_score")
            ),
            "savings_ratio": savings_ratio,
            "emi_burden": DecisionSummaryBuilder._to_float(DecisionSummaryBuilder._attr(profile, "emi_burden")),
            "cash_flow_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "cash_flow_score")
            ),
            "digital_adoption_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "digital_adoption_score")
            ),
            "customer_value_score": DecisionSummaryBuilder._to_float(customer_value),
            "occupation": DecisionSummaryBuilder._attr(profile, "occupation"),
            "employment_type": None,
            "city": DecisionSummaryBuilder._attr(profile, "city"),
        }

    @staticmethod
    def _external_repayment_features(profile, lead, features: dict) -> dict:
        income = None
        if lead and lead.estimated_income:
            income = float(lead.estimated_income / Decimal("12"))
        emi_burden = None
        monthly_emi = DecisionSummaryBuilder._attr(profile, "monthly_emi")
        if monthly_emi and income and income > 0:
            emi_burden = float((monthly_emi / Decimal(str(income))) * Decimal("100"))

        def _f(name: str):
            return DecisionSummaryBuilder._to_float(DecisionSummaryBuilder._attr(profile, name))

        return {
            "profile_type": "External",
            "age": lead.age if lead else None,
            "income": income,
            "credit_score": lead.credit_score if lead else None,
            "financial_health_score": _f("financial_health_score"),
            "repayment_behaviour_score": _f("repayment_behaviour_score"),
            "digital_engagement_score": _f("digital_engagement_score"),
            "financial_capacity_score": _f("financial_capacity_score"),
            "lead_score": _f("lead_score"),
            "lead_quality_score": _f("lead_quality_score"),
            "lead_authenticity_score": _f("lead_authenticity_score"),
            "income_confidence_score": _f("income_confidence_score"),
            "relationship_score": _f("relationship_potential"),
            "savings_ratio": DecisionSummaryBuilder._feature_float(features, "savings_ratio"),
            "emi_burden": emi_burden,
            "cash_flow_score": _f("financial_stability"),
            "digital_adoption_score": DecisionSummaryBuilder._to_float(
                DecisionSummaryBuilder._attr(profile, "digital_adoption")
                or DecisionSummaryBuilder._attr(profile, "digital_readiness_score")
            ),
            "customer_value_score": _f("cross_sell_potential"),
            "occupation": lead.occupation if lead else None,
            "employment_type": lead.employer if lead else None,
            "city": lead.city if lead else None,
        }

    @staticmethod
    def _feature_float(features: dict, name: str) -> float | None:
        value = features.get(name)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
