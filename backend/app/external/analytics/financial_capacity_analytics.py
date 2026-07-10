"""Financial Capacity Analytics — rule-based affordability metrics for external leads."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.external_analytics import FinancialCapacityAnalyticsResult
from app.schemas.external_analytics_input import ExternalLeadAnalyticsInput

SCORE_PRECISION = Decimal("0.01")
MONEY_PRECISION = Decimal("0.01")

STABLE_OCCUPATIONS = frozenset(
    {
        "Government Employee",
        "Doctor",
        "Professor",
        "Chartered Accountant",
        "Teacher",
        "Police Officer",
    }
)


class FinancialCapacityAnalytics:
    """
    Computes financial capacity and affordability from declared lead income and credit data.

    No transaction history is used — only estimated_income, credit_score, monthly_emi,
    and enrichment profile fields.
    """

    def calculate(self, data: ExternalLeadAnalyticsInput) -> FinancialCapacityAnalyticsResult:
        income_segment = data.income_segment or self._income_segment(data.estimated_income)
        income_stability = self._income_stability(data)
        emi_burden = self._emi_burden(data)
        credit_quality = self._credit_quality_label(data.credit_score)
        repayment_capacity = self._estimated_repayment_capacity(data, emi_burden)
        financial_capacity_score = self._financial_capacity_score(
            data, income_stability, emi_burden, repayment_capacity
        )
        affordability_level = self._affordability_level(financial_capacity_score, emi_burden)

        return FinancialCapacityAnalyticsResult(
            financial_capacity_score=financial_capacity_score,
            estimated_repayment_capacity=repayment_capacity,
            income_segment=income_segment,
            income_stability=income_stability,
            emi_burden=emi_burden,
            credit_quality=credit_quality,
            affordability_level=affordability_level,
        )

    @staticmethod
    def _q(value: Decimal) -> Decimal:
        return value.quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)

    def _income_segment(self, income: Decimal) -> str:
        if income >= Decimal("10000000"):
            return "Ultra High Income"
        if income >= Decimal("5000000"):
            return "High Net Worth"
        if income >= Decimal("2500000"):
            return "Affluent"
        if income >= Decimal("1200000"):
            return "Upper Middle"
        if income >= Decimal("600000"):
            return "Middle Income"
        if income >= Decimal("300000"):
            return "Emerging"
        return "Mass Market"

    def _income_stability(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        score = Decimal("35")
        if data.occupation in STABLE_OCCUPATIONS:
            score += Decimal("30")
        elif data.occupation in ("Software Engineer", "Lawyer", "Nurse"):
            score += Decimal("20")
        elif data.occupation == "Business Owner":
            score += Decimal("15")
        elif data.occupation == "Student":
            score += Decimal("5")
        if data.credit_score >= 720:
            score += Decimal("25")
        elif data.credit_score >= 650:
            score += Decimal("15")
        elif data.credit_score >= 600:
            score += Decimal("8")
        if data.financial_stability > 0:
            score = (score + data.financial_stability) / Decimal("2")
        if data.employer and data.employer.lower() not in ("unknown", ""):
            score += Decimal("5")
        return self._q(min(Decimal("100"), score))

    def _emi_burden(self, data: ExternalLeadAnalyticsInput) -> Decimal:
        monthly_income = data.estimated_income / Decimal("12")
        if monthly_income <= 0:
            return Decimal("0")
        burden = (data.monthly_emi / monthly_income) * Decimal("100")
        return self._q(min(Decimal("100"), burden))

    @staticmethod
    def _credit_quality_label(credit_score: int) -> str:
        if credit_score >= 780:
            return "Excellent"
        if credit_score >= 720:
            return "Very Good"
        if credit_score >= 680:
            return "Good"
        if credit_score >= 640:
            return "Fair"
        if credit_score >= 600:
            return "Average"
        return "Below Average"

    def _estimated_repayment_capacity(
        self, data: ExternalLeadAnalyticsInput, emi_burden: Decimal
    ) -> Decimal:
        monthly_income = data.estimated_income / Decimal("12")
        if monthly_income <= 0:
            return Decimal("0")
        max_emi_ratio = Decimal("0.45") if data.credit_score >= 700 else Decimal("0.35")
        available = monthly_income * max_emi_ratio
        remaining = available - data.monthly_emi
        return self._money(max(Decimal("0"), remaining))

    def _financial_capacity_score(
        self,
        data: ExternalLeadAnalyticsInput,
        income_stability: Decimal,
        emi_burden: Decimal,
        repayment_capacity: Decimal,
    ) -> Decimal:
        score = Decimal("20")
        income = data.estimated_income
        if income >= Decimal("2500000"):
            score += Decimal("25")
        elif income >= Decimal("1200000"):
            score += Decimal("18")
        elif income >= Decimal("600000"):
            score += Decimal("12")
        else:
            score += Decimal("6")

        if data.credit_score >= 750:
            score += Decimal("25")
        elif data.credit_score >= 680:
            score += Decimal("18")
        elif data.credit_score >= 620:
            score += Decimal("10")
        else:
            score += Decimal("4")

        score += income_stability * Decimal("0.20")

        if emi_burden < Decimal("20"):
            score += Decimal("15")
        elif emi_burden < Decimal("40"):
            score += Decimal("8")
        elif emi_burden >= Decimal("60"):
            score -= Decimal("10")

        monthly_income = income / Decimal("12") if income > 0 else Decimal("1")
        if repayment_capacity / monthly_income >= Decimal("0.15"):
            score += Decimal("10")

        return self._q(min(Decimal("100"), max(Decimal("0"), score)))

    @staticmethod
    def _affordability_level(financial_capacity_score: Decimal, emi_burden: Decimal) -> str:
        if financial_capacity_score >= Decimal("75") and emi_burden < Decimal("35"):
            return "High"
        if financial_capacity_score >= Decimal("55") and emi_burden < Decimal("50"):
            return "Medium"
        return "Low"
