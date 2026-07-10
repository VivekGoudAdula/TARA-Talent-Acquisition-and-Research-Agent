"""Integration tests for customer health analytics API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class CustomerHealthAPITests(unittest.TestCase):
    def test_customer_health_endpoints(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            client.post(f"/api/customer360/build/{customer_id}")

            compute = client.post(f"/api/customer360/customer-health/{customer_id}")
            self.assertEqual(compute.status_code, 200, compute.text)

            body = compute.json()["health_profile"]
            self.assertIn("customer_health_score", body)
            self.assertIn("financial_stress_score", body)
            self.assertIn("churn_risk_score", body)
            self.assertIn("risk_band", body)
            self.assertIn("reason_codes", body)
            self.assertGreater(len(body["reason_codes"]), 0)

            get_resp = client.get(f"/api/customer360/customer-health/{customer_id}")
            self.assertEqual(get_resp.status_code, 200, get_resp.text)


if __name__ == "__main__":
    unittest.main()
