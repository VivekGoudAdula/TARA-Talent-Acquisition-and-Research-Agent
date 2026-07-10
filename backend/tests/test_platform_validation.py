"""Unit tests for platform validation framework."""

import unittest
from unittest.mock import MagicMock

from app.platform_validation.check_result import ValidationCheck, overall_percentage, summarize_category
from app.platform_validation.database_validator import DatabaseValidator
from app.platform_validation.ml_validator import MLValidator


class CheckResultTests(unittest.TestCase):
    def test_overall_percentage(self) -> None:
        checks = [
            ValidationCheck("A", "one", "PASS", "ok"),
            ValidationCheck("A", "two", "FAIL", "bad"),
            ValidationCheck("A", "three", "SKIP", "skip"),
        ]
        self.assertEqual(overall_percentage(checks), "50%")

    def test_summarize_category_fail_priority(self) -> None:
        checks = [
            ValidationCheck("Database", "a", "PASS", "ok"),
            ValidationCheck("Database", "b", "FAIL", "bad"),
        ]
        summary = summarize_category("Database", checks)
        self.assertEqual(summary.status, "FAIL")
        self.assertEqual(summary.failed, 1)


class DatabaseValidatorTests(unittest.TestCase):
    def test_table_missing_fails(self) -> None:
        probe = MagicMock()
        probe.table_exists.return_value = False
        validator = DatabaseValidator(probe)
        checks = validator._validate_tables()
        self.assertTrue(all(c.status == "FAIL" for c in checks))


class MLValidatorTests(unittest.TestCase):
    def test_product_recommendation_catalog_check(self) -> None:
        probe = MagicMock()
        validator = MLValidator(probe)
        checks = validator._validate_product_recommendation()
        self.assertTrue(any(c.status == "PASS" for c in checks))


if __name__ == "__main__":
    unittest.main()
