"""Internal customer behaviour summary aggregation — reuses existing profile and feature store values."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

SCORE_PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class InternalSummaryInput:
    """Snapshot of pre-computed internal analytics for aggregation only."""

    customer_health_score: Decimal | None
    financial_stress_score: Decimal | None
    monthly_income: Decimal | None
    monthly_savings: Decimal | None
    cash_flow_score: Decimal | None
    liquidity_score: Decimal | None
    debt_ratio: Decimal | None
    income_regularity_score: Decimal | None
    emi_burden: Decimal | None
    expense_stability_score: Decimal | None
    digital_payment_ratio: Decimal | None
    digital_adoption_score: Decimal | None
    voice_readiness_score: Decimal | None
    sms_readiness_score: Decimal | None
    whatsapp_readiness_score: Decimal | None
    email_readiness_score: Decimal | None
    upi_usage_score: Decimal | None
    net_banking_usage_score: Decimal | None


class InternalBehaviourSummaryAggregator:
    """
    Aggregates existing internal Customer360 analytics into standardized summary scores.

    No new analytics — weighted combination of values already computed by prior engines.
    """

    def aggregate(self, data: InternalSummaryInput) -> tuple[Decimal, Decimal, Decimal]:
        financial_health = self._financial_health_score(data)
        repayment = self._repayment_behaviour_score(data)
        digital = self._digital_engagement_score(data)
        return financial_health, repayment, digital

    @staticmethod
    def _q(value: Decimal) -> Decimal:
        return value.quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    @staticmethod
    def _clamp(value: Decimal) -> Decimal:
        return max(Decimal("0"), min(Decimal("100"), value))

    @staticmethod
    def _weighted_avg(components: list[tuple[Decimal | None, Decimal]]) -> Decimal:
        total_weight = Decimal("0")
        weighted_sum = Decimal("0")
        for value, weight in components:
            if value is None:
                continue
            weighted_sum += value * weight
            total_weight += weight
        if total_weight == 0:
            return Decimal("0")
        return weighted_sum / total_weight

    def _savings_ratio(self, data: InternalSummaryInput) -> Decimal | None:
        if not data.monthly_income or data.monthly_income <= 0:
            return None
        if data.monthly_savings is None:
            return None
        return (data.monthly_savings / data.monthly_income) * Decimal("100")

    def _financial_stability(self, data: InternalSummaryInput) -> Decimal | None:
        if data.financial_stress_score is None:
            return None
        return self._clamp(Decimal("100") - data.financial_stress_score)

    def _financial_health_score(self, data: InternalSummaryInput) -> Decimal:
        savings_ratio = self._savings_ratio(data)
        savings_component = (
            self._clamp(savings_ratio * Decimal("2")) if savings_ratio is not None else None
        )
        debt_inverse = (
            self._clamp(Decimal("100") - data.debt_ratio) if data.debt_ratio is not None else None
        )
        score = self._weighted_avg(
            [
                (data.customer_health_score, Decimal("0.25")),
                (self._financial_stability(data), Decimal("0.20")),
                (savings_component, Decimal("0.15")),
                (data.cash_flow_score, Decimal("0.15")),
                (data.liquidity_score, Decimal("0.15")),
                (debt_inverse, Decimal("0.10")),
            ]
        )
        return self._q(self._clamp(score))

    def _repayment_behaviour_score(self, data: InternalSummaryInput) -> Decimal:
        savings_ratio = self._savings_ratio(data)
        savings_behaviour = (
            self._clamp(savings_ratio * Decimal("2")) if savings_ratio is not None else None
        )
        emi_inverse = (
            self._clamp(Decimal("100") - data.emi_burden) if data.emi_burden is not None else None
        )
        score = self._weighted_avg(
            [
                (data.income_regularity_score, Decimal("0.25")),
                (savings_behaviour, Decimal("0.20")),
                (emi_inverse, Decimal("0.15")),
                (data.cash_flow_score, Decimal("0.15")),
                (data.expense_stability_score, Decimal("0.15")),
                (data.digital_payment_ratio, Decimal("0.10")),
            ]
        )
        return self._q(self._clamp(score))

    def _digital_engagement_score(self, data: InternalSummaryInput) -> Decimal:
        score = self._weighted_avg(
            [
                (data.digital_adoption_score, Decimal("0.25")),
                (data.voice_readiness_score, Decimal("0.15")),
                (data.sms_readiness_score, Decimal("0.10")),
                (data.whatsapp_readiness_score, Decimal("0.15")),
                (data.email_readiness_score, Decimal("0.10")),
                (data.net_banking_usage_score, Decimal("0.12")),
                (data.upi_usage_score, Decimal("0.13")),
            ]
        )
        return self._q(self._clamp(score))
