"""Deterministic reason code engine for Explainable AI."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ReasonCodeInput:
    """Financial and behavioural signals used to derive reason codes."""

    monthly_income: Decimal | float | None
    emi_burden: Decimal | float | None
    credit_score: int | None
    financial_health_score: Decimal | float | None
    digital_engagement_score: Decimal | float | None
    savings_ratio: Decimal | float | None
    repayment_capacity: str | None
    repayment_confidence: float | None
    consent: bool | None = None
    lead_quality_score: Decimal | float | None = None


class ReasonCodeEngine:
    """
    Generates deterministic, regulator-friendly reason codes from structured data.

    OpenAI receives only these codes — it must not invent new reasons.
    """

    INCOME_STABLE_THRESHOLD = Decimal("50000")
    EMI_LOW_THRESHOLD = Decimal("20")
    CREDIT_EXCELLENT_THRESHOLD = 750
    CREDIT_GOOD_THRESHOLD = 650
    HEALTH_STRONG_THRESHOLD = Decimal("85")
    HEALTH_GOOD_THRESHOLD = Decimal("70")
    DIGITAL_EXCELLENT_THRESHOLD = Decimal("85")
    DIGITAL_GOOD_THRESHOLD = Decimal("70")
    SAVINGS_HIGH_THRESHOLD = Decimal("30")
    SAVINGS_GOOD_THRESHOLD = Decimal("15")

    def generate(self, data: ReasonCodeInput) -> list[str]:
        codes: list[str] = []
        codes.extend(self._income_codes(data.monthly_income))
        codes.extend(self._emi_codes(data.emi_burden))
        codes.extend(self._credit_codes(data.credit_score))
        codes.extend(self._health_codes(data.financial_health_score))
        codes.extend(self._digital_codes(data.digital_engagement_score))
        codes.extend(self._savings_codes(data.savings_ratio))
        codes.extend(self._repayment_codes(data.repayment_capacity, data.repayment_confidence))
        codes.extend(self._consent_codes(data.consent))
        codes.extend(self._lead_quality_codes(data.lead_quality_score))

        seen: set[str] = set()
        unique: list[str] = []
        for code in codes:
            if code not in seen:
                seen.add(code)
                unique.append(code)
        return unique[:10]

    def _income_codes(self, income: Decimal | float | None) -> list[str]:
        if income is None:
            return []
        value = Decimal(str(income))
        if value >= self.INCOME_STABLE_THRESHOLD:
            return ["Stable Salary"]
        if value >= Decimal("30000"):
            return ["Moderate Income"]
        return ["Income Below Preferred Threshold"]

    def _emi_codes(self, emi: Decimal | float | None) -> list[str]:
        if emi is None:
            return []
        value = Decimal(str(emi))
        if value < self.EMI_LOW_THRESHOLD:
            return ["Low EMI Burden"]
        if value < Decimal("35"):
            return ["Manageable EMI Burden"]
        return ["Elevated EMI Burden"]

    def _credit_codes(self, credit: int | None) -> list[str]:
        if credit is None:
            return []
        if credit >= self.CREDIT_EXCELLENT_THRESHOLD:
            return ["Excellent Credit Score"]
        if credit >= self.CREDIT_GOOD_THRESHOLD:
            return ["Good Credit Score"]
        return ["Credit Score Needs Review"]

    def _health_codes(self, score: Decimal | float | None) -> list[str]:
        if score is None:
            return []
        value = Decimal(str(score))
        if value >= self.HEALTH_STRONG_THRESHOLD:
            return ["Strong Financial Health"]
        if value >= self.HEALTH_GOOD_THRESHOLD:
            return ["Adequate Financial Health"]
        return ["Financial Health Requires Attention"]

    def _digital_codes(self, score: Decimal | float | None) -> list[str]:
        if score is None:
            return []
        value = Decimal(str(score))
        if value >= self.DIGITAL_EXCELLENT_THRESHOLD:
            return ["High Digital Engagement"]
        if value >= self.DIGITAL_GOOD_THRESHOLD:
            return ["Good Digital Engagement"]
        return ["Limited Digital Engagement"]

    def _savings_codes(self, ratio: Decimal | float | None) -> list[str]:
        if ratio is None:
            return []
        value = Decimal(str(ratio))
        if value >= self.SAVINGS_HIGH_THRESHOLD:
            return ["High Savings Ratio"]
        if value >= self.SAVINGS_GOOD_THRESHOLD:
            return ["Healthy Savings Ratio"]
        return []

    def _repayment_codes(self, capacity: str | None, confidence: float | None) -> list[str]:
        if capacity in ("Very High", "High"):
            return ["Strong Repayment Capacity"]
        if capacity == "Medium":
            return ["Moderate Repayment Capacity"]
        if capacity == "Low":
            return ["Limited Repayment Capacity"]
        return []

    def _consent_codes(self, consent: bool | None) -> list[str]:
        if consent is True:
            return ["Verified Consent"]
        if consent is False:
            return ["Consent Not Provided"]
        return []

    def _lead_quality_codes(self, score: Decimal | float | None) -> list[str]:
        if score is None:
            return []
        value = Decimal(str(score))
        if value >= Decimal("80"):
            return ["High Lead Quality"]
        if value >= Decimal("60"):
            return ["Qualified Lead Profile"]
        return []

    @staticmethod
    def to_dict_list(codes: list[str]) -> list[dict[str, str]]:
        return [{"code": c, "description": c} for c in codes]
