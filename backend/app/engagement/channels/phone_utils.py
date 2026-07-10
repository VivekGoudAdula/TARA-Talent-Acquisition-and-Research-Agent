"""Phone normalization for Twilio channels."""

from __future__ import annotations


def normalize_e164(phone: str, *, default_country_code: str = "91") -> str:
    raw = (phone or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if raw.startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+{default_country_code}{digits}"
    if len(digits) == 12 and digits.startswith(default_country_code):
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def to_whatsapp_address(phone: str) -> str:
    e164 = normalize_e164(phone)
    if not e164:
        return ""
    return e164 if e164.startswith("whatsapp:") else f"whatsapp:{e164}"


def normalize_phone(phone: str) -> str:
    """Alias used by onboarding — returns E.164."""
    return normalize_e164(phone)
