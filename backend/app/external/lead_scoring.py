"""Deterministic lead scoring engine for external CRM leads."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.external.lead_enrichment import EnrichmentContext

PREMIUM_EMPLOYERS = frozenset(
    {
        "apollo hospitals",
        "tcs",
        "infosys",
        "wipro",
        "hdfc bank",
        "icici bank",
        "state govt",
        "central govt",
        "reliance",
        "tata",
        "amazon",
        "google",
        "microsoft",
    }
)

HIGH_VALUE_CAMPAIGNS = frozenset(
    {
        "premium banking",
        "wealth management",
        "salary account",
        "digital lending",
        "home loan",
    }
)

OCCUPATION_SCORES: dict[str, Decimal] = {
    "Doctor": Decimal("15"),
    "Chartered Accountant": Decimal("14"),
    "Software Engineer": Decimal("13"),
    "Government Employee": Decimal("12"),
    "Lawyer": Decimal("12"),
    "Professor": Decimal("11"),
    "Business Owner": Decimal("10"),
    "Teacher": Decimal("9"),
    "Nurse": Decimal("8"),
    "Sales Executive": Decimal("7"),
    "Police Officer": Decimal("7"),
    "Farmer": Decimal("5"),
    "Student": Decimal("4"),
    "Retired": Decimal("6"),
}


@dataclass(frozen=True)
class LeadScoreResult:
    """Composite lead score with factor breakdown."""

    lead_score: Decimal
    income_factor: Decimal
    credit_factor: Decimal
    occupation_factor: Decimal
    employer_factor: Decimal
    campaign_factor: Decimal
    consent_factor: Decimal
    relationship_factor: Decimal
    stability_factor: Decimal


class LeadScoringEngine:
    """
    Calculates a composite lead score (0–100) from deterministic business rules.

    Factors: income, credit score, occupation, employer, campaign, consent,
    relationship potential, and financial stability.
    """

    def calculate(self, ctx: EnrichmentContext) -> LeadScoreResult:
        income_factor = self._income_score(ctx.estimated_income)
        credit_factor = self._credit_score(ctx.credit_score)
        occupation_factor = OCCUPATION_SCORES.get(ctx.occupation, Decimal("6"))
        employer_factor = self._employer_score(ctx.employer)
        campaign_factor = self._campaign_score(ctx.campaign)
        consent_factor = Decimal("5") if ctx.consent else Decimal("0")
        relationship_factor = (ctx.relationship_potential / Decimal("10")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        stability_factor = (ctx.financial_stability / Decimal("20")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        raw = (
            income_factor
            + credit_factor
            + occupation_factor
            + employer_factor
            + campaign_factor
            + consent_factor
            + relationship_factor
            + stability_factor
        )
        lead_score = min(Decimal("100"), raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return LeadScoreResult(
            lead_score=lead_score,
            income_factor=income_factor,
            credit_factor=credit_factor,
            occupation_factor=occupation_factor,
            employer_factor=employer_factor,
            campaign_factor=campaign_factor,
            consent_factor=consent_factor,
            relationship_factor=relationship_factor,
            stability_factor=stability_factor,
        )

    @staticmethod
    def _income_score(income: Decimal) -> Decimal:
        if income >= Decimal("5000000"):
            return Decimal("25")
        if income >= Decimal("2500000"):
            return Decimal("22")
        if income >= Decimal("1500000"):
            return Decimal("18")
        if income >= Decimal("800000"):
            return Decimal("14")
        if income >= Decimal("400000"):
            return Decimal("10")
        return Decimal("6")

    @staticmethod
    def _credit_score(score: int) -> Decimal:
        if score >= 780:
            return Decimal("20")
        if score >= 720:
            return Decimal("17")
        if score >= 680:
            return Decimal("14")
        if score >= 640:
            return Decimal("10")
        if score >= 600:
            return Decimal("6")
        return Decimal("3")

    @staticmethod
    def _employer_score(employer: str) -> Decimal:
        key = employer.strip().lower()
        for premium in PREMIUM_EMPLOYERS:
            if premium in key:
                return Decimal("10")
        if key and key != "unknown":
            return Decimal("6")
        return Decimal("3")

    @staticmethod
    def _campaign_score(campaign: str) -> Decimal:
        key = campaign.strip().lower()
        for high_value in HIGH_VALUE_CAMPAIGNS:
            if high_value in key:
                return Decimal("10")
        return Decimal("5")
