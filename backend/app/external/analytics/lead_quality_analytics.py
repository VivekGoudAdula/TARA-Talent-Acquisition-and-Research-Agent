"""Lead Quality Analytics — qualification and sales readiness for external leads."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.external_analytics import (
    FinancialCapacityAnalyticsResult,
    LeadBehaviourAnalyticsResult,
    LeadQualityAnalyticsResult,
)
from app.schemas.external_analytics_input import ExternalLeadAnalyticsInput

SCORE_PRECISION = Decimal("0.01")


class LeadQualityAnalytics:
    """
    Computes lead quality, qualification status, and sales readiness.

    Combines behaviour and financial capacity outputs with lead CRM completeness.
    """

    def calculate(
        self,
        data: ExternalLeadAnalyticsInput,
        behaviour: LeadBehaviourAnalyticsResult,
        financial: FinancialCapacityAnalyticsResult,
    ) -> LeadQualityAnalyticsResult:
        kyc_readiness = self._kyc_readiness(data)
        conversion_readiness = self._conversion_readiness(data, behaviour, financial, kyc_readiness)
        lead_quality_score = self._lead_quality_score(
            data, behaviour, financial, kyc_readiness, conversion_readiness
        )
        qualification_status = self._qualification_status(
            lead_quality_score, kyc_readiness, financial, data
        )
        priority_level = self._priority_level(lead_quality_score, financial, behaviour)
        sales_readiness = self._sales_readiness(
            conversion_readiness, behaviour, kyc_readiness, data
        )

        return LeadQualityAnalyticsResult(
            lead_quality_score=lead_quality_score,
            conversion_readiness=conversion_readiness,
            qualification_status=qualification_status,
            kyc_readiness=kyc_readiness,
            priority_level=priority_level,
            sales_readiness=sales_readiness,
        )

    @staticmethod
    def _q(value: Decimal) -> Decimal:
        return value.quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    def _kyc_readiness(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        score = Decimal("0")
        if data.full_name and len(data.full_name.strip()) > 2:
            score += Decimal("20")
        if data.phone_number and len(data.phone_number) >= 10:
            score += Decimal("25")
        if data.email and "@" in data.email:
            score += Decimal("20")
        if data.city and data.city != "Unknown":
            score += Decimal("10")
        if data.occupation and data.occupation != "Unknown":
            score += Decimal("10")
        if data.estimated_income > 0:
            score += Decimal("10")
        if data.consent:
            score += Decimal("5")
        return self._q(min(Decimal("100"), score))

    def _conversion_readiness(
        self,
        data: ExternalLeadAnalyticsInput,
        behaviour: LeadBehaviourAnalyticsResult,
        financial: FinancialCapacityAnalyticsResult,
        kyc_readiness: Decimal,
    ) -> Decimal:
        score = (
            behaviour.marketing_responsiveness_score * Decimal("0.25")
            + financial.financial_capacity_score * Decimal("0.30")
            + kyc_readiness * Decimal("0.20")
            + data.lead_score * Decimal("0.15")
            + behaviour.campaign_engagement_score * Decimal("0.10")
        )
        if data.consent:
            score += Decimal("5")
        if data.relationship_potential >= Decimal("70"):
            score += Decimal("5")
        return self._q(min(Decimal("100"), score))

    def _lead_quality_score(
        self,
        data: ExternalLeadAnalyticsInput,
        behaviour: LeadBehaviourAnalyticsResult,
        financial: FinancialCapacityAnalyticsResult,
        kyc_readiness: Decimal,
        conversion_readiness: Decimal,
    ) -> Decimal:
        score = (
            conversion_readiness * Decimal("0.35")
            + financial.financial_capacity_score * Decimal("0.25")
            + behaviour.referral_quality_score * Decimal("0.15")
            + behaviour.digital_readiness_score * Decimal("0.10")
            + kyc_readiness * Decimal("0.15")
        )
        if data.credit_score >= 700:
            score += Decimal("3")
        return self._q(min(Decimal("100"), score))

    def _qualification_status(
        self,
        lead_quality_score: Decimal,
        kyc_readiness: Decimal,
        financial: FinancialCapacityAnalyticsResult,
        data: ExternalLeadAnalyticsInput,
    ) -> str:
        if (
            lead_quality_score >= Decimal("70")
            and kyc_readiness >= Decimal("70")
            and financial.financial_capacity_score >= Decimal("60")
            and data.consent
        ):
            return "Qualified"
        if lead_quality_score >= Decimal("50") and kyc_readiness >= Decimal("50"):
            return "Partially Qualified"
        return "Not Qualified"

    def _priority_level(
        self,
        lead_quality_score: Decimal,
        financial: FinancialCapacityAnalyticsResult,
        behaviour: LeadBehaviourAnalyticsResult,
    ) -> str:
        if lead_quality_score >= Decimal("80") and financial.affordability_level == "High":
            return "High"
        if lead_quality_score >= Decimal("65") or behaviour.campaign_engagement_score >= Decimal("75"):
            return "Medium"
        return "Low"

    def _sales_readiness(
        self,
        conversion_readiness: Decimal,
        behaviour: LeadBehaviourAnalyticsResult,
        kyc_readiness: Decimal,
        data: ExternalLeadAnalyticsInput,
    ) -> Decimal:
        score = (
            conversion_readiness * Decimal("0.45")
            + behaviour.communication_readiness_score * Decimal("0.30")
            + kyc_readiness * Decimal("0.25")
        )
        if not data.consent:
            score *= Decimal("0.6")
        return self._q(min(Decimal("100"), score))
