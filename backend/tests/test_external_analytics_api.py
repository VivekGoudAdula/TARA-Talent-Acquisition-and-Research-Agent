"""Integration tests for External Lead Analytics API."""

import unittest
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env

load_db_env()


class ExternalLeadAnalyticsAPITests(unittest.TestCase):
    def test_analytics_flow(self) -> None:
        with TestClient(app) as client:
            leads = client.get("/api/external/leads?limit=1")
            self.assertEqual(leads.status_code, 200)
            items = leads.json()["leads"]
            self.assertGreater(len(items), 0)
            lead_id = items[0]["lead_id"]

            profile = client.get(f"/api/external/profile/{lead_id}")
            if profile.status_code == 404:
                client.post("/api/external/enrich")

            build = client.post(f"/api/external/analytics/build/{lead_id}")
            self.assertEqual(build.status_code, 200, build.text)
            body = build.json()["analytics"]
            self.assertIn("lead_quality_score", body)
            self.assertIn("financial_capacity_score", body)
            self.assertIn("campaign_engagement_score", body)
            self.assertIn("digital_readiness_score", body)
            self.assertIn("qualification_status", body)
            self.assertIn("priority_level", body)

            get_resp = client.get(f"/api/external/analytics/{lead_id}")
            self.assertEqual(get_resp.status_code, 200)
            self.assertEqual(
                get_resp.json()["lead_quality_score"],
                body["lead_quality_score"],
            )


if __name__ == "__main__":
    unittest.main()
