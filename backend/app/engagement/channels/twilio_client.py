"""Shared Twilio client for SMS and WhatsApp."""

from __future__ import annotations

import json
from typing import Any

from app.config import Settings, get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TwilioMessagingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.twilio_account_sid and self._settings.twilio_auth_token)

    def get_client(self):
        if not self.is_configured:
            return None
        if self._client is None:
            from twilio.rest import Client

            self._client = Client(
                self._settings.twilio_account_sid,
                self._settings.twilio_auth_token,
            )
        return self._client

    def send_sms(self, *, to: str, from_: str, body: str) -> tuple[bool, str | None, str | None]:
        return self._send(to=to, from_=from_, body=body)

    def send_whatsapp(
        self,
        *,
        to: str,
        from_: str,
        body: str | None = None,
        content_sid: str | None = None,
        content_variables: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None, str | None]:
        kwargs: dict[str, Any] = {"to": to, "from_": from_}
        if content_sid:
            kwargs["content_sid"] = content_sid
            if content_variables:
                kwargs["content_variables"] = json.dumps(content_variables)
        elif body:
            kwargs["body"] = body
        else:
            return False, None, "WhatsApp message requires body or content_sid"
        return self._send(**kwargs)

    def send_whatsapp_media(
        self,
        *,
        to: str,
        from_: str,
        body: str,
        media_url: str,
    ) -> tuple[bool, str | None, str | None]:
        return self._send(to=to, from_=from_, body=body, media_url=[media_url])

    def send_message(self, *, to: str, from_: str, body: str) -> tuple[bool, str | None, str | None]:
        """Backward-compatible SMS send."""
        return self.send_sms(to=to, from_=from_, body=body)

    def _send(self, **kwargs: Any) -> tuple[bool, str | None, str | None]:
        client = self.get_client()
        if not client:
            return False, None, "Twilio credentials not configured"
        if not kwargs.get("from_"):
            return False, None, "Twilio sender not configured"
        try:
            msg = client.messages.create(**kwargs)
            logger.info("Twilio message sent to=%s sid=%s", kwargs.get("to"), msg.sid)
            return True, msg.sid, msg.status or "sent"
        except Exception as exc:
            logger.warning("Twilio message failed to=%s: %s", kwargs.get("to"), exc)
            return False, None, str(exc)
