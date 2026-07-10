"""Integration tests for behaviour analytics API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class BehaviourAnalyticsAPITests(unittest.TestCase):
    def test_behaviour_endpoints(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            client.post(f"/api/customer360/build/{customer_id}")

            compute = client.post(f"/api/customer360/behaviour/{customer_id}")
            self.assertEqual(compute.status_code, 200, compute.text)

            body = compute.json()["behaviour_profile"]
            self.assertIn("shopping_score", body)
            self.assertIn("lifestyle_tags", body)
            self.assertIn("top_interest", body)

            get_resp = client.get(f"/api/customer360/behaviour/{customer_id}")
            self.assertEqual(get_resp.status_code, 200, get_resp.text)
            self.assertIsNotNone(get_resp.json()["shopping_score"])


if __name__ == "__main__":
    unittest.main()
