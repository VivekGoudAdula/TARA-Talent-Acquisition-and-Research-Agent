"""Unit tests for external lead intelligence validation engines."""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.external.intelligence.fraud_screening_engine import FraudScreeningEngine
from app.external.intelligence.income_confidence_engine import IncomeConfidenceEngine
from app.external.intelligence.kyc_readiness_engine import KycReadinessEngine
from app.external.intelligence.lead_authenticity_engine import LeadAuthenticityEngine
from app.schemas.external_intelligence_validation import ExternalLeadIntelligenceInput


def _sample_input(**overrides) -> ExternalLeadIntelligenceInput:
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
        referral_source="Branch Referral",
        campaign="Digital Lending",
        consent=True,
        lead_created_date=date(2024, 6, 15),
        income_segment="Affluent",
        monthly_emi=Decimal("15000"),
        duplicate_phone=False,
        duplicate_email=False,
        duplicate_lead_reference=False,
    )
    base.update(overrides)
    return ExternalLeadIntelligenceInput(**base)


class LeadAuthenticityEngineTests(unittest.TestCase):
    def test_high_authenticity_complete_lead(self) -> None:
        result = LeadAuthenticityEngine().calculate(_sample_input())
        self.assertGreaterEqual(result.lead_authenticity_score, Decimal("80"))
        self.assertGreater(len(result.reason_codes), 0)

    def test_low_authenticity_sparse_lead(self) -> None:
        result = LeadAuthenticityEngine().calculate(
            _sample_input(
                phone_number="invalid",
                email="bad",
                employer="Unknown",
                occupation="Unknown",
                consent=False,
                city="Unknown",
            )
        )
        self.assertLess(result.lead_authenticity_score, Decimal("50"))


class IncomeConfidenceEngineTests(unittest.TestCase):
    def test_consistent_income_high_confidence(self) -> None:
        result = IncomeConfidenceEngine().calculate(_sample_input())
        self.assertGreater(result.income_confidence_score, Decimal("50"))
        self.assertIn(result.income_confidence_level, ("High", "Medium", "Low"))


class FraudScreeningEngineTests(unittest.TestCase):
    def test_clean_lead_low_fraud(self) -> None:
        result = FraudScreeningEngine().calculate(_sample_input())
        self.assertEqual(result.fraud_risk, "Low")
        self.assertLess(result.fraud_score, Decimal("20"))

    def test_duplicate_phone_high_risk(self) -> None:
        result = FraudScreeningEngine().calculate(_sample_input(duplicate_phone=True))
        self.assertGreater(result.fraud_score, Decimal("20"))
        self.assertIn("Duplicate phone", result.fraud_reason_codes[0])


class KycReadinessEngineTests(unittest.TestCase):
    def test_ready_lead(self) -> None:
        result = KycReadinessEngine().calculate(_sample_input())
        self.assertEqual(result.kyc_readiness, "Ready")
        self.assertEqual(result.kyc_missing_items, [])

    def test_not_ready_without_consent(self) -> None:
        result = KycReadinessEngine().calculate(
            _sample_input(consent=False, phone_number="", email="")
        )
        self.assertIn(result.kyc_readiness, ("Not Ready", "Partially Ready"))


if __name__ == "__main__":
    unittest.main()
