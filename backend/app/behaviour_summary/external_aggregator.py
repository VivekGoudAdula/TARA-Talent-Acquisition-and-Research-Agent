"""External lead behaviour summary aggregation — reuses existing profile values."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

SCORE_PRECISION = Decimal("0.01")

CREDIT_QUALITY_SCORES: dict[str, Decimal] = {
    "Excellent": Decimal("95"),
    "Very Good": Decimal("85"),
    "Good": Decimal("75"),
    "Fair": Decimal("60"),
    "Average": Decimal("50"),
    "Below Average": Decimal("35"),
}

CHANNEL_ENGAGEMENT_SCORES: dict[str, Decimal] = {
    "Mobile App": Decimal("95"),
    "Voice": Decimal("90"),
    "WhatsApp": Decimal("88"),
    "Phone": Decimal("75"),
    "Email": Decimal("70"),
    "Branch": Decimal("55"),
}


@dataclass(frozen=True)
class ExternalSummaryInput:
    """Snapshot of pre-computed external lead analytics for aggregation only."""

    financial_capacity_score: Decimal | None
    lead_quality_score: Decimal | None
    income_confidence_score: Decimal | None
    estimated_repayment_capacity: Decimal | None
    estimated_income: Decimal | None
    income_stability_score: Decimal | None
    credit_quality: str | None
    lead_authenticity_score: Decimal | None
    digital_readiness_score: Decimal | None
    communication_readiness_score: Decimal | None
    campaign_engagement_score: Decimal | None
    preferred_channel: str | None


class ExternalBehaviourSummaryAggregator:
    """
    Aggregates existing external lead analytics into standardized summary scores.

    No new analytics — weighted combination of values already computed by prior engines.
    """

    def aggregate(self, data: ExternalSummaryInput) -> tuple[Decimal, Decimal, Decimal]:
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

    def _repayment_capacity_score(self, data: ExternalSummaryInput) -> Decimal | None:
        if data.estimated_repayment_capacity is None or data.estimated_income is None:
            return None
        if data.estimated_income <= 0:
            return None
        monthly_income = data.estimated_income / Decimal("12")
        if monthly_income <= 0:
            return None
        ratio = data.estimated_repayment_capacity / monthly_income
        return self._clamp(ratio * Decimal("100"))

    def _credit_quality_score(self, credit_quality: str | None) -> Decimal | None:
        if not credit_quality:
            return None
        return CREDIT_QUALITY_SCORES.get(credit_quality, Decimal("50"))

    def _channel_engagement_score(self, channel: str | None) -> Decimal | None:
        if not channel:
            return None
        for key, score in CHANNEL_ENGAGEMENT_SCORES.items():
            if key.lower() in channel.lower():
                return score
        return Decimal("60")

    def _financial_health_score(self, data: ExternalSummaryInput) -> Decimal:
        score = self._weighted_avg(
            [
                (data.financial_capacity_score, Decimal("0.40")),
                (data.lead_quality_score, Decimal("0.30")),
                (data.income_confidence_score, Decimal("0.30")),
            ]
        )
        return self._q(self._clamp(score))

    def _repayment_behaviour_score(self, data: ExternalSummaryInput) -> Decimal:
        score = self._weighted_avg(
            [
                (data.financial_capacity_score, Decimal("0.25")),
                (self._repayment_capacity_score(data), Decimal("0.25")),
                (data.income_stability_score, Decimal("0.20")),
                (self._credit_quality_score(data.credit_quality), Decimal("0.15")),
                (data.lead_authenticity_score, Decimal("0.15")),
            ]
        )
        return self._q(self._clamp(score))

    def _digital_engagement_score(self, data: ExternalSummaryInput) -> Decimal:
        score = self._weighted_avg(
            [
                (data.digital_readiness_score, Decimal("0.35")),
                (data.communication_readiness_score, Decimal("0.25")),
                (data.campaign_engagement_score, Decimal("0.25")),
                (self._channel_engagement_score(data.preferred_channel), Decimal("0.15")),
            ]
        )
        return self._q(self._clamp(score))
