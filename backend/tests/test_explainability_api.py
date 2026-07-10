"""Integration tests for Explainable AI API."""

import os
import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.ml.conversion.training import MODEL_PATH as CONVERSION_MODEL
from app.ml.repayment.registry import MODELS_DIR
from db_env import load_db_env

load_db_env()

os.environ["EXPLAINABILITY_USE_LLM"] = "false"

from app.config import get_settings

get_settings.cache_clear()


class ExplainabilityAPITests(unittest.TestCase):
    def setUp(self) -> None:
        if MODELS_DIR.exists():
            shutil.rmtree(MODELS_DIR)

    def test_generate_and_get_explanation(self) -> None:
        with TestClient(app) as client:
            client.post("/api/ml/dataset/build")
            client.post("/api/ml/repayment/train")
            client.post("/api/ml/conversion/train")

            preview = client.get("/api/ml/dataset?limit=1")
            self.assertEqual(preview.status_code, 200)
            record = preview.json()["records"][0]
            profile_id = record["profile_id"]

            generate = client.post(
                "/api/explain/generate",
                json={"profile_id": profile_id},
            )
            self.assertEqual(generate.status_code, 200, generate.text)
            body = generate.json()
            self.assertIn("report_id", body)
            self.assertIn("explanation", body)
            self.assertIn("summary", body["explanation"])
            self.assertIn("repayment_explanation", body["explanation"])
            self.assertIn("product_explanation", body["explanation"])
            self.assertIn("conversion_explanation", body["explanation"])
            self.assertIn("confidence_summary", body["explanation"])
            self.assertGreater(len(body["reason_codes"]), 0)
            self.assertIsNotNone(body["decision_summary"])

            customer_id = body["customer_id"]
            latest = client.get(f"/api/explain/{customer_id}")
            self.assertEqual(latest.status_code, 200, latest.text)
            self.assertEqual(latest.json()["report_id"], body["report_id"])

    def test_get_missing_report_returns_404(self) -> None:
        with TestClient(app) as client:
            from uuid import uuid4

            missing = client.get(f"/api/explain/{uuid4()}")
            self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
