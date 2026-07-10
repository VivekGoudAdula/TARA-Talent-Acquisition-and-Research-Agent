"""Unit tests for external lead enrichment and scoring engines."""

import unittest
from decimal import Decimal

from app.external.excel_importer import ExcelImporter, ImportedLeadRow
from app.external.lead_enrichment import LeadEnrichmentEngine
from app.external.lead_scoring import LeadScoringEngine
from datetime import date, datetime
from uuid import uuid4


def _sample_row(**overrides) -> ImportedLeadRow:
    base = dict(
        lead_id=uuid4(),
        external_reference="LEAD200001",
        full_name="Ananya Patel",
        phone_number="+919876543210",
        email="ananya.lead001@leads.tara.bank",
        age=32,
        gender="Female",
        occupation="Government Employee",
        employer="State Govt",
        estimated_income=Decimal("1355000"),
        credit_score=591,
        city="Mumbai",
        state="Maharashtra",
        preferred_language="Marathi",
        referral_source="Branch Referral",
        campaign="Digital Lending",
        lead_status="NEW",
        consent=True,
        lead_created_date=date(2024, 6, 15),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    base.update(overrides)
    return ImportedLeadRow(**base)


class LeadEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = LeadEnrichmentEngine()

    def test_enrichment_produces_all_fields(self) -> None:
        profile = self.engine.enrich(_sample_row())
        self.assertIsNotNone(profile.income_segment)
        self.assertIsNotNone(profile.customer_persona)
        self.assertGreater(profile.lead_score, Decimal("0"))
        self.assertLessEqual(profile.lead_score, Decimal("100"))
        self.assertIn(profile.preferred_channel, ("Mobile App", "WhatsApp", "Email", "Phone", "Branch"))

    def test_high_income_persona(self) -> None:
        profile = self.engine.enrich(
            _sample_row(estimated_income=Decimal("6000000"), credit_score=780, occupation="Doctor")
        )
        self.assertIn(profile.customer_persona, ("High Net Worth", "Premium", "Salary Elite"))

    def test_student_persona(self) -> None:
        profile = self.engine.enrich(_sample_row(occupation="Student", age=20, estimated_income=Decimal("200000")))
        self.assertEqual(profile.customer_persona, "Student")


class LeadScoringTests(unittest.TestCase):
    def test_score_within_range(self) -> None:
        enriched = LeadEnrichmentEngine().enrich(_sample_row())
        self.assertGreaterEqual(enriched.lead_score, Decimal("0"))
        self.assertLessEqual(enriched.lead_score, Decimal("100"))

    def test_consent_increases_score(self) -> None:
        with_consent = LeadEnrichmentEngine().enrich(_sample_row(consent=True))
        without_consent = LeadEnrichmentEngine().enrich(_sample_row(consent=False))
        self.assertGreater(with_consent.lead_score, without_consent.lead_score)


class ExcelImporterTests(unittest.TestCase):
    def test_normalize_occupation(self) -> None:
        self.assertEqual(ExcelImporter._normalize_occupation("govt employee"), "Government Employee")

    def test_normalize_phone_format(self) -> None:
        phone = ExcelImporter._normalize_phone("LEAD200001")
        self.assertTrue(phone.startswith("+91"))
        self.assertEqual(len(phone), 13)


if __name__ == "__main__":
    unittest.main()
