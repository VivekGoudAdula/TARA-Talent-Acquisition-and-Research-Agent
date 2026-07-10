"""Integration tests for relationship analytics API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class RelationshipAnalyticsAPITests(unittest.TestCase):
    def test_relationship_endpoints(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            client.post(f"/api/customer360/build/{customer_id}")

            compute = client.post(f"/api/customer360/relationship/{customer_id}")
            self.assertEqual(compute.status_code, 200, compute.text)

            body = compute.json()["relationship_profile"]
            self.assertIn("relationship_tier", body)
            self.assertIn("relationship_strength_score", body)
            self.assertIn("missing_products", body)
            self.assertIn("engagement_score", body)

            get_resp = client.get(f"/api/customer360/relationship/{customer_id}")
            self.assertEqual(get_resp.status_code, 200, get_resp.text)
            self.assertIsNotNone(get_resp.json()["relationship_tier"])


if __name__ == "__main__":
    unittest.main()
