"""Integration tests for the financial analytics API endpoint."""

import unittest
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class FinancialAnalyticsAPITests(unittest.TestCase):
    def test_financial_endpoint(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            build = client.post(f"/api/customer360/build/{customer_id}")
            self.assertEqual(build.status_code, 200, build.text)

            financial = client.post(f"/api/customer360/financial/{customer_id}")
            self.assertEqual(financial.status_code, 200, financial.text)

            body = financial.json()
            profile = body["financial_profile"]

            self.assertIn("monthly_income", profile)
            self.assertIn("monthly_expense", profile)
            self.assertIn("monthly_savings", profile)
            self.assertIn("savings_ratio", profile)
            self.assertIn("cash_flow_score", profile)
            self.assertIn("liquidity_score", profile)
            self.assertIn("debt_ratio", profile)
            self.assertIn("investment_ratio", profile)
            self.assertIn("emi_burden", profile)

            self.assertIsNotNone(profile["monthly_income"])
            self.assertIsNotNone(profile["cash_flow_score"])


if __name__ == "__main__":
    unittest.main()
