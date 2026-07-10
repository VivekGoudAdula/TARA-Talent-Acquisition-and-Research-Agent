"""Unit tests for Lead Conversion Prediction."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.ml.conversion.service import lead_priority, marketing_priority
from app.ml.conversion.training import (
    ConversionModelRegistry,
    ConversionTrainer,
    categorize_lead_source,
    evaluate_regression,
    label_conversion_probability,
)


class ConversionLabelingTests(unittest.TestCase):
    def test_high_quality_lead_high_probability(self) -> None:
        row = {
            "lead_quality_score": 85.0,
            "behaviour_score": 80.0,
            "digital_engagement_score": 75.0,
            "communication_readiness": 78.0,
            "previous_campaign_response": 70.0,
            "credit_score": 750,
            "estimated_income": 1200000.0,
            "consent": 1,
            "lead_source": "Referral",
        }
        prob = label_conversion_probability(row)
        self.assertGreaterEqual(prob, 70.0)

    def test_no_consent_reduces_probability(self) -> None:
        base = {
            "lead_quality_score": 80.0,
            "behaviour_score": 75.0,
            "digital_engagement_score": 70.0,
            "communication_readiness": 72.0,
            "previous_campaign_response": 65.0,
            "credit_score": 720,
            "estimated_income": 900000.0,
            "consent": 1,
            "lead_source": "Digital",
        }
        with_consent = label_conversion_probability(base)
        without = label_conversion_probability({**base, "consent": 0})
        self.assertLess(without, with_consent)

    def test_categorize_lead_source(self) -> None:
        self.assertEqual(categorize_lead_source("Branch Referral"), "Referral")
        self.assertEqual(categorize_lead_source("Website"), "Digital")
        self.assertEqual(categorize_lead_source("Cold Call"), "Cold Outreach")


class ConversionTrainerTests(unittest.TestCase):
    def _sample_df(self, n: int = 80) -> pd.DataFrame:
        rows = []
        for i in range(n):
            consent = 1 if i % 3 != 0 else 0
            row = {
                "lead_source": ["Referral", "Digital", "Direct", "Cold Outreach"][i % 4],
                "campaign": f"Campaign {i % 5}",
                "referral_source": f"Source {i % 6}",
                "occupation": f"Role {i % 4}",
                "employer": f"Employer {i % 7}",
                "estimated_income": 300000 + (i * 15000),
                "credit_score": 600 + (i % 200),
                "lead_quality_score": 40 + (i % 50),
                "behaviour_score": 35 + (i % 55),
                "digital_engagement_score": 30 + (i % 60),
                "consent": consent,
                "previous_campaign_response": 25 + (i % 65),
                "communication_readiness": 30 + (i % 60),
            }
            row["conversion_probability"] = label_conversion_probability(row)
            rows.append(row)
        return pd.DataFrame(rows)

    def test_train_selects_best_model(self) -> None:
        result = ConversionTrainer().train(self._sample_df())
        self.assertIn(result.best_model_name, {"random_forest", "xgboost", "lightgbm"})
        self.assertIn("mae", result.test_metrics)
        self.assertIn("r2", result.test_metrics)
        self.assertIsInstance(result.feature_importance, dict)


class ConversionPriorityTests(unittest.TestCase):
    def test_priority_tiers(self) -> None:
        self.assertEqual(lead_priority(80.0), "High")
        self.assertEqual(lead_priority(60.0), "Medium")
        self.assertEqual(lead_priority(30.0), "Low")
        self.assertEqual(marketing_priority(80.0, True), "High")
        self.assertEqual(marketing_priority(80.0, False), "Medium")


class ConversionRegistryTests(unittest.TestCase):
    def test_save_and_load(self) -> None:
        df = ConversionTrainerTests()._sample_df()
        result = ConversionTrainer().train(df)
        with tempfile.TemporaryDirectory() as tmp:
            registry = ConversionModelRegistry(
                models_dir=Path(tmp),
                model_path=Path(tmp) / "best_conversion_model.pkl",
                metrics_path=Path(tmp) / "conversion_metrics.json",
                feature_importance_path=Path(tmp) / "conversion_feature_importance.json",
            )
            registry.save_model(result.pipeline, {"best_model": result.best_model_name})
            registry.save_metrics(result.test_metrics)
            registry.save_feature_importance(result.feature_importance)
            self.assertTrue(registry.model_exists())
            artifact = registry.load_model()
            self.assertIn("pipeline", artifact)


if __name__ == "__main__":
    unittest.main()
