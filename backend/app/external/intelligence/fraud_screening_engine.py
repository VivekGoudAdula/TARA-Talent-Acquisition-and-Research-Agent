"""Fraud Screening Engine — deterministic duplicate and data-quality checks."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.external_intelligence_validation import ExternalLeadIntelligenceInput
from app.schemas.external_lead_intelligence import FraudScreeningResult

SCORE_PRECISION = Decimal("0.01")

DISPOSABLE_EMAIL_DOMAINS = frozenset(
    {
        "mailinator.com",
        "tempmail.com",
        "throwaway.email",
        "guerrillamail.com",
        "yopmail.com",
        "10minutemail.com",
        "trashmail.com",
        "fakeinbox.com",
        "getnada.com",
        "dispostable.com",
    }
)

MIN_INCOME = 50_000
MAX_INCOME = 50_000_000
MIN_CREDIT = 300
MAX_CREDIT = 900
MIN_AGE = 18
MAX_AGE = 75


class FraudScreeningEngine:
    """
    Deterministic fraud risk screening for external leads.

    Not AML. Not ML prediction. Validation and duplicate detection only.
    """

    def calculate(self, data: ExternalLeadIntelligenceInput) -> FraudScreeningResult:
        score = Decimal("0")
        reasons: list[str] = []

        if data.duplicate_phone:
            score += Decimal("30")
            reasons.append("Duplicate phone number detected")
        if data.duplicate_email:
            score += Decimal("30")
            reasons.append("Duplicate email detected")
        if data.duplicate_lead_reference:
            score += Decimal("25")
            reasons.append("Duplicate lead reference detected")

        if not self._valid_age(data.age):
            score += Decimal("20")
            reasons.append("Invalid age")

        if not self._valid_income(data.estimated_income):
            score += Decimal("15")
            reasons.append("Invalid estimated income")

        if not self._valid_credit_score(data.credit_score):
            score += Decimal("15")
            reasons.append("Invalid credit score")

        if not data.consent:
            score += Decimal("10")
            reasons.append("Missing marketing consent")

        if self._is_disposable_email(data.email):
            score += Decimal("25")
            reasons.append("Disposable email domain detected")

        final_score = min(Decimal("100"), score).quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)
        risk = self._risk_band(final_score)

        if final_score <= Decimal("15") and not reasons:
            reasons.append("No fraud indicators detected")

        return FraudScreeningResult(
            fraud_score=final_score,
            fraud_risk=risk,
            fraud_reason_codes=reasons,
        )

    @staticmethod
    def _valid_age(age: int) -> bool:
        return MIN_AGE <= age <= MAX_AGE

    @staticmethod
    def _valid_income(income: Decimal) -> bool:
        return Decimal(str(MIN_INCOME)) <= income <= Decimal(str(MAX_INCOME))

    @staticmethod
    def _valid_credit_score(score: int) -> bool:
        return MIN_CREDIT <= score <= MAX_CREDIT

    @staticmethod
    def _is_disposable_email(email: str) -> bool:
        domain = email.split("@")[-1].lower().strip() if "@" in email else ""
        return domain in DISPOSABLE_EMAIL_DOMAINS

    @staticmethod
    def _risk_band(fraud_score: Decimal) -> str:
        if fraud_score >= Decimal("50"):
            return "High"
        if fraud_score >= Decimal("20"):
            return "Medium"
        return "Low"
