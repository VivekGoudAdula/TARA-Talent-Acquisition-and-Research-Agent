"""Trigger AI voice callback when a customer asks to talk via WhatsApp/SMS/Email."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.engagement.export_service import EngagementExportService
from app.engagement.voice_bridge import VoiceBridge, VoiceBridgeError
from app.onboarding.response_parser import is_contact_intent
from app.schemas.engagement import EngagementLeadRecord
from app.schemas.onboarding import LeadResponseCaptureRequest
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_DEDUP_MINUTES = 3


class ContactVoiceTrigger:
    def __init__(self, db, voice_bridge: VoiceBridge | None = None) -> None:
        self._db = db
        self._export = EngagementExportService(db)
        self._voice = voice_bridge or VoiceBridge()

    def maybe_trigger_from_response(
        self,
        request: LeadResponseCaptureRequest,
        *,
        response_type: str,
        record: EngagementLeadRecord | None = None,
    ) -> dict | None:
        """If the message is a contact/callback intent, place an AI voice call."""
        if not is_contact_intent(
            response_type=response_type,
            raw_text=request.raw_text,
            button_payload=request.button_payload,
        ):
            return None

        rec = record or self._export.build_record_for_entity(
            request.entity_id, request.entity_type
        )
        if not rec:
            rec = EngagementLeadRecord(
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                phone=request.phone or "",
                name=request.name or "Customer",
                consent=True,
            )

        if rec.consent is False:
            logger.info(
                "Voice callback skipped — no marketing consent entity=%s",
                request.entity_id,
            )
            return {
                "triggered": False,
                "reason": "consent_denied",
                "message": "Customer has not consented to promotional contact.",
            }

        phone = (request.phone or rec.phone or "").strip()
        if not phone:
            return {"triggered": False, "reason": "no_phone"}

        if self._recent_callback(request.entity_id, phone):
            return {"triggered": False, "reason": "dedup_recent"}

        if not self._voice.is_configured:
            return {"triggered": False, "reason": "voice_not_configured"}

        try:
            result = self._voice.initiate_call_by_phone(
                phone=phone,
                agent_id="lending_offer_agent",
                entity_id=request.entity_id,
                entity_type=request.entity_type,
            )
            self._mark_callback(request.entity_id, phone)
            logger.info(
                "Contact voice triggered entity=%s phone=%s call_sid=%s",
                request.entity_id,
                phone,
                result.get("call_sid"),
            )
            return {"triggered": True, "call": result}
        except VoiceBridgeError as exc:
            logger.warning("Contact voice trigger failed: %s", exc)
            return {"triggered": False, "reason": str(exc)}

    def _recent_callback(self, entity_id: str, phone: str) -> bool:
        digits = "".join(c for c in phone if c.isdigit())[-10:]
        key = f"{entity_id}:{digits}"
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_DEDUP_MINUTES)
        return bool(
            self._db.voice_callback_dedup.find_one(
                {"dedup_key": key, "created_at": {"$gte": cutoff}}
            )
        )

    def _mark_callback(self, entity_id: str, phone: str) -> None:
        digits = "".join(c for c in phone if c.isdigit())[-10:]
        self._db.voice_callback_dedup.insert_one(
            {
                "dedup_key": f"{entity_id}:{digits}",
                "entity_id": entity_id,
                "phone": digits,
                "created_at": datetime.now(timezone.utc),
            }
        )
