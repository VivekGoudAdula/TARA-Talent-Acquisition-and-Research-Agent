"""Integration tests for digital & channel analytics API."""

import unittest

from fastapi.testclient import TestClient

from app.main import app
from db_env import load_db_env, sample_customer_id

load_db_env()


class DigitalChannelAPITests(unittest.TestCase):
    def test_channel_endpoints(self) -> None:
        customer_id = sample_customer_id()

        with TestClient(app) as client:
            client.post(f"/api/customer360/build/{customer_id}")

            compute = client.post(f"/api/customer360/channel/{customer_id}")
            self.assertEqual(compute.status_code, 200, compute.text)

            body = compute.json()["channel_profile"]
            self.assertIn("digital_adoption_score", body)
            self.assertIn("digital_maturity", body)
            self.assertIn("preferred_channel", body)
            self.assertIn("voice_readiness_score", body)
            self.assertIn("contact_policy", body)

            get_resp = client.get(f"/api/customer360/channel/{customer_id}")
            self.assertEqual(get_resp.status_code, 200, get_resp.text)


if __name__ == "__main__":
    unittest.main()
