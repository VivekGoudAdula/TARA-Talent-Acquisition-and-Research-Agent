"""Orchestration for Product Recommendation Engine."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.ml.product_recommendation.catalog import get_product_catalog
from app.ml.product_recommendation.customer_context import CustomerContext
from app.ml.product_recommendation.eligibility import EligibilityEngine
from app.ml.product_recommendation.ranking import ProductRankingEngine
from app.ml.repayment.service import RepaymentCapacityService
from app.models.customer360_profile import Customer360Profile
from app.models.external_customer_profile import ExternalCustomerProfile
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.repositories.ml_scoring_repository import MLScoringRepository
from app.schemas.product_recommendation import (
    ProductCatalogItem,
    ProductCatalogResponse,
    ProductRecommendationItem,
    ProductRecommendRequest,
    ProductRecommendResponse,
)
from app.utils.exceptions import RepaymentModelNotFoundError, UnifiedProfileNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ProductRecommendationService:
    """
    Enterprise Product Recommendation Engine (Model 2).

    Consumes Customer360 / External profiles and Repayment Capacity predictions.
    Does not retrain repayment models.
    """

    def __init__(
        self,
        customer360_repository: Customer360Repository,
        external_profile_repository: ExternalProfileRepository,
        external_lead_repository: ExternalLeadRepository,
        feature_store_repository: FeatureStoreRepository,
        lead_feature_store_repository: LeadFeatureStoreRepository,
        repayment_service: RepaymentCapacityService,
        eligibility_engine: EligibilityEngine | None = None,
        ranking_engine: ProductRankingEngine | None = None,
        scoring_repository: MLScoringRepository | None = None,
    ) -> None:
        self._internal_repo = customer360_repository
        self._external_repo = external_profile_repository
        self._lead_repo = external_lead_repository
        self._feature_repo = feature_store_repository
        self._lead_feature_repo = lead_feature_store_repository
        self._repayment_service = repayment_service
        self._eligibility = eligibility_engine or EligibilityEngine()
        self._ranking = ranking_engine or ProductRankingEngine()
        self._scoring_repo = scoring_repository

    def get_catalog(self) -> ProductCatalogResponse:
        products = [
            ProductCatalogItem(
                name=p.name,
                description=p.description,
                min_monthly_income=p.min_monthly_income,
                min_credit_score=p.min_credit_score,
                max_emi_ratio=p.max_emi_ratio,
                min_age=p.min_age,
                max_age=p.max_age,
                target_personas=list(p.target_personas),
                relationship_preference=p.relationship_preference,
            )
            for p in get_product_catalog()
        ]
        return ProductCatalogResponse(products=products, total_products=len(products))

    def recommend(self, request: ProductRecommendRequest) -> ProductRecommendResponse:
        customer = self._build_customer_context(request.profile_id)
        self._persist_repayment_from_context(request.profile_id, customer)
        eligibility_results = self._eligibility.evaluate_all(customer)
        ranked = self._ranking.rank(
            customer,
            eligibility_results,
            top_n=request.top_n,
        )

        recommendations = [
            ProductRecommendationItem(
                product_name=item.product_name,
                confidence_score=item.confidence_score,
                eligible=item.eligible,
                probability=item.probability,
                eligibility_reasons=item.eligibility_reasons,
            )
            for item in ranked
        ]

        top = recommendations[0] if recommendations else None
        logger.info(
            "Product recommendation profile_id=%s top=%s eligible=%s",
            request.profile_id,
            top.product_name if top else None,
            top.eligible if top else None,
        )

        response = ProductRecommendResponse(
            profile_id=request.profile_id,
            profile_type=customer.profile_type,
            repayment_capacity=customer.repayment_capacity or "Unknown",
            repayment_confidence=customer.repayment_confidence,
            top_recommendation=top.product_name if top else None,
            recommendations=recommendations,
        )

        if self._scoring_repo:
            entity_id: UUID | None = None
            internal = self._internal_repo.get_profile_by_profile_id(request.profile_id)
            if internal is not None:
                entity_id = internal.customer_id
            else:
                external = self._external_repo.get_profile_by_profile_id(request.profile_id)
                if external is not None:
                    entity_id = external.lead_id
            if entity_id is not None:
                rec_docs = [
                    {
                        "product_name": item.product_name,
                        "confidence_score": item.confidence_score,
                        "eligible": item.eligible,
                        "probability": item.probability,
                        "eligibility_reasons": item.eligibility_reasons,
                    }
                    for item in response.recommendations
                ]
                self._scoring_repo.upsert_product_recommendation(
                    profile_id=request.profile_id,
                    profile_type=response.profile_type,
                    entity_id=entity_id,
                    repayment_capacity=response.repayment_capacity,
                    repayment_confidence=response.repayment_confidence,
                    top_recommendation=response.top_recommendation,
                    recommendations=rec_docs,
                )

        return response

    def _persist_repayment_from_context(self, profile_id: UUID, customer: CustomerContext) -> None:
        if not self._scoring_repo or not customer.repayment_capacity:
            return
        entity_id: UUID | None = None
        internal = self._internal_repo.get_profile_by_profile_id(profile_id)
        if internal is not None:
            entity_id = internal.customer_id
        else:
            external = self._external_repo.get_profile_by_profile_id(profile_id)
            if external is not None:
                entity_id = external.lead_id
        if entity_id is None:
            return
        self._scoring_repo.upsert_repayment_prediction(
            profile_id=profile_id,
            profile_type=customer.profile_type,
            entity_id=entity_id,
            repayment_capacity=customer.repayment_capacity,
            confidence=customer.repayment_confidence,
            probabilities=customer.repayment_probabilities or {},
            model_used="repayment_capacity",
        )

    def _build_customer_context(self, profile_id: UUID) -> CustomerContext:
        internal = self._internal_repo.get_profile_by_profile_id(profile_id)
        if internal is not None:
            return self._context_from_internal(internal)

        external = self._external_repo.get_profile_by_profile_id(profile_id)
        if external is not None:
            return self._context_from_external(external)

        raise UnifiedProfileNotFoundError(profile_id)

    @staticmethod
    def _attr(obj, name: str, default=None):
        return getattr(obj, name, default) if obj is not None else default

    def _context_from_internal(self, profile: Customer360Profile) -> CustomerContext:
        features = self._feature_repo.features_to_dict(
            self._feature_repo.get_all_features_by_customer(profile.customer_id)
        )
        repayment_features = self._internal_repayment_features(profile, features)
        repayment = self._predict_repayment(repayment_features)

        monthly_income = self._attr(profile, "monthly_income")
        credit_score = self._feature_int(features, "credit_score")
        occupation = self._attr(profile, "occupation")
        persona = (
            self._attr(profile, "customer_segment")
            or self._attr(profile, "income_segment")
            or occupation
            or "General"
        )
        engagement = self._attr(profile, "engagement_score")
        estimated_value = self._attr(profile, "estimated_customer_value")

        return CustomerContext(
            profile_id=profile.profile_id,
            profile_type="Internal",
            is_existing_customer=True,
            age=self._attr(profile, "age"),
            monthly_income=monthly_income,
            credit_score=credit_score,
            emi_ratio=self._attr(profile, "emi_burden"),
            persona=persona,
            occupation=occupation,
            city=self._attr(profile, "city"),
            relationship_score=self._attr(profile, "relationship_strength_score"),
            financial_health_score=self._attr(profile, "financial_health_score")
            or self._attr(profile, "customer_health_score")
            or self._attr(profile, "cash_flow_score"),
            financial_capacity_score=None,
            customer_value_score=engagement or estimated_value,
            repayment_capacity=repayment.repayment_capacity,
            repayment_confidence=repayment.confidence,
            repayment_probabilities=repayment.probabilities,
        )

    def _context_from_external(self, profile: ExternalCustomerProfile) -> CustomerContext:
        lead = self._lead_repo.get_by_lead_id(profile.lead_id)
        features = self._lead_feature_repo.features_to_dict(
            self._lead_feature_repo.get_all_features_by_lead(profile.lead_id)
        )
        repayment_features = self._external_repayment_features(profile, lead, features)
        repayment = self._predict_repayment(repayment_features)

        monthly_income = None
        if lead and lead.estimated_income:
            monthly_income = lead.estimated_income / Decimal("12")

        emi_ratio = None
        monthly_emi = self._attr(profile, "monthly_emi")
        if monthly_emi and monthly_income and monthly_income > 0:
            emi_ratio = (monthly_emi / monthly_income) * Decimal("100")

        return CustomerContext(
            profile_id=profile.profile_id,
            profile_type="External",
            is_existing_customer=False,
            age=lead.age if lead else None,
            monthly_income=monthly_income,
            credit_score=lead.credit_score if lead else None,
            emi_ratio=emi_ratio,
            persona=self._attr(profile, "customer_persona"),
            occupation=lead.occupation if lead else None,
            city=lead.city if lead else None,
            relationship_score=self._attr(profile, "relationship_potential"),
            financial_health_score=self._attr(profile, "financial_health_score"),
            financial_capacity_score=self._attr(profile, "financial_capacity_score"),
            customer_value_score=self._attr(profile, "cross_sell_potential"),
            repayment_capacity=repayment.repayment_capacity,
            repayment_confidence=repayment.confidence,
            repayment_probabilities=repayment.probabilities,
        )

    def _predict_repayment(self, features: dict):
        try:
            return self._repayment_service.predict(features=features)
        except RepaymentModelNotFoundError:
            from app.ml.repayment.fallback import rule_based_repayment_predict

            return rule_based_repayment_predict(features)

    @staticmethod
    def _internal_repayment_features(
        profile: Customer360Profile,
        features: dict,
    ) -> dict:
        def _a(name):
            return ProductRecommendationService._attr(profile, name)

        income = _a("monthly_income")
        customer_value = _a("engagement_score")
        estimated_value = _a("estimated_customer_value")
        if customer_value is None and estimated_value is not None:
            customer_value = min(
                Decimal("100"),
                (estimated_value / Decimal("50000")) * Decimal("10"),
            )
        monthly_income = _a("monthly_income")
        monthly_savings = _a("monthly_savings")
        savings_ratio = None
        if monthly_income and monthly_income > 0 and monthly_savings:
            savings_ratio = float((monthly_savings / monthly_income) * Decimal("100"))

        def _f(name):
            val = _a(name)
            return float(val) if val is not None else None

        return {
            "profile_type": "Internal",
            "age": _a("age"),
            "income": float(income) if income is not None else None,
            "credit_score": ProductRecommendationService._feature_int(features, "credit_score"),
            "financial_health_score": _f("financial_health_score") or _f("customer_health_score"),
            "repayment_behaviour_score": _f("repayment_behaviour_score"),
            "digital_engagement_score": _f("digital_engagement_score"),
            "financial_capacity_score": None,
            "lead_score": None,
            "lead_quality_score": None,
            "lead_authenticity_score": None,
            "income_confidence_score": None,
            "relationship_score": _f("relationship_strength_score"),
            "savings_ratio": savings_ratio,
            "emi_burden": _f("emi_burden"),
            "cash_flow_score": _f("cash_flow_score"),
            "digital_adoption_score": _f("digital_adoption_score"),
            "customer_value_score": float(customer_value) if customer_value is not None else None,
            "occupation": _a("occupation"),
            "employment_type": None,
            "city": _a("city"),
        }

    @staticmethod
    def _external_repayment_features(profile, lead, features: dict) -> dict:
        income = None
        if lead and lead.estimated_income:
            income = float(lead.estimated_income / Decimal("12"))

        emi_burden = None
        monthly_emi = ProductRecommendationService._attr(profile, "monthly_emi")
        if monthly_emi and income and income > 0:
            emi_burden = float((monthly_emi / Decimal(str(income))) * Decimal("100"))

        def _f(name):
            val = ProductRecommendationService._attr(profile, name)
            return float(val) if val is not None else None

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
            "savings_ratio": ProductRecommendationService._feature_float(features, "savings_ratio"),
            "emi_burden": emi_burden,
            "cash_flow_score": _f("financial_stability"),
            "digital_adoption_score": _f("digital_adoption") or _f("digital_readiness_score"),
            "customer_value_score": _f("cross_sell_potential"),
            "occupation": lead.occupation if lead else None,
            "employment_type": lead.employer if lead else None,
            "city": lead.city if lead else None,
        }

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
    def _feature_float(features: dict, name: str) -> float | None:
        value = features.get(name)
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None
