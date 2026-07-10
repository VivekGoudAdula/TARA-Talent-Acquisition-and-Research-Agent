"""Unit tests for ML Dataset Builder."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.ml.dataset_builder.dataset_exporter import DatasetExporter
from app.ml.dataset_builder.dataset_generator import (
    TARGET_HIGH,
    TARGET_LOW,
    TARGET_MEDIUM,
    TARGET_VERY_HIGH,
    DatasetGenerator,
    DatasetRow,
    PROFILE_INTERNAL,
)
from app.ml.dataset_builder.dataset_validator import DatasetValidator


def _sample_row(**overrides) -> DatasetRow:
    base = dict(
        record_id=uuid4(),
        profile_type=PROFILE_INTERNAL,
        profile_id=uuid4(),
        age=35,
        income=Decimal("120000"),
        credit_score=780,
        financial_health_score=Decimal("85"),
        repayment_behaviour_score=Decimal("80"),
        digital_engagement_score=Decimal("75"),
        financial_capacity_score=None,
        lead_score=None,
        lead_quality_score=None,
        lead_authenticity_score=None,
        income_confidence_score=None,
        relationship_score=Decimal("70"),
        savings_ratio=Decimal("40"),
        emi_burden=Decimal("15"),
        cash_flow_score=Decimal("72"),
        digital_adoption_score=Decimal("68"),
        customer_value_score=Decimal("60"),
        occupation="Engineer",
        employment_type=None,
        city="Mumbai",
        target_repayment_capacity=TARGET_LOW,
        created_at=datetime.utcnow(),
    )
    base.update(overrides)
    return DatasetRow(**base)


class DatasetGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = DatasetGenerator()

    def test_very_high_target_label(self) -> None:
        row = _sample_row()
        labeled = self.generator.assign_targets([row])[0]
        self.assertEqual(labeled.target_repayment_capacity, TARGET_VERY_HIGH)

    def test_low_target_when_income_weak(self) -> None:
        row = _sample_row(income=Decimal("30000"), credit_score=600, savings_ratio=Decimal("5"))
        labeled = self.generator.assign_targets([row])[0]
        self.assertEqual(labeled.target_repayment_capacity, TARGET_LOW)

    def test_high_target_tier(self) -> None:
        row = _sample_row(
            income=Decimal("80000"),
            credit_score=720,
            savings_ratio=Decimal("28"),
            emi_burden=Decimal("25"),
        )
        labeled = self.generator.assign_targets([row])[0]
        self.assertEqual(labeled.target_repayment_capacity, TARGET_HIGH)

    def test_medium_target_tier(self) -> None:
        row = _sample_row(
            income=Decimal("50000"),
            credit_score=680,
            savings_ratio=Decimal("10"),
            emi_burden=Decimal("35"),
            financial_health_score=Decimal("65"),
        )
        labeled = self.generator.assign_targets([row])[0]
        self.assertEqual(labeled.target_repayment_capacity, TARGET_MEDIUM)


class DatasetValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = DatasetValidator()

    def test_removes_duplicate_profiles(self) -> None:
        profile_id = uuid4()
        rows = [
            _sample_row(profile_id=profile_id, income=Decimal("50000")),
            _sample_row(profile_id=profile_id, income=Decimal("90000")),
        ]
        cleaned, report = self.validator.validate_and_clean(rows)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(report.duplicates_removed, 1)
        self.assertEqual(cleaned[0].income, Decimal("90000"))

    def test_clips_score_columns(self) -> None:
        row = _sample_row(financial_health_score=Decimal("150"))
        cleaned, _ = self.validator.validate_and_clean([row])
        self.assertEqual(cleaned[0].financial_health_score, Decimal("100"))


class DatasetExporterTests(unittest.TestCase):
    def test_export_csv_and_parquet(self) -> None:
        import tempfile
        from pathlib import Path

        validator = DatasetValidator()
        row = _sample_row()
        labeled = DatasetGenerator().assign_targets([row])[0]
        df = validator.rows_to_dataframe([labeled])

        with tempfile.TemporaryDirectory() as tmp:
            exporter = DatasetExporter(output_dir=Path(tmp))
            result = exporter.export(df)
            self.assertTrue(Path(result["csv_path"]).exists())
            self.assertTrue(Path(result["parquet_path"]).exists())
            self.assertEqual(result["record_count"], "1")


if __name__ == "__main__":
    unittest.main()
