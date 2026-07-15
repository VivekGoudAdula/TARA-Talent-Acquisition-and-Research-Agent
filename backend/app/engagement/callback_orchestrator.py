"""AI Callback orchestration: Click → CreateSession → LoadContext → Call."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings, get_settings
from app.db.mongo import MongoDatabase
from app.engagement.channels.phone_utils import normalize_e164
from app.engagement.channels.twilio_voice import TwilioVoiceClient
from app.engagement.voice_bridge import VoiceBridge, VoiceBridgeError
from app.engagement.voice_context_service import VoiceContextService
from app.schemas.voice_session import VoiceAgentContext, VoiceCallbackStartResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_CALL_SLA_MS = 2000.0


class CallbackOrchestrator:
    """
    Unified AI Callback pipeline.

    Flow: CreateSession → LoadContext → Call (target <2s to dial initiation).
    """

    def __init__(
        self,
        db: MongoDatabase,
        voice_bridge: VoiceBridge | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._settings = settings or get_settings()
        self._voice = voice_bridge or VoiceBridge(self._settings)
        self._twilio_voice = TwilioVoiceClient(self._settings)
        self._context_svc = VoiceContextService(db)

    def start_callback(
        self,
        *,
        phone: str,
        entity_id: str,
        entity_type: str = "External",
        campaign: str | None = None,
        source_channel: str | None = None,
        name: str | None = None,
        skip_dedup: bool = False,
    ) -> VoiceCallbackStartResponse:
        timing: dict[str, float] = {}
        t0 = time.perf_counter()

        phone = phone.strip()
        if not phone:
            return self._fail_response("", "no_phone", timing)

        try:
            phone = normalize_e164(phone)
        except Exception:
            pass

        if not skip_dedup and self._recent_callback(entity_id, phone):
            return self._fail_response("", "dedup_recent", timing)

        if not self._voice.is_configured and not self._twilio_voice.is_configured:
            return self._fail_response("", "voice_not_configured", timing)

        # LoadContext
        t_ctx = time.perf_counter()
        try:
            context = self._context_svc.load_context(
                entity_id=entity_id,
                entity_type=entity_type,
                phone=phone,
                name=name,
                campaign=campaign,
                source_channel=source_channel,
            )
        except Exception as exc:
            logger.warning("LoadContext failed entity=%s: %s", entity_id, exc)
            return self._fail_response("", f"context_load_failed: {exc}", timing)
        timing["load_context"] = round((time.perf_counter() - t_ctx) * 1000, 1)

        # CreateSession
        t_sess = time.perf_counter()
        session_id = str(uuid4())
        session_doc = self._create_session(
            session_id=session_id,
            context=context,
            source_channel=source_channel,
        )
        timing["create_session"] = round((time.perf_counter() - t_sess) * 1000, 1)

        # Call — Vanguard platform if reachable, else Twilio direct (<2s target)
        t_call = time.perf_counter()
        try:
            call_result, provider = self._place_call(
                phone=phone,
                session_id=session_id,
                context=context,
            )
        except Exception as exc:
            self._update_session(session_id, status="failed", error=str(exc))
            timing["call"] = round((time.perf_counter() - t_call) * 1000, 1)
            timing["total"] = round((time.perf_counter() - t0) * 1000, 1)
            reason = str(exc)
            if isinstance(exc, VoiceBridgeError):
                reason = str(exc)
            logger.warning("Callback call failed session=%s: %s", session_id, reason)
            return VoiceCallbackStartResponse(
                session_id=session_id,
                triggered=False,
                context=context,
                timing_ms=timing,
                reason=str(exc),
                message="Voice callback failed",
            )

        call_ms = round((time.perf_counter() - t_call) * 1000, 1)
        timing["call"] = call_ms
        timing["total"] = round((time.perf_counter() - t0) * 1000, 1)

        call_sid = call_result.get("call_sid") or call_result.get("sid")
        self._update_session(
            session_id,
            status="initiated",
            call_sid=call_sid,
            call_result=call_result,
            timing_ms=timing,
            provider=provider,
        )
        self._mark_callback(entity_id, phone)

        if call_ms > _CALL_SLA_MS:
            logger.warning(
                "Callback call initiation exceeded SLA session=%s ms=%.1f",
                session_id,
                call_ms,
            )

        logger.info(
            "AI Callback started session=%s entity=%s call_sid=%s total_ms=%.1f",
            session_id,
            entity_id,
            call_sid,
            timing["total"],
        )

        return VoiceCallbackStartResponse(
            session_id=session_id,
            triggered=True,
            context=context,
            timing_ms=timing,
            call=call_result,
            call_sid=call_sid,
            message="AI callback call initiated",
        )

    def get_session_context(self, session_id: str) -> VoiceAgentContext | None:
        doc = self._db.voice_callback_sessions.find_one({"session_id": session_id})
        if not doc:
            return None
        ctx = doc.get("context")
        if not ctx:
            return None
        return VoiceAgentContext.model_validate(ctx)

    def _create_session(
        self,
        *,
        session_id: str,
        context: VoiceAgentContext,
        source_channel: str | None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "session_id": session_id,
            "entity_id": context.customer_id,
            "entity_type": context.entity_type,
            "phone": context.phone,
            "intent": context.intent,
            "source_channel": source_channel,
            "context": context.model_dump(),
            "status": "created",
            "call_sid": None,
            "created_at": now,
            "updated_at": now,
        }
        self._db.voice_callback_sessions.insert_one(doc)

        # External session registration is best-effort — never block the hot path
        if self._voice.is_configured and self._voice.is_reachable(timeout=0.5):
            try:
                external = self._voice.create_session(
                    session_id=session_id,
                    context=context.model_dump(),
                )
                if external.get("session_id"):
                    self._db.voice_callback_sessions.update_one(
                        {"session_id": session_id},
                        {"$set": {"external_session_id": external["session_id"]}},
                    )
            except VoiceBridgeError:
                pass

        return doc

    def _place_call(
        self,
        *,
        phone: str,
        session_id: str,
        context: VoiceAgentContext,
    ) -> tuple[dict, str]:
        """Return (call_result, provider_name)."""
        if self._voice.is_configured and self._voice.is_reachable(timeout=0.8):
            try:
                result = self._voice.initiate_callback_call(
                    phone=phone,
                    session_id=session_id,
                    context=context.model_dump(),
                    timeout=_CALL_SLA_MS / 1000.0,
                )
                return result, "vanguard_voice"
            except VoiceBridgeError as exc:
                logger.warning("Vanguard voice call failed, trying Twilio fallback: %s", exc)

        if not self._twilio_voice.is_configured:
            raise VoiceBridgeError(
                "Voice platform unreachable and Twilio voice is not configured. "
                "Start VOICE_AGENT_BASE_URL or set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER."
            )

        from app.engagement.callback_links import (
            is_public_webhook_url,
            is_webhook_reachable,
            resolve_public_api_base,
            twilio_webhook_url,
        )

        base = resolve_public_api_base(self._settings)
        if is_public_webhook_url(base) and is_webhook_reachable(base):
            from app.engagement.voice_conversation_agent import VoiceConversationAgent
            from app.engagement.voice_twiml import build_conversation_twiml

            agent = VoiceConversationAgent(self._db, self._settings)
            opening = agent.generate_opening(session_id, context)
            gather_url = twilio_webhook_url(
                base, f"/api/engagement/voice/twiml/gather/{session_id}"
            )
            outcome_url = twilio_webhook_url(
                base, f"/api/engagement/voice/twiml/outcome/{session_id}?outcome=neutral"
            )
            twiml = build_conversation_twiml(
                say_text=opening.reply,
                gather_url=gather_url,
                outcome_url=outcome_url,
                polly_voice=opening.polly_voice,
                polly_language=opening.polly_language,
                speech_hints=opening.speech_hints,
            )
            logger.info(
                "Twilio conversational callback (inline+gather) session=%s to=%s",
                session_id,
                phone,
            )
            result = self._twilio_voice.place_call(to=phone, twiml=twiml)
            return result, "twilio_conversational"

        from app.engagement.voice_twiml import build_simple_callback_twiml

        twiml = build_simple_callback_twiml(context)
        logger.warning(
            "Twilio one-shot callback (no gather) session=%s to=%s — "
            "start ngrok http 8000 and set ENGAGEMENT_API_BASE_URL for two-way voice",
            session_id,
            phone,
        )
        result = self._twilio_voice.place_call(to=phone, twiml=twiml)
        return result, "twilio_direct"

    def _update_session(self, session_id: str, **fields) -> None:
        fields["updated_at"] = datetime.now(timezone.utc)
        self._db.voice_callback_sessions.update_one(
            {"session_id": session_id},
            {"$set": fields},
        )

    def _fail_response(
        self,
        session_id: str,
        reason: str,
        timing: dict[str, float],
    ) -> VoiceCallbackStartResponse:
        return VoiceCallbackStartResponse(
            session_id=session_id or str(uuid4()),
            triggered=False,
            context=VoiceAgentContext(
                name="Customer",
                customer_id="",
                phone="",
            ),
            timing_ms=timing,
            reason=reason,
            message=f"Callback not started: {reason}",
        )

    def _recent_callback(self, entity_id: str, phone: str) -> bool:
        if self._settings.engagement_test_mode:
            return False
        from datetime import timedelta

        from app.engagement.callback_links import _as_utc_aware

        digits = "".join(c for c in phone if c.isdigit())[-10:]
        key = f"{entity_id}:{digits}"
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
        doc = self._db.voice_callback_dedup.find_one(
            {"dedup_key": key, "created_at": {"$gte": cutoff}}
        )
        if not doc:
            return False
        created = _as_utc_aware(doc.get("created_at"))
        return bool(created and created >= cutoff)

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
