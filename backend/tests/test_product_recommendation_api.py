"""Integration tests for Product Recommendation API."""

import shutil
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.ml.repayment.registry import MODELS_DIR
from db_env import load_db_env

load_db_env()


class ProductRecommendationAPITests(unittest.TestCase):
    def setUp(self) -> None:
        if MODELS_DIR.exists():
            shutil.rmtree(MODELS_DIR)

    def test_catalog_and_recommend(self) -> None:
        with TestClient(app) as client:
            catalog = client.get("/api/ml/products/catalog")
            self.assertEqual(catalog.status_code, 200, catalog.text)
            catalog_body = catalog.json()
            self.assertEqual(catalog_body["total_products"], 5)
            self.assertEqual(len(catalog_body["products"]), 5)

            build = client.post("/api/ml/dataset/build")
            self.assertEqual(build.status_code, 200, build.text)

            train = client.post("/api/ml/repayment/train")
            self.assertEqual(train.status_code, 200, train.text)

            preview = client.get("/api/ml/dataset?limit=1")
            self.assertEqual(preview.status_code, 200)
            record = preview.json()["records"][0]
            profile_id = record["profile_id"]

            recommend = client.post(
                "/api/ml/products/recommend",
                json={"profile_id": profile_id, "top_n": 5},
            )
            self.assertEqual(recommend.status_code, 200, recommend.text)
            body = recommend.json()
            self.assertEqual(body["profile_id"], profile_id)
            self.assertIn(body["repayment_capacity"], {"Very High", "High", "Medium", "Low"})
            self.assertGreater(len(body["recommendations"]), 0)
            self.assertLessEqual(len(body["recommendations"]), 5)
            self.assertIsNotNone(body["top_recommendation"])

            top = body["recommendations"][0]
            self.assertIn("product_name", top)
            self.assertIn("confidence_score", top)
            self.assertIn("eligible", top)
            self.assertIn("probability", top)
            self.assertGreater(top["probability"], 0)

    def test_recommend_requires_trained_repayment_model(self) -> None:
        with TestClient(app) as client:
            if MODELS_DIR.exists():
                shutil.rmtree(MODELS_DIR)

            build = client.post("/api/ml/dataset/build")
            self.assertEqual(build.status_code, 200)
            preview = client.get("/api/ml/dataset?limit=1")
            profile_id = preview.json()["records"][0]["profile_id"]

            recommend = client.post(
                "/api/ml/products/recommend",
                json={"profile_id": profile_id},
            )
            self.assertEqual(recommend.status_code, 404)


if __name__ == "__main__":
    unittest.main()
