"""Deterministic lead enrichment and segmentation engine."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.external.excel_importer import ImportedLeadRow

INDIAN_BANKS = (
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Kotak Mahindra",
    "SBI",
    "PNB",
    "Bank of Baroda",
    "Yes Bank",
    "IndusInd Bank",
)

PRODUCT_OPTIONS = (
    "Savings Account",
    "Salary Account",
    "Credit Card",
    "Personal Loan",
    "Home Loan",
    "Car Loan",
    "Fixed Deposit",
)

PERSONAS = (
    "High Net Worth",
    "Salary Elite",
    "Premium",
    "Business Owner",
    "Young Professional",
    "Family",
    "Student",
    "Retired",
    "Mass Market",
)


@dataclass(frozen=True)
class EnrichmentContext:
    """Input context for scoring and enrichment engines."""

    external_reference: str
    full_name: str
    age: int
    gender: str
    occupation: str
    employer: str
    estimated_income: Decimal
    credit_score: int
    city: str
    state: str
    referral_source: str
    campaign: str
    consent: bool
    preferred_language: str
    relationship_potential: Decimal = Decimal("0")
    financial_stability: Decimal = Decimal("0")


@dataclass(frozen=True)
class EnrichedLeadProfile:
    """Complete enriched profile for an external lead."""

    income_segment: str
    occupation_segment: str
    customer_persona: str
    relationship_potential: Decimal
    financial_stability: Decimal
    digital_adoption: Decimal
    preferred_channel: str
    preferred_contact_time: str
    cross_sell_potential: Decimal
    lead_score: Decimal
    existing_bank: str
    existing_products: str
    monthly_emi: Decimal
    home_owner: bool
    preferred_language: str


class LeadEnrichmentEngine:
    """
    Enriches external leads with synthetic enterprise CRM fields
    using deterministic, explainable business rules.
    """

    def enrich(self, lead: ImportedLeadRow) -> EnrichedLeadProfile:
        ctx = EnrichmentContext(
            external_reference=lead.external_reference,
            full_name=lead.full_name,
            age=lead.age,
            gender=lead.gender,
            occupation=lead.occupation,
            employer=lead.employer,
            estimated_income=lead.estimated_income,
            credit_score=lead.credit_score,
            city=lead.city,
            state=lead.state,
            referral_source=lead.referral_source,
            campaign=lead.campaign,
            consent=lead.consent,
            preferred_language=lead.preferred_language,
        )

        income_segment = self._income_segment(lead.estimated_income)
        occupation_segment = self._occupation_segment(lead.occupation)
        relationship_potential = self._relationship_potential(ctx)
        financial_stability = self._financial_stability(ctx)
        digital_adoption = self._digital_adoption(ctx)
        cross_sell_potential = self._cross_sell_potential(ctx, relationship_potential)
        existing_bank = self._existing_bank(lead.external_reference)
        existing_products = self._existing_products(lead.external_reference, lead.estimated_income)
        monthly_emi = self._monthly_emi(lead.estimated_income, existing_products)
        home_owner = self._home_owner(lead.age, lead.estimated_income, lead.occupation)
        preferred_channel = self._preferred_channel(digital_adoption, lead.consent)
        preferred_contact_time = self._preferred_contact_time(lead.occupation)
        customer_persona = self._segment_persona(lead, income_segment, occupation_segment)

        # Lead score computed in LeadScoringEngine after enrichment factors are known
        enriched_ctx = EnrichmentContext(
            external_reference=ctx.external_reference,
            full_name=ctx.full_name,
            age=ctx.age,
            gender=ctx.gender,
            occupation=ctx.occupation,
            employer=ctx.employer,
            estimated_income=ctx.estimated_income,
            credit_score=ctx.credit_score,
            city=ctx.city,
            state=ctx.state,
            referral_source=ctx.referral_source,
            campaign=ctx.campaign,
            consent=ctx.consent,
            preferred_language=ctx.preferred_language,
            relationship_potential=relationship_potential,
            financial_stability=financial_stability,
        )

        from app.external.lead_scoring import LeadScoringEngine

        score_result = LeadScoringEngine().calculate(enriched_ctx)

        return EnrichedLeadProfile(
            income_segment=income_segment,
            occupation_segment=occupation_segment,
            customer_persona=customer_persona,
            relationship_potential=relationship_potential,
            financial_stability=financial_stability,
            digital_adoption=digital_adoption,
            preferred_channel=preferred_channel,
            preferred_contact_time=preferred_contact_time,
            cross_sell_potential=cross_sell_potential,
            lead_score=score_result.lead_score,
            existing_bank=existing_bank,
            existing_products=existing_products,
            monthly_emi=monthly_emi,
            home_owner=home_owner,
            preferred_language=lead.preferred_language,
        )

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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

    def _occupation_segment(self, occupation: str) -> str:
        professional = {
            "Doctor",
            "Lawyer",
            "Chartered Accountant",
            "Professor",
            "Software Engineer",
        }
        service = {"Teacher", "Nurse", "Police Officer", "Sales Executive", "Government Employee"}
        if occupation in professional:
            return "Professional"
        if occupation == "Business Owner":
            return "Self Employed"
        if occupation == "Student":
            return "Student"
        if occupation == "Retired":
            return "Retired"
        if occupation in service:
            return "Service Sector"
        if occupation == "Farmer":
            return "Agriculture"
        return "General"

    def _relationship_potential(self, ctx: EnrichmentContext) -> Decimal:
        score = Decimal("40")
        if ctx.estimated_income >= Decimal("2500000"):
            score += Decimal("20")
        elif ctx.estimated_income >= Decimal("1000000"):
            score += Decimal("12")
        if ctx.credit_score >= 720:
            score += Decimal("15")
        elif ctx.credit_score >= 650:
            score += Decimal("8")
        if ctx.referral_source.lower() in ("existing customer", "branch referral"):
            score += Decimal("15")
        elif "referral" in ctx.referral_source.lower():
            score += Decimal("8")
        if ctx.consent:
            score += Decimal("10")
        return self._quantize(min(Decimal("100"), score))

    def _financial_stability(self, ctx: EnrichmentContext) -> Decimal:
        score = Decimal("30")
        if ctx.credit_score >= 750:
            score += Decimal("35")
        elif ctx.credit_score >= 680:
            score += Decimal("25")
        elif ctx.credit_score >= 620:
            score += Decimal("15")
        income = ctx.estimated_income
        if income >= Decimal("2000000"):
            score += Decimal("20")
        elif income >= Decimal("800000"):
            score += Decimal("12")
        stable_occupations = {"Government Employee", "Doctor", "Professor", "Chartered Accountant"}
        if ctx.occupation in stable_occupations:
            score += Decimal("15")
        return self._quantize(min(Decimal("100"), score))

    def _digital_adoption(self, ctx: EnrichmentContext) -> Decimal:
        score = Decimal("35")
        digital_campaigns = ("digital", "online", "app", "mobile")
        if any(k in ctx.campaign.lower() for k in digital_campaigns):
            score += Decimal("25")
        if ctx.age < 40:
            score += Decimal("20")
        elif ctx.age < 55:
            score += Decimal("10")
        tech_occupations = {"Software Engineer", "Chartered Accountant", "Sales Executive"}
        if ctx.occupation in tech_occupations:
            score += Decimal("15")
        return self._quantize(min(Decimal("100"), score))

    def _cross_sell_potential(
        self, ctx: EnrichmentContext, relationship_potential: Decimal
    ) -> Decimal:
        base = relationship_potential * Decimal("0.6")
        if ctx.estimated_income >= Decimal("1500000"):
            base += Decimal("15")
        if "loan" in ctx.campaign.lower() or "card" in ctx.campaign.lower():
            base += Decimal("10")
        return self._quantize(min(Decimal("100"), base))

    @staticmethod
    def _existing_bank(external_ref: str) -> str:
        idx = int(hashlib.md5(external_ref.encode()).hexdigest()[:2], 16) % len(INDIAN_BANKS)
        return INDIAN_BANKS[idx]

    @staticmethod
    def _existing_products(external_ref: str, income: Decimal) -> str:
        digest = hashlib.md5(f"products:{external_ref}".encode()).hexdigest()
        count = 1 + int(digest[0], 16) % 3
        if income >= Decimal("2500000"):
            count = min(4, count + 1)
        selected: list[str] = []
        for i in range(count):
            idx = int(digest[i * 2 : i * 2 + 2], 16) % len(PRODUCT_OPTIONS)
            product = PRODUCT_OPTIONS[idx]
            if product not in selected:
                selected.append(product)
        return ", ".join(selected) if selected else "Savings Account"

    @staticmethod
    def _monthly_emi(income: Decimal, existing_products: str) -> Decimal:
        annual = income
        monthly_income = annual / Decimal("12")
        burden = Decimal("0")
        if "Home Loan" in existing_products:
            burden += Decimal("0.35")
        if "Car Loan" in existing_products:
            burden += Decimal("0.12")
        if "Personal Loan" in existing_products:
            burden += Decimal("0.08")
        emi = (monthly_income * burden).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return emi

    @staticmethod
    def _home_owner(age: int, income: Decimal, occupation: str) -> bool:
        if age < 28:
            return False
        if income >= Decimal("1200000"):
            return True
        if occupation in ("Government Employee", "Doctor", "Business Owner") and age >= 35:
            return True
        return age >= 45 and income >= Decimal("600000")

    @staticmethod
    def _preferred_channel(digital_adoption: Decimal, consent: bool) -> str:
        if not consent:
            return "Branch"
        if digital_adoption >= Decimal("70"):
            return "Mobile App"
        if digital_adoption >= Decimal("50"):
            return "WhatsApp"
        if digital_adoption >= Decimal("35"):
            return "Email"
        return "Phone"

    @staticmethod
    def _preferred_contact_time(occupation: str) -> str:
        if occupation in ("Doctor", "Nurse", "Police Officer"):
            return "Evening (18:00–20:00)"
        if occupation == "Business Owner":
            return "Late Morning (11:00–13:00)"
        if occupation in ("Student", "Retired"):
            return "Afternoon (14:00–16:00)"
        return "Morning (10:00–12:00)"

    def _segment_persona(
        self, lead: ImportedLeadRow, income_segment: str, occupation_segment: str
    ) -> str:
        income = lead.estimated_income
        age = lead.age
        occupation = lead.occupation

        if income >= Decimal("5000000") and lead.credit_score >= 750:
            return "High Net Worth"
        if (
            income >= Decimal("2500000")
            and occupation in ("Software Engineer", "Government Employee", "Doctor")
            and lead.credit_score >= 700
        ):
            return "Salary Elite"
        if income >= Decimal("2000000") or lead.credit_score >= 720:
            return "Premium"
        if occupation == "Business Owner":
            return "Business Owner"
        if occupation == "Student" or age < 24:
            return "Student"
        if occupation == "Retired" or age >= 60:
            return "Retired"
        if 22 <= age <= 35 and Decimal("500000") <= income < Decimal("2000000"):
            return "Young Professional"
        if 30 <= age <= 50 and income >= Decimal("1000000"):
            return "Family"
        if income_segment == "Mass Market" or income < Decimal("500000"):
            return "Mass Market"
        return "Mass Market"
