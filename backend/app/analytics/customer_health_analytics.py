"""
Customer Health & Risk Analytics Engine — CRM-oriented health and business risk.

NOT a credit approval, fraud, or AML engine. Deterministic rules only.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate
from app.schemas.customer_health_analytics import CustomerHealthProfile
from app.schemas.customer_health_input import CustomerHealthAnalyticsInput
from app.schemas.digital_channel_analytics import DigitalChannelProfile
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SCORE = Decimal("0.01")


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value)).quantize(SCORE, ROUND_HALF_UP)


class CustomerHealthAnalyzer:
    """Composite customer health score (0–100, higher = healthier)."""

    def analyze(
        self,
        relationship: RelationshipProfile,
        digital: DigitalChannelProfile,
        financial: FinancialProfile,
        transaction: TransactionAnalyticsProfile,
        aggregate: CustomerAggregate,
    ) -> Decimal:
        active_products = sum(1 for p in aggregate.products if p.status == "Active")
        product_usage = min(Decimal("100"), Decimal(active_products) / Decimal("8") * Decimal("100"))
        balance_score = min(Decimal("100"), financial.average_balance / Decimal("500000") * Decimal("100"))
        savings_score = min(Decimal("100"), financial.savings_ratio * Decimal("2"))
        txn_score = min(Decimal("100"), transaction.monthly_transaction_count)

        health = (
            relationship.relationship_strength_score * Decimal("0.20")
            + digital.engagement_score * Decimal("0.15")
            + balance_score * Decimal("0.15")
            + savings_score * Decimal("0.15")
            + txn_score * Decimal("0.15")
            + product_usage * Decimal("0.10")
            + relationship.loyalty_score * Decimal("0.10")
        )
        return _clamp(health)


class FinancialStressAnalyzer:
    """Financial stress score (0–100, higher = more stress)."""

    def analyze(self, financial: FinancialProfile, transaction: TransactionAnalyticsProfile) -> Decimal:
        income_instability = Decimal("100") - transaction.income_regularity_score
        low_savings = max(Decimal("0"), Decimal("50") - financial.savings_ratio)
        cash_flow_stress = max(Decimal("0"), Decimal("100") - financial.cash_flow_score)
        debt_stress = min(Decimal("100"), financial.debt_ratio * Decimal("2"))
        emi_stress = min(Decimal("100"), financial.emi_burden * Decimal("2"))
        expense_stress = max(Decimal("0"), Decimal("100") - transaction.expense_stability_score)

        stress = (
            income_instability * Decimal("0.20")
            + low_savings * Decimal("0.20")
            + cash_flow_stress * Decimal("0.20")
            + debt_stress * Decimal("0.15")
            + emi_stress * Decimal("0.15")
            + expense_stress * Decimal("0.10")
        )
        return _clamp(stress)


class DormancyAnalyzer:
    """Dormancy risk classification: Low | Medium | High."""

    def analyze(
        self,
        aggregate: CustomerAggregate,
        transaction: TransactionAnalyticsProfile,
        digital: DigitalChannelProfile,
    ) -> str:
        dormant_accounts = sum(1 for a in aggregate.accounts if a.status == "Dormant")
        inactive_accounts = sum(1 for a in aggregate.accounts if a.status == "Inactive")
        low_txn = transaction.monthly_transaction_count < Decimal("20")
        no_digital = digital.digital_adoption_score < Decimal("30")
        few_products = sum(1 for p in aggregate.products if p.status == "Active") <= 1

        risk_points = dormant_accounts * 2 + inactive_accounts + int(low_txn) + int(no_digital) + int(few_products)

        if risk_points >= 4:
            return "High"
        if risk_points >= 2:
            return "Medium"
        return "Low"


class ChurnAnalyzer:
    """Churn risk score (0–100, higher = more likely to churn)."""

    def analyze(
        self,
        financial: FinancialProfile,
        transaction: TransactionAnalyticsProfile,
        digital: DigitalChannelProfile,
        relationship: RelationshipProfile,
        aggregate: CustomerAggregate,
    ) -> Decimal:
        low_balance = max(Decimal("0"), Decimal("100") - min(Decimal("100"), financial.average_balance / Decimal("100000") * Decimal("100")))
        reduced_txn = max(Decimal("0"), Decimal("100") - min(Decimal("100"), transaction.monthly_transaction_count))
        no_engagement = max(Decimal("0"), Decimal("100") - digital.engagement_score)
        weakening = max(Decimal("0"), Decimal("100") - relationship.relationship_strength_score)
        no_new_products = Decimal("30") if relationship.number_of_products <= 2 else Decimal("0")
        no_digital = max(Decimal("0"), Decimal("100") - digital.digital_adoption_score) * Decimal("0.5")

        dormant_penalty = Decimal("15") if any(a.status == "Dormant" for a in aggregate.accounts) else Decimal("0")

        churn = (
            low_balance * Decimal("0.20")
            + reduced_txn * Decimal("0.20")
            + no_engagement * Decimal("0.20")
            + weakening * Decimal("0.15")
            + no_new_products * Decimal("0.10")
            + no_digital * Decimal("0.10")
            + dormant_penalty * Decimal("0.05")
        )
        return _clamp(churn)


class RelationshipRiskAnalyzer:
    """Relationship stability, loyalty trend, and retention scoring."""

    def analyze(
        self,
        relationship: RelationshipProfile,
        transaction: TransactionAnalyticsProfile,
        digital: DigitalChannelProfile,
    ) -> dict[str, Decimal]:
        stability = (
            relationship.relationship_stability * Decimal("0.40")
            + transaction.transaction_consistency_score * Decimal("0.30")
            + transaction.income_regularity_score * Decimal("0.30")
        ).quantize(SCORE, ROUND_HALF_UP)

        retention = (
            relationship.loyalty_score * Decimal("0.35")
            + stability * Decimal("0.25")
            + digital.engagement_score * Decimal("0.20")
            + relationship.engagement_score * Decimal("0.20")
        ).quantize(SCORE, ROUND_HALF_UP)

        return {
            "relationship_stability": _clamp(stability),
            "retention_score": _clamp(retention),
            "loyalty_score": relationship.loyalty_score,
        }


class CrossSellReadinessAnalyzer:
    """Cross-sell readiness (0–100) — CRM indicator, NOT product recommendation."""

    def analyze(
        self,
        financial: FinancialProfile,
        relationship: RelationshipProfile,
        digital: DigitalChannelProfile,
        behaviour: BehaviourProfile,
        health_score: Decimal,
    ) -> Decimal:
        income_ready = min(Decimal("100"), financial.monthly_income / Decimal("100000") * Decimal("100"))
        savings_ready = min(Decimal("100"), financial.savings_ratio * Decimal("2"))

        readiness = (
            income_ready * Decimal("0.20")
            + savings_ready * Decimal("0.15")
            + relationship.relationship_strength_score * Decimal("0.20")
            + digital.digital_adoption_score * Decimal("0.15")
            + behaviour.investment_score * Decimal("0.10")
            + health_score * Decimal("0.20")
        )
        return _clamp(readiness)


class ExplanationEngine:
    """Generates explainable reason codes for all health metrics."""

    @staticmethod
    def generate(
        health_score: Decimal,
        stress_score: Decimal,
        churn_score: Decimal,
        dormancy: str,
        financial: FinancialProfile,
        transaction: TransactionAnalyticsProfile,
        digital: DigitalChannelProfile,
        relationship: RelationshipProfile,
    ) -> list[str]:
        reasons: list[str] = []

        if transaction.income_regularity_score >= Decimal("80"):
            reasons.append("Stable monthly income")
        elif transaction.income_regularity_score < Decimal("50"):
            reasons.append("Irregular income pattern")

        if financial.savings_ratio >= Decimal("30"):
            reasons.append("Healthy savings ratio")
        elif financial.savings_ratio < Decimal("10"):
            reasons.append("Low savings ratio")

        if digital.digital_adoption_score >= Decimal("70"):
            reasons.append("High digital engagement")
        elif digital.digital_adoption_score < Decimal("30"):
            reasons.append("No digital engagement")

        if relationship.relationship_strength_score >= Decimal("70"):
            reasons.append("Strong banking relationship")
        elif relationship.relationship_strength_score < Decimal("40"):
            reasons.append("Weakening banking relationship")

        if financial.debt_ratio <= Decimal("20"):
            reasons.append("Low debt burden")
        elif financial.debt_ratio >= Decimal("40"):
            reasons.append("Elevated debt burden")

        if financial.cash_flow_score >= Decimal("75"):
            reasons.append("Positive cash flow")
        elif financial.cash_flow_score < Decimal("40"):
            reasons.append("Cash flow pressure")

        if transaction.monthly_transaction_count >= Decimal("50"):
            reasons.append("Active transaction history")
        elif transaction.monthly_transaction_count < Decimal("15"):
            reasons.append("Reduced transactions")

        if financial.average_balance >= Decimal("200000"):
            reasons.append("Healthy average balance")
        elif financial.average_balance < Decimal("50000"):
            reasons.append("Average balance declining")

        if dormancy == "High":
            reasons.append("Dormant account detected")
        if churn_score >= Decimal("60"):
            reasons.append("Elevated churn risk indicators")
        if stress_score <= Decimal("25"):
            reasons.append("Low financial stress")
        if health_score >= Decimal("80"):
            reasons.append("Overall customer health is strong")

        return reasons[:10]


class RiskBandClassifier:
    """Assigns CRM business risk band."""

    @staticmethod
    def classify(health: Decimal, stress: Decimal, churn: Decimal, dormancy: str) -> str:
        if health >= Decimal("75") and churn <= Decimal("30") and stress <= Decimal("35") and dormancy == "Low":
            return "Healthy"
        if health < Decimal("30") or churn >= Decimal("80") or dormancy == "High":
            return "Critical"
        if health < Decimal("50") or churn >= Decimal("60") or stress >= Decimal("65"):
            return "At Risk"
        return "Monitor"


class CustomerHealthAnalytics:
    """Orchestrates all customer health and CRM risk analyzers."""

    def __init__(self) -> None:
        self._health = CustomerHealthAnalyzer()
        self._stress = FinancialStressAnalyzer()
        self._dormancy = DormancyAnalyzer()
        self._churn = ChurnAnalyzer()
        self._relationship_risk = RelationshipRiskAnalyzer()
        self._cross_sell = CrossSellReadinessAnalyzer()
        self._explanation = ExplanationEngine()
        self._risk_band = RiskBandClassifier()

    def calculate(self, data: CustomerHealthAnalyticsInput) -> CustomerHealthProfile:
        customer_id = data.aggregate.customer.customer_id

        health_score = self._health.analyze(
            data.relationship, data.digital, data.financial, data.transaction, data.aggregate
        )
        stress_score = self._stress.analyze(data.financial, data.transaction)
        dormancy = self._dormancy.analyze(data.aggregate, data.transaction, data.digital)
        churn_score = self._churn.analyze(
            data.financial, data.transaction, data.digital, data.relationship, data.aggregate
        )
        rel_risk = self._relationship_risk.analyze(data.relationship, data.transaction, data.digital)
        cross_sell = self._cross_sell.analyze(
            data.financial, data.relationship, data.digital, data.behaviour, health_score
        )
        reasons = self._explanation.generate(
            health_score, stress_score, churn_score, dormancy,
            data.financial, data.transaction, data.digital, data.relationship,
        )
        band = self._risk_band.classify(health_score, stress_score, churn_score, dormancy)

        profile = CustomerHealthProfile(
            customer_id=customer_id,
            customer_health_score=health_score,
            financial_stress_score=stress_score,
            churn_risk_score=churn_score,
            dormancy_risk=dormancy,
            relationship_stability=rel_risk["relationship_stability"],
            retention_score=rel_risk["retention_score"],
            cross_sell_readiness=cross_sell,
            risk_band=band,
            reason_codes=reasons,
        )

        logger.info(
            "Customer health analytics for customer_id=%s band=%s health=%s churn=%s",
            customer_id, band, health_score, churn_score,
        )
        return profile
