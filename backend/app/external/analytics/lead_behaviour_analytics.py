"""Lead Behaviour Analytics — deterministic CRM engagement metrics for external leads."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.external_analytics import LeadBehaviourAnalyticsResult
from app.schemas.external_analytics_input import ExternalLeadAnalyticsInput

SCORE_PRECISION = Decimal("0.01")

HIGH_ENGAGEMENT_CAMPAIGNS = frozenset(
    {
        "digital lending",
        "salary account",
        "premium banking",
        "wealth management",
        "credit card",
        "home loan",
    }
)

DIGITAL_CAMPAIGN_KEYWORDS = ("digital", "online", "app", "mobile", "sms", "whatsapp")

PREMIUM_REFERRAL_SOURCES = frozenset(
    {
        "existing customer",
        "branch referral",
        "employee referral",
        "partner referral",
    }
)


class LeadBehaviourAnalytics:
    """
    Computes engagement and communication behaviour scores for external leads.

    Uses only lead CRM fields and enriched profile attributes — no transaction data.
    """

    def calculate(self, data: ExternalLeadAnalyticsInput) -> LeadBehaviourAnalyticsResult:
        campaign_engagement = self._campaign_engagement_score(data)
        referral_quality = self._referral_quality_score(data)
        digital_readiness = self._digital_readiness_score(data)
        consent_strength = self._consent_strength(data)
        communication_readiness = self._communication_readiness_score(
            data, digital_readiness, consent_strength
        )
        preferred_channel = self._preferred_contact_channel(data, digital_readiness, consent_strength)
        preferred_time = self._preferred_contact_time(data)
        marketing_responsiveness = self._marketing_responsiveness_score(
            data, campaign_engagement, referral_quality, consent_strength
        )
        persona_confidence = self._customer_persona_confidence(data)

        return LeadBehaviourAnalyticsResult(
            campaign_engagement_score=campaign_engagement,
            referral_quality_score=referral_quality,
            digital_readiness_score=digital_readiness,
            communication_readiness_score=communication_readiness,
            consent_strength=consent_strength,
            preferred_contact_channel=preferred_channel,
            preferred_contact_time=preferred_time,
            marketing_responsiveness_score=marketing_responsiveness,
            customer_persona_confidence=persona_confidence,
        )

    @staticmethod
    def _q(value: Decimal) -> Decimal:
        return value.quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    def _campaign_engagement_score(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        score = Decimal("40")
        campaign_lower = data.campaign.lower()
        for high in HIGH_ENGAGEMENT_CAMPAIGNS:
            if high in campaign_lower:
                score += Decimal("25")
                break
        else:
            score += Decimal("10")
        if any(kw in campaign_lower for kw in DIGITAL_CAMPAIGN_KEYWORDS):
            score += Decimal("15")
        if data.consent:
            score += Decimal("15")
        if data.lead_status in ("ENRICHED", "QUALIFIED", "CONTACTED", "ANALYTICS_READY"):
            score += Decimal("10")
        return self._q(min(Decimal("100"), score))

    def _referral_quality_score(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        source = data.referral_source.lower()
        if source in PREMIUM_REFERRAL_SOURCES:
            return Decimal("90")
        if "referral" in source:
            return Decimal("75")
        if source in ("direct", "website", "walk-in"):
            return Decimal("60")
        if source in ("cold call", "purchased list"):
            return Decimal("35")
        return Decimal("50")

    def _digital_readiness_score(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        score = data.digital_adoption if data.digital_adoption > 0 else Decimal("40")
        if data.age < 45:
            score += Decimal("15")
        if any(kw in data.campaign.lower() for kw in DIGITAL_CAMPAIGN_KEYWORDS):
            score += Decimal("15")
        if data.consent and data.email:
            score += Decimal("10")
        if data.phone_number.startswith("+91"):
            score += Decimal("5")
        return self._q(min(Decimal("100"), score))

    @staticmethod
    def _consent_strength(data: ExternalLeadAnalyticsInput) -> Decimal:
        if not data.consent:
            return Decimal("0")
        strength = Decimal("70")
        if data.phone_number and data.email:
            strength += Decimal("20")
        if data.lead_status in ("ENRICHED", "QUALIFIED", "ANALYTICS_READY"):
            strength += Decimal("10")
        return min(Decimal("100"), strength).quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    def _communication_readiness_score(
        self,
        data: ExternalLeadAnalyticsInput,
        digital_readiness: Decimal,
        consent_strength: Decimal,
    ) -> Decimal:
        score = (digital_readiness * Decimal("0.4")) + (consent_strength * Decimal("0.4"))
        if data.phone_number:
            score += Decimal("10")
        if data.email and "@" in data.email:
            score += Decimal("10")
        return self._q(min(Decimal("100"), score))

    def _preferred_contact_channel(
        self,
        data: ExternalLeadAnalyticsInput,
        digital_readiness: Decimal,
        consent_strength: Decimal,
    ) -> str:
        if data.preferred_channel:
            return data.preferred_channel
        if not data.consent:
            return "Branch"
        if digital_readiness >= Decimal("75") and consent_strength >= Decimal("70"):
            return "Voice"
        if digital_readiness >= Decimal("65"):
            return "Mobile App"
        if digital_readiness >= Decimal("50"):
            return "WhatsApp"
        if consent_strength >= Decimal("50"):
            return "Phone"
        return "Email"

    def _preferred_contact_time(self, data: ExternalLeadAnalyticsInput) -> str:
        if data.preferred_contact_time:
            return data.preferred_contact_time
        if data.occupation in ("Doctor", "Nurse", "Police Officer"):
            return "Evening (18:00–20:00)"
        if data.occupation == "Business Owner":
            return "Late Morning (11:00–13:00)"
        if data.occupation in ("Student", "Retired"):
            return "Afternoon (14:00–16:00)"
        if data.age < 30:
            return "Evening (18:00–20:00)"
        return "Morning (10:00–12:00)"

    def _marketing_responsiveness_score(
        self,
        data: ExternalLeadAnalyticsInput,
        campaign_engagement: Decimal,
        referral_quality: Decimal,
        consent_strength: Decimal,
    ) -> Decimal:
        score = (
            campaign_engagement * Decimal("0.35")
            + referral_quality * Decimal("0.25")
            + consent_strength * Decimal("0.40")
        )
        return self._q(min(Decimal("100"), score))

    def _customer_persona_confidence(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        if not data.customer_persona:
            return Decimal("40")
        score = Decimal("55")
        income = data.estimated_income
        persona = data.customer_persona

        persona_income_fit = {
            "High Net Worth": income >= Decimal("5000000"),
            "Salary Elite": income >= Decimal("2500000"),
            "Premium": income >= Decimal("2000000") or data.credit_score >= 720,
            "Business Owner": data.occupation == "Business Owner",
            "Student": data.occupation == "Student" or data.age < 24,
            "Retired": data.occupation == "Retired" or data.age >= 60,
            "Young Professional": 22 <= data.age <= 35,
            "Family": 30 <= data.age <= 50 and income >= Decimal("1000000"),
            "Mass Market": True,
        }
        if persona_income_fit.get(persona, False):
            score += Decimal("30")
        if data.credit_score >= 650:
            score += Decimal("10")
        if data.occupation and data.occupation != "Unknown":
            score += Decimal("5")
        return self._q(min(Decimal("100"), score))
