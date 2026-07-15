"""Trigger AI voice callback when a customer asks to talk via WhatsApp/SMS/Email."""

from __future__ import annotations

from app.engagement.callback_orchestrator import CallbackOrchestrator
from app.engagement.export_service import EngagementExportService
from app.engagement.voice_bridge import VoiceBridge
from app.onboarding.response_parser import is_contact_intent
from app.schemas.engagement import EngagementLeadRecord
from app.schemas.onboarding import LeadResponseCaptureRequest
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ContactVoiceTrigger:
    def __init__(self, db, voice_bridge: VoiceBridge | None = None) -> None:
        self._db = db
        self._export = EngagementExportService(db)
        self._orchestrator = CallbackOrchestrator(db, voice_bridge=voice_bridge)

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

        result = self._orchestrator.start_callback(
            phone=phone,
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            name=request.name or rec.name,
            source_channel=request.channel,
        )

        if result.triggered:
            logger.info(
                "Contact voice triggered entity=%s phone=%s session=%s call_sid=%s",
                request.entity_id,
                phone,
                result.session_id,
                result.call_sid,
            )
            return {
                "triggered": True,
                "session_id": result.session_id,
                "call": result.call,
                "call_sid": result.call_sid,
                "timing_ms": result.timing_ms,
                "context": result.context.model_dump(),
            }

        logger.warning(
            "Contact voice trigger skipped entity=%s reason=%s",
            request.entity_id,
            result.reason,
        )
        return {
            "triggered": False,
            "reason": result.reason,
            "session_id": result.session_id,
        }
