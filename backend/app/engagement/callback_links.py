"""Public callback CTA links for Email/WhatsApp — must not use localhost on mobile."""

from __future__ import annotations

import secrets
import socket
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import Settings, get_settings
from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_TOKEN_TTL_HOURS = 72


def get_lan_ip() -> str | None:
    """Best-effort LAN IP for same-WiFi mobile testing."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def is_public_webhook_url(base: str) -> bool:
    """True only if Twilio's cloud can fetch this URL (ngrok, deployed host)."""
    b = (base or "").strip().lower()
    if not b.startswith("http"):
        return False
    private = (
        "localhost",
        "127.0.0.1",
        "192.168.",
        "10.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
    )
    return not any(marker in b for marker in private)


def twilio_webhook_url(base: str, path: str) -> str:
    """Build a Twilio-facing webhook URL (ngrok interstitial bypass when needed)."""
    url = f"{base.rstrip('/')}{path}"
    if "ngrok" in url.lower() and "ngrok-skip-browser-warning" not in url.lower():
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ngrok-skip-browser-warning=1"
    return url


def is_webhook_reachable(base: str, timeout: float = 2.0) -> bool:
    """True if Twilio can reach this host (e.g. ngrok tunnel running)."""
    if not is_public_webhook_url(base):
        return False
    import urllib.error
    import urllib.request

    health_url = f"{base.rstrip('/')}/health"
    if "ngrok" in health_url.lower():
        sep = "&" if "?" in health_url else "?"
        health_url = f"{health_url}{sep}ngrok-skip-browser-warning=1"
    try:
        req = urllib.request.Request(
            health_url,
            method="GET",
            headers={"User-Agent": "Tara-Webhook-Probe/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception as exc:
        logger.warning("Webhook probe failed url=%s: %s", health_url, exc)
        return False


def resolve_public_api_base(settings: Settings | None = None) -> str:
    """
    Base URL embedded in email/WhatsApp callback CTAs.

    Mobile devices cannot open localhost — use ngrok, a deployed host, or LAN IP.
    """
    cfg = settings or get_settings()
    candidates = [
        cfg.engagement_api_base_url,
        getattr(cfg, "engagement_public_url", "") or "",
    ]
    for raw in candidates:
        base = (raw or "").strip().rstrip("/")
        if not base:
            continue
        if "localhost" not in base and "127.0.0.1" not in base:
            return base

    if cfg.engagement_use_lan_ip:
        lan = get_lan_ip()
        if lan:
            port = _port_from_url(cfg.engagement_api_base_url)
            return f"http://{lan}:{port}"

    base = (cfg.engagement_api_base_url or "http://localhost:8000").rstrip("/")
    if "localhost" in base or "127.0.0.1" in base:
        logger.warning(
            "Callback CTA uses localhost — email links will fail on mobile. "
            "Set ENGAGEMENT_API_BASE_URL to your ngrok or public URL."
        )
    return base


def _port_from_url(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url or "http://localhost:8000")
    return str(parsed.port or 8000)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    """Cosmos/Mongo may return naive datetimes — normalize for comparisons."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class CallbackLinkService:
    """Creates short-lived tokens so email CTAs work from any device."""

    def __init__(self, db: MongoDatabase, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings or get_settings()

    def create_link(
        self,
        *,
        phone: str,
        entity_id: str,
        entity_type: str = "External",
        source_channel: str = "Email",
        campaign: str | None = None,
    ) -> str:
        token = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        self._db.callback_cta_tokens.insert_one(
            {
                "token": token,
                "phone": phone,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "source_channel": source_channel,
                "campaign": campaign,
                "created_at": now,
                "expires_at": now + timedelta(hours=_TOKEN_TTL_HOURS),
                "used_at": None,
            }
        )
        base = resolve_public_api_base(self._settings)
        return f"{base}/api/engagement/callback/go/{token}"

    def resolve_token(self, token: str) -> dict[str, Any] | None:
        doc = self._db.callback_cta_tokens.find_one({"token": token})
        if not doc:
            return None
        expires = _as_utc_aware(doc.get("expires_at"))
        if expires and expires < datetime.now(timezone.utc):
            return None
        return doc

    def mark_used(self, token: str) -> None:
        self._db.callback_cta_tokens.update_one(
            {"token": token},
            {"$set": {"used_at": datetime.now(timezone.utc)}},
        )
