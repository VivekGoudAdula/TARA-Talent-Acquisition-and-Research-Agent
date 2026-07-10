"""Hybrid ML product ranking engine."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.ml.product_recommendation.catalog import LendingProduct, PRODUCT_CATALOG
from app.ml.product_recommendation.customer_context import CustomerContext
from app.ml.product_recommendation.eligibility import EligibilityResult

REPAYMENT_CAPACITY_WEIGHT = {
    "Very High": 1.0,
    "High": 0.78,
    "Medium": 0.52,
    "Low": 0.2,
}

PRODUCT_AFFINITY_WEIGHTS: dict[str, dict[str, float]] = {
    "Personal Loan": {
        "income": 0.15,
        "credit": 0.2,
        "repayment": 0.3,
        "emi_headroom": 0.15,
        "persona": 0.1,
        "relationship": 0.05,
        "financial_health": 0.05,
    },
    "Home Loan": {
        "income": 0.25,
        "credit": 0.2,
        "repayment": 0.25,
        "emi_headroom": 0.15,
        "persona": 0.05,
        "relationship": 0.05,
        "financial_health": 0.05,
    },
    "Auto Loan": {
        "income": 0.18,
        "credit": 0.18,
        "repayment": 0.25,
        "emi_headroom": 0.15,
        "persona": 0.12,
        "relationship": 0.05,
        "financial_health": 0.07,
    },
    "Mortgage Loan": {
        "income": 0.28,
        "credit": 0.22,
        "repayment": 0.22,
        "emi_headroom": 0.12,
        "persona": 0.05,
        "relationship": 0.06,
        "financial_health": 0.05,
    },
    "Education Loan": {
        "income": 0.1,
        "credit": 0.15,
        "repayment": 0.25,
        "emi_headroom": 0.15,
        "persona": 0.2,
        "relationship": 0.05,
        "financial_health": 0.1,
    },
}


@dataclass(frozen=True)
class RankedProduct:
    """A product with hybrid rule + ML ranking scores."""

    product_name: str
    eligible: bool
    probability: float
    confidence_score: float
    eligibility_reasons: list[str]
    rule_score: float
    ml_score: float


class ProductRankingEngine:
    """
    Ranks lending products using a hybrid scorer.

    Combines business-rule eligibility with a weighted logistic-style ML ranker
    that consumes repayment capacity model output and profile features.
    """

    RULE_WEIGHT = 0.35
    ML_WEIGHT = 0.65

    def rank(
        self,
        customer: CustomerContext,
        eligibility_results: list[EligibilityResult],
        top_n: int = 5,
    ) -> list[RankedProduct]:
        product_map = {p.name: p for p in PRODUCT_CATALOG}
        eligibility_map = {e.product_name: e for e in eligibility_results}

        ranked: list[RankedProduct] = []
        for product in PRODUCT_CATALOG:
            eligibility = eligibility_map[product.name]
            ml_score = self._ml_score(customer, product)
            combined = (
                self.RULE_WEIGHT * eligibility.rule_score + self.ML_WEIGHT * ml_score
            )
            if not eligibility.eligible:
                combined *= 0.35

            probability = self._to_percentage(combined)
            confidence = self._confidence(customer, eligibility, ml_score)

            ranked.append(
                RankedProduct(
                    product_name=product.name,
                    eligible=eligibility.eligible,
                    probability=probability,
                    confidence_score=confidence,
                    eligibility_reasons=eligibility.reasons,
                    rule_score=eligibility.rule_score,
                    ml_score=ml_score,
                )
            )

        ranked.sort(key=lambda r: (r.eligible, r.probability, r.ml_score), reverse=True)
        return ranked[:top_n]

    def _ml_score(self, customer: CustomerContext, product: LendingProduct) -> float:
        weights = PRODUCT_AFFINITY_WEIGHTS[product.name]
        features = {
            "income": self._norm_income(customer.monthly_income, product.min_monthly_income),
            "credit": self._norm_credit(customer.credit_score, product.min_credit_score),
            "repayment": self._repayment_score(customer),
            "emi_headroom": self._emi_headroom(customer.emi_ratio, product.max_emi_ratio),
            "persona": self._persona_score(customer.persona, product.target_personas),
            "relationship": self._relationship_score(customer),
            "financial_health": self._norm_score(customer.financial_health_score),
        }
        linear = sum(weights[key] * features[key] for key in weights)
        return self._sigmoid(4.0 * (linear - 0.45))

    def _repayment_score(self, customer: CustomerContext) -> float:
        base = REPAYMENT_CAPACITY_WEIGHT.get(customer.repayment_capacity or "Low", 0.2)
        if customer.repayment_probabilities:
            weighted = sum(
                REPAYMENT_CAPACITY_WEIGHT.get(label, 0.2) * prob
                for label, prob in customer.repayment_probabilities.items()
            )
            return 0.5 * base + 0.5 * weighted
        return base * customer.repayment_confidence

    @staticmethod
    def _norm_income(income, minimum) -> float:
        if income is None or minimum is None or minimum <= 0:
            return 0.3
        ratio = float(income / minimum)
        return min(1.0, max(0.0, (ratio - 0.8) / 1.5))

    @staticmethod
    def _norm_credit(score: int | None, minimum: int) -> float:
        if score is None:
            return 0.3
        return min(1.0, max(0.0, (score - minimum + 80) / 120))

    @staticmethod
    def _emi_headroom(emi_ratio, max_ratio) -> float:
        if emi_ratio is None:
            return 0.6
        headroom = float(max_ratio - emi_ratio)
        return min(1.0, max(0.0, headroom / float(max_ratio)))

    @staticmethod
    def _persona_score(persona: str | None, targets: tuple[str, ...]) -> float:
        if persona is None:
            return 0.5
        persona_lower = persona.lower()
        if any(t.lower() in persona_lower or persona_lower in t.lower() for t in targets):
            return 1.0
        return 0.25

    @staticmethod
    def _relationship_score(customer: CustomerContext) -> float:
        if customer.is_existing_customer:
            return 1.0
        if customer.relationship_score is not None:
            return min(1.0, float(customer.relationship_score) / 100.0)
        return 0.4

    @staticmethod
    def _norm_score(score) -> float:
        if score is None:
            return 0.5
        return min(1.0, max(0.0, float(score) / 100.0))

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _to_percentage(score: float) -> float:
        return round(min(99.0, max(1.0, score * 100)), 1)

    def _confidence(
        self,
        customer: CustomerContext,
        eligibility: EligibilityResult,
        ml_score: float,
    ) -> float:
        data_completeness = sum(
            1
            for v in (
                customer.age,
                customer.monthly_income,
                customer.credit_score,
                customer.repayment_capacity,
            )
            if v is not None
        ) / 4.0
        base = 0.4 * eligibility.rule_score + 0.4 * ml_score + 0.2 * data_completeness
        base *= customer.repayment_confidence
        if eligibility.eligible:
            base = min(0.99, base + 0.1)
        return round(min(99.0, max(1.0, base * 100)), 1)
