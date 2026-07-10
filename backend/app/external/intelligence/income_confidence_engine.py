"""Income Confidence Engine — rule-based confidence in reported lead income."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.external_intelligence_validation import ExternalLeadIntelligenceInput
from app.schemas.external_lead_intelligence import IncomeConfidenceResult

SCORE_PRECISION = Decimal("0.01")

OCCUPATION_INCOME_RANGES: dict[str, tuple[int, int]] = {
    "Student": (100_000, 500_000),
    "Farmer": (200_000, 1_200_000),
    "Teacher": (400_000, 1_500_000),
    "Nurse": (350_000, 1_200_000),
    "Police Officer": (450_000, 1_400_000),
    "Sales Executive": (350_000, 2_000_000),
    "Software Engineer": (800_000, 4_000_000),
    "Government Employee": (500_000, 2_500_000),
    "Doctor": (1_200_000, 6_000_000),
    "Lawyer": (800_000, 5_000_000),
    "Chartered Accountant": (700_000, 4_000_000),
    "Professor": (600_000, 2_500_000),
    "Business Owner": (500_000, 10_000_000),
    "Retired": (200_000, 2_000_000),
}

PREMIUM_EMPLOYER_KEYWORDS = (
    "tcs",
    "infosys",
    "wipro",
    "hdfc",
    "icici",
    "apollo",
    "reliance",
    "tata",
    "state govt",
    "central govt",
    "government",
    "microsoft",
    "google",
    "amazon",
)


class IncomeConfidenceEngine:
    """Estimates confidence in the declared estimated income for a lead."""

    def calculate(self, data: ExternalLeadIntelligenceInput) -> IncomeConfidenceResult:
        score = Decimal("30")
        reasons: list[str] = []

        employer_score = self._employer_type_score(data.employer)
        score += employer_score
        if employer_score >= Decimal("15"):
            reasons.append("Recognized employer type")

        occupation_score = self._occupation_score(data.occupation)
        score += occupation_score
        if occupation_score > 0:
            reasons.append("Occupation supports income declaration")

        consistency_score = self._income_range_consistency(data)
        score += consistency_score
        if consistency_score >= Decimal("15"):
            reasons.append("Income consistent with occupation")
        elif consistency_score < Decimal("5"):
            reasons.append("Income may be inconsistent with occupation")

        credit_bonus = self._credit_score_bonus(data.credit_score)
        score += credit_bonus
        if credit_bonus >= Decimal("10"):
            reasons.append("Credit score supports income profile")

        emi_penalty = self._emi_burden_penalty(data)
        score -= emi_penalty
        if emi_penalty > 0:
            reasons.append("EMI burden reduces income confidence")

        final_score = min(Decimal("100"), max(Decimal("0"), score)).quantize(
            SCORE_PRECISION, rounding=ROUND_HALF_UP
        )
        level = self._confidence_level(final_score)

        return IncomeConfidenceResult(
            income_confidence_score=final_score,
            income_confidence_level=level,
            reason_codes=reasons,
        )

    def _employer_type_score(self, employer: str) -> Decimal:
        key = employer.strip().lower()
        if not key or key == "unknown":
            return Decimal("0")
        for keyword in PREMIUM_EMPLOYER_KEYWORDS:
            if keyword in key:
                return Decimal("20")
        return Decimal("10")

    @staticmethod
    def _occupation_score(occupation: str) -> Decimal:
        stable = {
            "Government Employee",
            "Doctor",
            "Chartered Accountant",
            "Professor",
            "Software Engineer",
        }
        if occupation in stable:
            return Decimal("15")
        if occupation in ("Teacher", "Lawyer", "Nurse", "Police Officer"):
            return Decimal("10")
        if occupation == "Business Owner":
            return Decimal("8")
        if occupation == "Student":
            return Decimal("3")
        return Decimal("5")

    def _income_range_consistency(self, data: ExternalLeadIntelligenceInput) -> Decimal:
        income = int(data.estimated_income)
        occ_range = OCCUPATION_INCOME_RANGES.get(data.occupation)
        if occ_range is None:
            if income > 0:
                return Decimal("8")
            return Decimal("0")

        low, high = occ_range
        if low <= income <= high:
            return Decimal("25")
        if income < low:
            ratio = income / low if low > 0 else 0
            return Decimal(str(max(0, min(12, ratio * 12))))
        if income > high:
            overflow = income / high if high > 0 else 2
            if overflow <= 1.5:
                return Decimal("15")
            return Decimal("5")
        return Decimal("0")

    @staticmethod
    def _credit_score_bonus(credit_score: int) -> Decimal:
        if credit_score >= 750:
            return Decimal("15")
        if credit_score >= 700:
            return Decimal("12")
        if credit_score >= 650:
            return Decimal("8")
        if credit_score >= 600:
            return Decimal("4")
        return Decimal("0")

    @staticmethod
    def _emi_burden_penalty(data: ExternalLeadIntelligenceInput) -> Decimal:
        monthly_income = data.estimated_income / Decimal("12")
        if monthly_income <= 0:
            return Decimal("0")
        burden_pct = (data.monthly_emi / monthly_income) * Decimal("100")
        if burden_pct > Decimal("60"):
            return Decimal("20")
        if burden_pct > Decimal("45"):
            return Decimal("12")
        if burden_pct > Decimal("30"):
            return Decimal("5")
        return Decimal("0")

    @staticmethod
    def _confidence_level(score: Decimal) -> str:
        if score >= Decimal("75"):
            return "High"
        if score >= Decimal("50"):
            return "Medium"
        return "Low"
