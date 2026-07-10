"""Lead Authenticity Engine — deterministic trust and completeness scoring."""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.external_intelligence_validation import ExternalLeadIntelligenceInput
from app.schemas.external_lead_intelligence import LeadAuthenticityResult

SCORE_PRECISION = Decimal("0.01")

PHONE_PATTERN = re.compile(r"^\+91\d{10}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class LeadAuthenticityEngine:
    """Estimates how trustworthy and complete an external lead record is."""

    FACTOR_WEIGHTS: dict[str, Decimal] = {
        "phone": Decimal("15"),
        "email": Decimal("15"),
        "employer": Decimal("12"),
        "occupation": Decimal("10"),
        "credit_score": Decimal("12"),
        "consent": Decimal("10"),
        "referral_source": Decimal("8"),
        "campaign": Decimal("8"),
        "city": Decimal("10"),
    }

    def calculate(self, data: ExternalLeadIntelligenceInput) -> LeadAuthenticityResult:
        score = Decimal("0")
        reasons: list[str] = []

        if self._valid_phone(data.phone_number):
            score += self.FACTOR_WEIGHTS["phone"]
            reasons.append("Valid phone number")
        if self._valid_email(data.email):
            score += self.FACTOR_WEIGHTS["email"]
            reasons.append("Valid contact details")
        if self._present(data.employer):
            score += self.FACTOR_WEIGHTS["employer"]
            reasons.append("Employer information available")
        if self._present(data.occupation):
            score += self.FACTOR_WEIGHTS["occupation"]
            reasons.append("Occupation available")
        if data.credit_score > 0:
            score += self.FACTOR_WEIGHTS["credit_score"]
            reasons.append("Credit score available")
        if data.consent:
            score += self.FACTOR_WEIGHTS["consent"]
            reasons.append("Consent available")
        if self._present(data.referral_source):
            score += self.FACTOR_WEIGHTS["referral_source"]
            reasons.append("Referral source available")
        if self._present(data.campaign):
            score += self.FACTOR_WEIGHTS["campaign"]
            reasons.append("Campaign information available")
        if self._present(data.city) and data.city != "Unknown":
            score += self.FACTOR_WEIGHTS["city"]
            reasons.append("City available")

        if data.employer and data.employer.lower() not in ("unknown", ""):
            reasons.append("Employer verified")

        final_score = min(Decimal("100"), score).quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)
        return LeadAuthenticityResult(lead_authenticity_score=final_score, reason_codes=reasons)

    @staticmethod
    def _valid_phone(phone: str) -> bool:
        return bool(PHONE_PATTERN.match(phone.strip()))

    @staticmethod
    def _valid_email(email: str) -> bool:
        return bool(EMAIL_PATTERN.match(email.strip().lower()))

    @staticmethod
    def _present(value: str | None) -> bool:
        return bool(value and value.strip() and value.strip().lower() not in ("unknown", "none", "nan"))
