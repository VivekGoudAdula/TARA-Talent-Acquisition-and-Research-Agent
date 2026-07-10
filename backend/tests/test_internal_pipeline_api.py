"""Integration tests for Internal Intelligence Pipeline API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class InternalPipelineAPITests(unittest.TestCase):
    def test_status_endpoint(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/internal/status")
            self.assertEqual(resp.status_code, 200, resp.text)
            body = resp.json()
            self.assertIn("total_customers", body)
            self.assertIn("profiles_built", body)
            self.assertIn("feature_store_built", body)
            self.assertIn("success_percentage", body)

    def test_build_single_customer(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            resp = client.post(f"/api/internal/build/{customer_id}")
            self.assertEqual(resp.status_code, 200, resp.text)
            body = resp.json()
            self.assertEqual(body["completed"], 1)
            self.assertEqual(body["failed"], 0)
            self.assertIn("validation", body)
            self.assertEqual(len(body["results"]), 1)
            self.assertTrue(body["results"][0]["success"])


if __name__ == "__main__":
    unittest.main()
