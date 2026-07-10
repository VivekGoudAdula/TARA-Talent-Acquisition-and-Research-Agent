"""Integration tests for Behaviour Analytics Summary API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class BehaviourSummaryAPITests(unittest.TestCase):
    def test_internal_behaviour_summary_flow(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            build_profile = client.post(f"/api/customer360/build/{customer_id}")
            self.assertEqual(build_profile.status_code, 200, build_profile.text)
            profile_id = build_profile.json()["profile"]["profile_id"]

            for path in (
                f"/api/customer360/financial/{customer_id}",
                f"/api/customer360/transaction/{customer_id}",
                f"/api/customer360/behaviour/{customer_id}",
                f"/api/customer360/relationship/{customer_id}",
                f"/api/customer360/channel/{customer_id}",
                f"/api/customer360/customer-health/{customer_id}",
            ):
                resp = client.post(path)
                self.assertEqual(resp.status_code, 200, f"{path}: {resp.text}")

            build = client.post(f"/api/behaviour/build/{profile_id}")
            self.assertEqual(build.status_code, 200, build.text)
            summary = build.json()["summary"]
            self.assertEqual(summary["profile_type"], "Internal")
            self.assertIn("financial_health_score", summary)
            self.assertIn("repayment_behaviour_score", summary)
            self.assertIn("digital_engagement_score", summary)

            get_resp = client.get(f"/api/behaviour/{profile_id}")
            self.assertEqual(get_resp.status_code, 200)
            body = get_resp.json()
            self.assertEqual(body["profile_type"], "Internal")
            self.assertEqual(
                body["financial_health_score"],
                summary["financial_health_score"],
            )

    def test_external_behaviour_summary_flow(self) -> None:
        with TestClient(app) as client:
            leads = client.get("/api/external/leads?limit=1")
            self.assertEqual(leads.status_code, 200)
            lead_id = leads.json()["leads"][0]["lead_id"]

            profile_resp = client.get(f"/api/external/profile/{lead_id}")
            if profile_resp.status_code == 404:
                client.post("/api/external/enrich")
                profile_resp = client.get(f"/api/external/profile/{lead_id}")
            self.assertEqual(profile_resp.status_code, 200, profile_resp.text)
            profile_id = profile_resp.json()["profile_id"]

            client.post(f"/api/external/analytics/build/{lead_id}")
            client.post(f"/api/external/intelligence/build/{lead_id}")

            build = client.post(f"/api/behaviour/build/{profile_id}")
            self.assertEqual(build.status_code, 200, build.text)
            summary = build.json()["summary"]
            self.assertEqual(summary["profile_type"], "External")
            self.assertIn("financial_health_score", summary)
            self.assertIn("repayment_behaviour_score", summary)
            self.assertIn("digital_engagement_score", summary)

            get_resp = client.get(f"/api/behaviour/{profile_id}")
            self.assertEqual(get_resp.status_code, 200)
            self.assertEqual(get_resp.json()["profile_type"], "External")


if __name__ == "__main__":
    unittest.main()
