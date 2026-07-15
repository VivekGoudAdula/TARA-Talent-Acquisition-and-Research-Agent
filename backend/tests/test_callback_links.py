"""Tests for mobile-safe callback CTA links."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.config import Settings
from app.engagement.callback_links import (
    CallbackLinkService,
    _as_utc_aware,
    get_lan_ip,
    resolve_public_api_base,
    twilio_webhook_url,
)


class CallbackLinksTests(unittest.TestCase):
    def test_as_utc_aware_naive_datetime(self) -> None:
        naive = datetime(2026, 7, 11, 12, 0, 0)
        aware = _as_utc_aware(naive)
        assert aware is not None
        self.assertEqual(aware.tzinfo, timezone.utc)

    def test_resolve_token_handles_naive_expiry(self) -> None:
        db = MagicMock()
        naive_expires = datetime.utcnow() + timedelta(hours=1)
        db.callback_cta_tokens.find_one.return_value = {
            "token": "abc",
            "phone": "+919876543210",
            "entity_id": "lead-1",
            "expires_at": naive_expires,
        }
        settings = Settings(ENGAGEMENT_API_BASE_URL="https://demo.example.com")
        doc = CallbackLinkService(db, settings).resolve_token("abc")
        self.assertIsNotNone(doc)

    def test_resolve_public_url_uses_ngrok_when_set(self) -> None:
        settings = Settings(
            ENGAGEMENT_API_BASE_URL="https://abc123.ngrok-free.app",
            ENGAGEMENT_USE_LAN_IP=True,
        )
        self.assertEqual(resolve_public_api_base(settings), "https://abc123.ngrok-free.app")

    def test_resolve_public_url_uses_lan_when_localhost(self) -> None:
        settings = Settings(
            ENGAGEMENT_API_BASE_URL="http://localhost:8000",
            ENGAGEMENT_USE_LAN_IP=True,
        )
        base = resolve_public_api_base(settings)
        self.assertNotIn("localhost", base)
        lan = get_lan_ip()
        if lan:
            self.assertIn(lan, base)

    def test_twilio_webhook_url_adds_ngrok_bypass(self) -> None:
        url = twilio_webhook_url(
            "https://abc.ngrok-free.dev",
            "/api/engagement/voice/twiml/gather/sess-1",
        )
        self.assertIn("ngrok-skip-browser-warning=1", url)

    def test_create_token_link(self) -> None:
        db = MagicMock()
        settings = Settings(ENGAGEMENT_API_BASE_URL="https://demo.example.com")
        svc = CallbackLinkService(db, settings)
        url = svc.create_link(
            phone="+919876543210",
            entity_id="lead-1",
            entity_type="External",
        )
        self.assertTrue(url.startswith("https://demo.example.com/api/engagement/callback/go/"))
        db.callback_cta_tokens.insert_one.assert_called_once()


if __name__ == "__main__":
    unittest.main()
