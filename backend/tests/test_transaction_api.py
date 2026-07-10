"""Integration tests for transaction analytics API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class TransactionAnalyticsAPITests(unittest.TestCase):
    def test_transaction_endpoints(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            client.post(f"/api/customer360/build/{customer_id}")

            compute = client.post(f"/api/customer360/transaction/{customer_id}")
            self.assertEqual(compute.status_code, 200, compute.text)
            analytics = compute.json()["analytics"]
            self.assertIn("digital_payment_ratio", analytics)
            self.assertIn("merchant_diversity", analytics)
            self.assertIn("transaction_consistency_score", analytics)

            get_resp = client.get(f"/api/customer360/transaction/{customer_id}")
            self.assertEqual(get_resp.status_code, 200, get_resp.text)
            self.assertIn("most_frequent_merchant", get_resp.json())


if __name__ == "__main__":
    unittest.main()
