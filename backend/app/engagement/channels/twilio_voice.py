"""Direct Twilio outbound voice calls — fallback when Vanguard voice platform is down."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TwilioVoiceClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.twilio_account_sid
            and self._settings.twilio_auth_token
            and self._settings.twilio_from_number
        )

    def place_call(self, *, to: str, twiml: str | None = None, twiml_url: str | None = None) -> dict:
        if not self.is_configured:
            raise RuntimeError("Twilio voice not configured (TWILIO_ACCOUNT_SID, AUTH_TOKEN, FROM_NUMBER)")
        if not twiml and not twiml_url:
            raise ValueError("twiml or twiml_url is required")

        from twilio.rest import Client

        client = Client(self._settings.twilio_account_sid, self._settings.twilio_auth_token)
        kwargs: dict = {"to": to, "from_": self._settings.twilio_from_number}
        if twiml:
            kwargs["twiml"] = twiml
        else:
            kwargs["url"] = twiml_url
        try:
            call = client.calls.create(**kwargs)
            logger.info("Twilio callback placed to=%s sid=%s", to, call.sid)
            return {"call_sid": call.sid, "status": call.status, "provider": "twilio_direct"}
        except Exception as exc:
            msg = str(exc)
            if "not verified" in msg.lower() or "21219" in msg:
                raise RuntimeError(
                    "Twilio trial account can only call verified numbers. "
                    "Add your phone at https://console.twilio.com/us1/develop/phone-numbers/manage/verified"
                ) from exc
            if "not authorized to call" in msg.lower():
                raise RuntimeError(
                    "Twilio voice not enabled for this FROM number. "
                    "Use a voice-capable Twilio number in TWILIO_FROM_NUMBER."
                ) from exc
            raise RuntimeError(f"Twilio voice call failed: {msg}") from exc
