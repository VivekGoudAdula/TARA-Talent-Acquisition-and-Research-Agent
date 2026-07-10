"""Integration tests for Repayment Capacity Prediction API."""

import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.ml.repayment.registry import MODELS_DIR
from db_env import load_db_env

load_db_env()


class RepaymentAPITests(unittest.TestCase):
    def setUp(self) -> None:
        if MODELS_DIR.exists():
            shutil.rmtree(MODELS_DIR)

    def test_repayment_train_predict_model_info(self) -> None:
        with TestClient(app) as client:
            build = client.post("/api/ml/dataset/build")
            self.assertEqual(build.status_code, 200, build.text)

            model_before = client.get("/api/ml/repayment/model")
            self.assertEqual(model_before.status_code, 404)

            train = client.post("/api/ml/repayment/train")
            self.assertEqual(train.status_code, 200, train.text)
            body = train.json()
            self.assertIn(body["best_model"], {"random_forest", "xgboost", "lightgbm"})
            self.assertGreater(body["records_used"], 0)
            self.assertIn("test_metrics", body)
            self.assertIn("cv_scores", body)
            self.assertTrue(Path(body["model_path"]).exists())
            self.assertTrue(Path(body["metrics_path"]).exists())
            self.assertTrue(Path(body["feature_importance_path"]).exists())

            model = client.get("/api/ml/repayment/model")
            self.assertEqual(model.status_code, 200, model.text)
            model_body = model.json()
            self.assertTrue(model_body["model_exists"])
            self.assertIsNotNone(model_body["metrics"])
            self.assertIsNotNone(model_body["feature_importance"])

            preview = client.get("/api/ml/dataset?limit=1")
            self.assertEqual(preview.status_code, 200)
            record = preview.json()["records"][0]

            predict_by_profile = client.post(
                "/api/ml/repayment/predict",
                json={"profile_id": record["profile_id"], "profile_type": record["profile_type"]},
            )
            self.assertEqual(predict_by_profile.status_code, 200, predict_by_profile.text)
            pred_body = predict_by_profile.json()
            self.assertIn(
                pred_body["repayment_capacity"],
                {"Very High", "High", "Medium", "Low"},
            )
            self.assertGreater(pred_body["confidence"], 0)
            self.assertIn("probabilities", pred_body)

            predict_by_features = client.post(
                "/api/ml/repayment/predict",
                json={
                    "features": {
                        "profile_type": "Internal",
                        "age": 35,
                        "income": 120000,
                        "credit_score": 780,
                        "financial_health_score": 85,
                        "repayment_behaviour_score": 80,
                        "digital_engagement_score": 75,
                        "relationship_score": 70,
                        "savings_ratio": 40,
                        "emi_burden": 15,
                        "cash_flow_score": 72,
                        "digital_adoption_score": 68,
                        "customer_value_score": 60,
                        "occupation": "Engineer",
                        "city": "Mumbai",
                    }
                },
            )
            self.assertEqual(predict_by_features.status_code, 200, predict_by_features.text)
            self.assertIn(
                predict_by_features.json()["repayment_capacity"],
                {"Very High", "High", "Medium", "Low"},
            )


if __name__ == "__main__":
    unittest.main()
