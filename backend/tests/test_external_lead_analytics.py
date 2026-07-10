"""Unit tests for external lead analytics engines."""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.external.analytics.financial_capacity_analytics import FinancialCapacityAnalytics
from app.external.analytics.lead_behaviour_analytics import LeadBehaviourAnalytics
from app.external.analytics.lead_quality_analytics import LeadQualityAnalytics
from app.schemas.external_analytics_input import ExternalLeadAnalyticsInput


def _sample_input(**overrides) -> ExternalLeadAnalyticsInput:
    base = dict(
        lead_id=uuid4(),
        external_reference="LEAD200001",
        full_name="Ananya Patel",
        phone_number="+919876543210",
        email="ananya@leads.tara.bank",
        age=32,
        gender="Female",
        occupation="Government Employee",
        employer="State Govt",
        estimated_income=Decimal("2500000"),
        credit_score=720,
        city="Mumbai",
        state="Maharashtra",
        preferred_language="Marathi",
        referral_source="Branch Referral",
        campaign="Digital Lending",
        consent=True,
        lead_status="ENRICHED",
        lead_created_date=date(2024, 6, 15),
        income_segment="Affluent",
        customer_persona="Salary Elite",
        relationship_potential=Decimal("75"),
        financial_stability=Decimal("80"),
        digital_adoption=Decimal("70"),
        preferred_channel="WhatsApp",
        preferred_contact_time="Morning (10:00–12:00)",
        cross_sell_potential=Decimal("60"),
        lead_score=Decimal("82"),
        existing_bank="HDFC Bank",
        existing_products="Savings Account, Credit Card",
        monthly_emi=Decimal("15000"),
        home_owner=True,
    )
    base.update(overrides)
    return ExternalLeadAnalyticsInput(**base)


class LeadBehaviourAnalyticsTests(unittest.TestCase):
    def test_scores_in_valid_range(self) -> None:
        result = LeadBehaviourAnalytics().calculate(_sample_input())
        for field in (
            "campaign_engagement_score",
            "referral_quality_score",
            "digital_readiness_score",
            "communication_readiness_score",
            "marketing_responsiveness_score",
            "customer_persona_confidence",
        ):
            value = getattr(result, field)
            self.assertGreaterEqual(value, Decimal("0"))
            self.assertLessEqual(value, Decimal("100"))

    def test_no_consent_reduces_strength(self) -> None:
        with_consent = LeadBehaviourAnalytics().calculate(_sample_input(consent=True))
        without = LeadBehaviourAnalytics().calculate(_sample_input(consent=False))
        self.assertGreater(with_consent.consent_strength, without.consent_strength)


class FinancialCapacityAnalyticsTests(unittest.TestCase):
    def test_high_income_affordability(self) -> None:
        result = FinancialCapacityAnalytics().calculate(_sample_input())
        self.assertGreater(result.financial_capacity_score, Decimal("50"))
        self.assertGreater(result.estimated_repayment_capacity, Decimal("0"))
        self.assertIn(result.affordability_level, ("High", "Medium", "Low"))

    def test_credit_quality_label(self) -> None:
        result = FinancialCapacityAnalytics().calculate(_sample_input(credit_score=780))
        self.assertEqual(result.credit_quality, "Excellent")


class LeadQualityAnalyticsTests(unittest.TestCase):
    def test_qualified_lead(self) -> None:
        behaviour = LeadBehaviourAnalytics().calculate(_sample_input())
        financial = FinancialCapacityAnalytics().calculate(_sample_input())
        quality = LeadQualityAnalytics().calculate(_sample_input(), behaviour, financial)
        self.assertGreater(quality.lead_quality_score, Decimal("60"))
        self.assertIn(quality.qualification_status, ("Qualified", "Partially Qualified", "Not Qualified"))
        self.assertIn(quality.priority_level, ("High", "Medium", "Low"))


if __name__ == "__main__":
    unittest.main()
