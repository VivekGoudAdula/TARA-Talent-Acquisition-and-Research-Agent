"""HTTP bridge from Tara to the Vanguard Voice Banking platform."""

from __future__ import annotations

import io
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.schemas.engagement import EngagementLeadRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class VoiceBridgeError(RuntimeError):
    """Raised when the voice platform API returns an error."""


class VoiceBridge:
    """Pushes Tara engagement rows to bank/bank campaign APIs."""

    def __init__(self, settings: Settings | None = None, timeout: float = 60.0) -> None:
        self._settings = settings or get_settings()
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return (self._settings.voice_agent_base_url or "").rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def health_check(self) -> dict[str, Any]:
        if not self.is_configured:
            return {"configured": False, "reachable": False, "detail": "VOICE_AGENT_BASE_URL not set"}
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=10.0)
            return {
                "configured": True,
                "reachable": response.status_code == 200,
                "status_code": response.status_code,
            }
        except Exception as exc:
            return {"configured": True, "reachable": False, "detail": str(exc)}

    def create_campaign(self, name: str, agent_id: str, description: str = "") -> dict[str, Any]:
        payload = {
            "name": name,
            "agent_id": agent_id,
            "description": description or f"Tara engagement campaign — agent={agent_id}",
        }
        return self._post_json("/campaigns/create", payload)

    def upload_leads_csv(self, campaign_id: int, csv_text: str) -> dict[str, Any]:
        files = {
            "file": ("tara_engagement_leads.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv"),
        }
        data = {"campaign_id": str(campaign_id)}
        return self._post_multipart("/campaigns/upload", data=data, files=files)

    def start_campaign(self, campaign_id: int) -> dict[str, Any]:
        return self._post_json(f"/campaigns/{campaign_id}/start", {})

    def initiate_call(self, customer_id: str, agent_id: str) -> dict[str, Any]:
        return self._post_json(
            "/calls/initiate",
            {"customer_id": customer_id, "agent_id": agent_id},
        )

    def initiate_call_by_phone(
        self,
        phone: str,
        agent_id: str = "lending_offer_agent",
        entity_id: str | None = None,
        entity_type: str = "External",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"phone": phone, "agent_id": agent_id}
        if entity_id:
            payload["entity_id"] = entity_id
        if entity_type:
            payload["entity_type"] = entity_type
        return self._post_json("/calls/initiate-by-phone", payload)

    def push_campaign(
        self,
        *,
        records: list[EngagementLeadRecord],
        campaign_name: str,
        agent_id: str,
        csv_text: str,
        start_campaign: bool = False,
    ) -> dict[str, Any]:
        if not records:
            raise VoiceBridgeError("No engagement records to push")
        if not self.is_configured:
            raise VoiceBridgeError(
                "VOICE_AGENT_BASE_URL is not set. Start bank/bank backend and set the URL in .env"
            )

        created = self.create_campaign(campaign_name, agent_id)
        campaign_id = created.get("id")
        if campaign_id is None:
            raise VoiceBridgeError(f"Voice platform did not return campaign id: {created}")

        upload_result = self.upload_leads_csv(int(campaign_id), csv_text)
        dialer_result = None
        if start_campaign:
            dialer_result = self.start_campaign(int(campaign_id))

        logger.info(
            "Pushed %d leads to voice campaign_id=%s start=%s",
            len(records),
            campaign_id,
            start_campaign,
        )
        return {
            "campaign_id": int(campaign_id),
            "campaign_name": campaign_name,
            "agent_id": agent_id,
            "leads_pushed": len(records),
            "upload_result": upload_result,
            "dialer_result": dialer_result,
        }

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise VoiceBridgeError(f"Voice API {path} failed ({exc.response.status_code}): {detail}") from exc
        except Exception as exc:
            raise VoiceBridgeError(f"Voice API {path} failed: {exc}") from exc

    def _post_multipart(
        self,
        path: str,
        *,
        data: dict[str, str],
        files: dict[str, tuple[str, io.BytesIO, str]],
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = httpx.post(url, data=data, files=files, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise VoiceBridgeError(f"Voice API {path} failed ({exc.response.status_code}): {detail}") from exc
        except Exception as exc:
            raise VoiceBridgeError(f"Voice API {path} failed: {exc}") from exc
