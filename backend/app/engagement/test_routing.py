"""Route engagement messages to safe test recipients during demos."""

from __future__ import annotations

import threading

from app.config import Settings, get_settings
from app.engagement.channels.phone_utils import normalize_e164, to_whatsapp_address

_lock = threading.Lock()
_sms_index = 0
_email_index = 0


class TestRecipientRouter:
    """When test mode is on, override delivery addresses per channel."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self._settings.engagement_test_mode)

    def whatsapp_to(self, record_phone: str) -> str:
        override = (self._settings.engagement_whatsapp_override_phone or "").strip()
        phone = override or record_phone
        return to_whatsapp_address(phone)

    def sms_to(self, record_phone: str, *, entity_type: str | None = None) -> str:
        pool = self._phone_pool(self._settings.engagement_sms_test_phones)
        if not pool:
            return normalize_e164(record_phone)
        et = (entity_type or "").strip().lower()
        if et == "internal":
            return normalize_e164(pool[0])
        if et == "external" and len(pool) > 1:
            return normalize_e164(pool[1])
        global _sms_index
        with _lock:
            chosen = pool[_sms_index % len(pool)]
            _sms_index += 1
        return normalize_e164(chosen)

    def email_to(self, record_email: str, *, entity_type: str | None = None) -> str:
        pool = self._email_pool(self._settings.engagement_email_test_addresses)
        if not pool:
            return (record_email or "").strip()
        et = (entity_type or "").strip().lower()
        if et == "internal":
            return pool[0]
        if et == "external" and len(pool) > 1:
            return pool[1]
        global _email_index
        with _lock:
            chosen = pool[_email_index % len(pool)]
            _email_index += 1
        return chosen

    @staticmethod
    def _phone_pool(raw: str) -> list[str]:
        out: list[str] = []
        for part in (raw or "").split(","):
            normalized = normalize_e164(part.strip())
            if normalized:
                out.append(normalized)
        return out

    @staticmethod
    def _email_pool(raw: str) -> list[str]:
        return [p.strip() for p in (raw or "").split(",") if p.strip() and "@" in p]
