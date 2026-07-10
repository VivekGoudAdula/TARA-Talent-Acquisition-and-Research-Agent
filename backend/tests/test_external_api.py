"""Integration tests for External Customer Intelligence API."""

import os
import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env

load_db_env()


class ExternalIntelligenceAPITests(unittest.TestCase):
    def test_import_enrich_and_profile_flow(self) -> None:
        with TestClient(app) as client:
            import_resp = client.post("/api/external/import")
            self.assertEqual(import_resp.status_code, 200, import_resp.text)
            body = import_resp.json()
            self.assertGreater(body["leads_imported"] + body["leads_updated"], 0)

            enrich_resp = client.post("/api/external/enrich")
            self.assertEqual(enrich_resp.status_code, 200, enrich_resp.text)
            enrich_body = enrich_resp.json()
            self.assertGreater(enrich_body["leads_enriched"], 0)

            leads_resp = client.get("/api/external/leads?limit=5")
            self.assertEqual(leads_resp.status_code, 200)
            leads = leads_resp.json()
            self.assertGreater(leads["total"], 0)
            self.assertGreater(len(leads["leads"]), 0)

            lead_id = leads["leads"][0]["lead_id"]
            profile_resp = client.get(f"/api/external/profile/{lead_id}")
            self.assertEqual(profile_resp.status_code, 200, profile_resp.text)
            profile = profile_resp.json()
            self.assertEqual(profile["lead_id"], lead_id)
            self.assertIsNotNone(profile["lead_score"])
            self.assertIsNotNone(profile["customer_persona"])
            self.assertIsNotNone(profile["income_segment"])


if __name__ == "__main__":
    unittest.main()
