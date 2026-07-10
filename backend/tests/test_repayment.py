"""Unit tests for Repayment Capacity Prediction."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from app.ml.dataset_builder.dataset_generator import (
    TARGET_HIGH,
    TARGET_LOW,
    TARGET_MEDIUM,
    TARGET_VERY_HIGH,
    DatasetGenerator,
)
from app.ml.dataset_builder.dataset_validator import DatasetValidator
from app.ml.repayment.evaluation import TARGET_ORDER, evaluate_multiclass
from app.ml.repayment.registry import RepaymentModelRegistry
from app.ml.repayment.training import RepaymentTrainer
from tests.test_ml_dataset import _sample_row


class RepaymentEvaluationTests(unittest.TestCase):
    def test_evaluate_multiclass_metrics(self) -> None:
        y_true = [TARGET_LOW, TARGET_HIGH, TARGET_MEDIUM, TARGET_VERY_HIGH]
        y_pred = [TARGET_LOW, TARGET_HIGH, TARGET_MEDIUM, TARGET_LOW]
        import numpy as np

        y_proba = np.array(
            [
                [0.7, 0.1, 0.1, 0.1],
                [0.1, 0.7, 0.1, 0.1],
                [0.1, 0.1, 0.7, 0.1],
                [0.5, 0.2, 0.2, 0.1],
            ]
        )
        metrics = evaluate_multiclass(y_true, y_pred, y_proba, labels=TARGET_ORDER)
        self.assertIn("accuracy", metrics)
        self.assertIn("f1_macro", metrics)
        self.assertIn("confusion_matrix", metrics)
        self.assertEqual(len(metrics["confusion_matrix"]), 4)


class RepaymentTrainerTests(unittest.TestCase):
    def test_train_selects_best_model(self) -> None:
        generator = DatasetGenerator()
        validator = DatasetValidator()
        rows = []
        for income, credit, savings, emi, expected in [
            (Decimal("120000"), 780, Decimal("40"), Decimal("15"), TARGET_VERY_HIGH),
            (Decimal("80000"), 720, Decimal("28"), Decimal("25"), TARGET_HIGH),
            (Decimal("50000"), 680, Decimal("10"), Decimal("35"), TARGET_MEDIUM),
            (Decimal("30000"), 600, Decimal("5"), Decimal("50"), TARGET_LOW),
        ]:
            for _ in range(15):
                row = _sample_row(
                    income=income,
                    credit_score=credit,
                    savings_ratio=savings,
                    emi_burden=emi,
                )
                rows.append(row)

        labeled = generator.assign_targets(rows)
        df = validator.rows_to_dataframe(labeled)
        result = RepaymentTrainer().train(df)

        self.assertIn(result.best_model_name, {"random_forest", "xgboost", "lightgbm"})
        self.assertGreater(result.records_used, 0)
        self.assertIn("accuracy", result.test_metrics)
        self.assertIn("f1_macro", result.test_metrics)
        self.assertIsInstance(result.feature_importance, dict)


class RepaymentRegistryTests(unittest.TestCase):
    def test_save_and_load_artifacts(self) -> None:
        generator = DatasetGenerator()
        validator = DatasetValidator()
        rows = []
        for income, credit, savings, emi in [
            (Decimal("120000"), 780, Decimal("40"), Decimal("15")),
            (Decimal("80000"), 720, Decimal("28"), Decimal("25")),
            (Decimal("50000"), 680, Decimal("10"), Decimal("35")),
            (Decimal("30000"), 600, Decimal("5"), Decimal("50")),
        ]:
            for _ in range(15):
                rows.append(
                    _sample_row(
                        income=income,
                        credit_score=credit,
                        savings_ratio=savings,
                        emi_burden=emi,
                    )
                )
        labeled = generator.assign_targets(rows)
        df = validator.rows_to_dataframe(labeled)
        result = RepaymentTrainer().train(df)

        with tempfile.TemporaryDirectory() as tmp:
            registry = RepaymentModelRegistry(models_dir=Path(tmp))
            registry.save_model(
                result.pipeline,
                {"best_model": result.best_model_name},
                label_encoder=result.label_encoder,
            )
            registry.save_metrics({"f1_macro": result.test_metrics["f1_macro"]})
            registry.save_feature_importance(result.feature_importance)

            self.assertTrue(registry.model_exists())
            artifact = registry.load_model()
            self.assertIn("pipeline", artifact)
            self.assertIsNotNone(registry.load_metrics())
            self.assertIsNotNone(registry.load_feature_importance())


if __name__ == "__main__":
    unittest.main()
