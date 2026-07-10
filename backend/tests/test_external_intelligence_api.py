"""Integration tests for External Lead Intelligence API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env

load_db_env()


class ExternalLeadIntelligenceAPITests(unittest.TestCase):
    def test_intelligence_flow(self) -> None:
        with TestClient(app) as client:
            leads = client.get("/api/external/leads?limit=1")
            self.assertEqual(leads.status_code, 200)
            lead_id = leads.json()["leads"][0]["lead_id"]

            profile = client.get(f"/api/external/profile/{lead_id}")
            if profile.status_code == 404:
                client.post("/api/external/enrich")

            build = client.post(f"/api/external/intelligence/build/{lead_id}")
            self.assertEqual(build.status_code, 200, build.text)
            intel = build.json()["intelligence"]
            self.assertIn("lead_authenticity_score", intel)
            self.assertIn("income_confidence_score", intel)
            self.assertIn("fraud_score", intel)
            self.assertIn("kyc_readiness", intel)
            self.assertIn("reason_codes", intel)

            get_resp = client.get(f"/api/external/intelligence/{lead_id}")
            self.assertEqual(get_resp.status_code, 200)
            self.assertEqual(
                get_resp.json()["lead_authenticity_score"],
                intel["lead_authenticity_score"],
            )


if __name__ == "__main__":
    unittest.main()
