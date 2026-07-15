"""Integration tests for Lead Conversion Prediction API."""

import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.ml.conversion.training import MODELS_DIR
from db_env import load_db_env

load_db_env()

CONVERSION_MODEL = MODELS_DIR / "best_conversion_model.pkl"


class ConversionAPITests(unittest.TestCase):
    def setUp(self) -> None:
        if CONVERSION_MODEL.exists():
            CONVERSION_MODEL.unlink()
        metrics = MODELS_DIR / "conversion_metrics.json"
        importance = MODELS_DIR / "conversion_feature_importance.json"
        if metrics.exists():
            metrics.unlink()
        if importance.exists():
            importance.unlink()

    def test_train_predict_model_info(self) -> None:
        with TestClient(app) as client:
            model_before = client.get("/api/ml/conversion/model")
            self.assertEqual(model_before.status_code, 404)

            train = client.post("/api/ml/conversion/train")
            self.assertEqual(train.status_code, 200, train.text)
            body = train.json()
            self.assertIn(body["best_model"], {"random_forest", "xgboost", "lightgbm"})
            self.assertGreater(body["records_used"], 0)
            self.assertIn("test_metrics", body)
            self.assertTrue(Path(body["model_path"]).exists())

            model = client.get("/api/ml/conversion/model")
            self.assertEqual(model.status_code, 200, model.text)
            self.assertTrue(model.json()["model_exists"])

            from app.repositories.external_lead_repository import ExternalLeadRepository
            from app.utils.database import new_session

            db = new_session()
            try:
                lead = ExternalLeadRepository(db).get_all(limit=1)[0]
                lead_id = str(lead.lead_id)
            finally:
                db.close()

            predict = client.post(
                "/api/ml/conversion/predict",
                json={"lead_id": lead_id},
            )
            self.assertEqual(predict.status_code, 200, predict.text)
            pred = predict.json()
            self.assertGreaterEqual(pred["conversion_probability"], 0.0)
            self.assertLessEqual(pred["conversion_probability"], 100.0)
            self.assertIn(pred["lead_priority"], {"High", "Medium", "Low"})
            self.assertIn(pred["marketing_priority"], {"High", "Medium", "Low"})

            predict_features = client.post(
                "/api/ml/conversion/predict",
                json={
                    "features": {
                        "lead_source": "Referral",
                        "campaign": "Premium Banking",
                        "referral_source": "Branch Referral",
                        "occupation": "Engineer",
                        "employer": "TCS",
                        "estimated_income": 900000,
                        "credit_score": 740,
                        "lead_quality_score": 82,
                        "behaviour_score": 78,
                        "digital_engagement_score": 75,
                        "consent": 1,
                        "previous_campaign_response": 70,
                        "communication_readiness": 80,
                    }
                },
            )
            self.assertEqual(predict_features.status_code, 200, predict_features.text)

            model_info = client.get("/api/ml/conversion/model-info")
            self.assertEqual(model_info.status_code, 200, model_info.text)
            info = model_info.json()
            self.assertEqual(info["metrics"]["model_type"], "regression")
            self.assertIn("mae", info["metrics"])
            self.assertIn("rmse", info["metrics"])
            self.assertIn("r2", info["metrics"])
            self.assertNotIn("accuracy", info["metrics"])


if __name__ == "__main__":
    unittest.main()
