from __future__ import annotations

import time
from pathlib import Path
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.engagement.export_service import EngagementExportService
from app.engagement.orchestrator import EngagementOrchestrator, OutreachRunResult
from app.engagement.personalize_service import PersonalizeService
from app.engagement.repository import EngagementRepository
from app.engagement.voice_bridge import VoiceBridge, VoiceBridgeError
from app.api.ui_adapters import adapt_channel_status, adapt_engagement_lead
from app.schemas.engagement import (
    ChannelDeliveryResultResponse,
    ChannelStatusResponse,
    CustomSendRequest,
    CustomSendResponse,
    EngagementExportResponse,
    EngagementLeadRecord,
    OutreachRequest,
    OutreachResponse,
    VoiceCallOutcomeRequest,
    VoiceCallOutcomeResponse,
    VoiceCampaignRequest,
    VoiceCampaignResponse,
)


_PREVIEW_CACHE_TTL_SEC = 90
_preview_cache: dict[tuple, tuple[float, list[EngagementLeadRecord]]] = {}


class EngagementService:
    """Coordinates export, personalization, and multi-channel delivery."""

    def __init__(self, db: MongoDatabase, voice_bridge: VoiceBridge | None = None) -> None:
        self._db = db
        self._export = EngagementExportService(db)
        self._repo = EngagementRepository(db)
        self._voice = voice_bridge or VoiceBridge()
        self._orchestrator = EngagementOrchestrator(
            self._export,
            self._repo,
            personalize=PersonalizeService(db=db),
        )

    def export_leads(
        self,
        output_path: Path,
        *,
        profile_types: list[str] | None = None,
        limit: int | None = None,
        min_conversion_probability: float | None = None,
    ) -> EngagementExportResponse:
        result = self._export.export_csv(
            output_path,
            profile_types=profile_types,
            limit=limit,
            min_conversion_probability=min_conversion_probability,
        )
        return EngagementExportResponse(
            message="Engagement leads exported successfully",
            file_path=str(result.file_path),
            records_exported=len(result.records),
            records=result.records,
        )

    def preview_leads(
        self,
        *,
        profile_types: list[str] | None = None,
        limit: int | None = 10,
        min_conversion_probability: float | None = None,
    ) -> list[EngagementLeadRecord]:
        types_key = tuple(sorted({t.strip().title() for t in (profile_types or ["External", "Internal"])}))
        cache_key = (types_key, limit, min_conversion_probability)
        cached = _preview_cache.get(cache_key)
        if cached and (time.time() - cached[0]) < _PREVIEW_CACHE_TTL_SEC:
            return cached[1]

        records = self._export.build_preview_records(
            profile_types=profile_types,
            limit=limit or 20,
            min_conversion_probability=min_conversion_probability,
        )
        result = [EngagementLeadRecord(**adapt_engagement_lead(r.model_dump(mode="json"))) for r in records]
        _preview_cache[cache_key] = (time.time(), result)
        return result

    def channel_status(self) -> ChannelStatusResponse:
        raw = self._orchestrator.channel_status()
        adapted = adapt_channel_status(raw)
        return ChannelStatusResponse(channels=adapted["channels"])

    def voice_health(self) -> dict:
        from app.config import get_settings
        from app.engagement.channels.twilio_voice import TwilioVoiceClient

        settings = get_settings()
        return {
            "vanguard_voice": self._voice.health_check(),
            "twilio_voice_configured": TwilioVoiceClient(settings).is_configured,
        }

    def run_outreach(self, request: OutreachRequest) -> OutreachResponse:
        records = self._export.build_records(
            profile_types=request.profile_types,
            limit=request.limit,
            offset=request.offset,
            min_conversion_probability=request.min_conversion_probability,
            require_consent=request.require_consent,
        )
        run = self._orchestrator.run_outreach(
            records,
            channel=request.channel,
            dry_run=request.dry_run,
            campaign_name=request.campaign_name,
            agent_id=request.agent_id,
            start_voice_campaign=request.start_voice_campaign,
        )
        if request.auto_sequence and records:
            from app.engagement.sequence_service import EngagementSequenceService

            seq_svc = EngagementSequenceService(self._db, self._orchestrator)
            for rec in records:
                seq_svc.create_sequence(rec.entity_id, entity_type=rec.entity_type)
                run.sequences_created += 1
        return self._to_outreach_response(run)

    def send_custom(self, request: CustomSendRequest) -> CustomSendResponse:
        """Send one custom personalized message to any phone (e.g. sandbox testing)."""
        record = self._build_record_for_custom_send(request)
        personalize = PersonalizeService(db=self._db)
        msg = personalize.build(record)

        if request.message:
            msg.whatsapp_body = request.message
            msg.sms_body = request.message
            msg.email_text = request.message

        preview = (
            msg.whatsapp_body
            if request.channel.lower() in ("whatsapp", "wa")
            else msg.email_subject
            if request.channel.lower() == "email"
            else msg.sms_body
        )

        if request.dry_run:
            result = self._orchestrator.send_one(
                record,
                channel=request.channel,
                dry_run=True,
                whatsapp_message_type=request.whatsapp_message_type,
            )
            return CustomSendResponse(
                message="Dry run — message not sent",
                result=self._to_result_response(result),
                personalized_text=preview,
            )

        result = self._orchestrator.send_one(
            record,
            channel=request.channel,
            dry_run=False,
            whatsapp_message_type=request.whatsapp_message_type,
        )
        return CustomSendResponse(
            message="Custom message sent" if result.success else "Send failed",
            result=self._to_result_response(result),
            personalized_text=preview,
        )

    def _build_record_for_custom_send(self, request: CustomSendRequest) -> EngagementLeadRecord:
        if request.use_tara_intelligence:
            record = None
            try:
                # Try External lead first
                record = self._export.build_record_for_entity(f"phone:{request.phone}", "External")
                if not record:
                    # Try Internal customer search by phone in Mongo
                    cust_doc = self._db.customers.find_one({"phone_number": {"$regex": request.phone[-10:]}})
                    if cust_doc:
                        record = self._export.build_record_for_entity(cust_doc["customer_id"], "Internal")
            except Exception as exc:
                from app.utils.logging_config import get_logger
                get_logger(__name__).warning("Custom send lead lookup by phone failed: %s", exc)

            if record:
                return record.model_copy(
                    update={
                        "phone": request.phone,
                        "name": request.name or record.name,
                        "email": request.email or record.email,
                    }
                )

            # Fallback to top scored lead
            leads = self._export.build_records(limit=1)
            if leads:
                base = leads[0]
                return base.model_copy(
                    update={
                        "phone": request.phone,
                        "name": request.name,
                        "email": request.email or base.email,
                        "entity_id": str(uuid4()),
                    }
                )
        return EngagementLeadRecord(
            entity_type="Test",
            entity_id=str(uuid4()),
            phone=request.phone,
            name=request.name,
            email=request.email,
            recommended_product="Personal Loan",
            consent=True,
        )

    def get_events_for_entity(self, entity_id: UUID | str) -> list[dict]:
        return self._repo.get_by_entity(entity_id)

    def record_voice_call_outcome(self, request: VoiceCallOutcomeRequest) -> dict:
        event_id = self._repo.save_voice_call_outcome(
            call_sid=request.call_sid,
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            recipient=request.recipient,
            call_status=request.call_status,
            duration_seconds=request.duration_seconds,
            agent_id=request.agent_id,
            direction=request.direction,
            intent=request.intent,
            transcript_preview=request.transcript_preview,
            campaign_lead_id=request.campaign_lead_id,
            metadata=request.metadata,
        )
        onboarding_result = None
        try:
            from app.onboarding.service import OnboardingService

            onboarding_result = OnboardingService(self._db).process_voice_outcome(request)
        except Exception as exc:
            from app.utils.logging_config import get_logger

            get_logger(__name__).warning("Layer 5 onboarding after voice outcome failed: %s", exc)

        result = {"message": "Voice call outcome recorded", "event_id": event_id}
        if onboarding_result:
            result["onboarding"] = onboarding_result.model_dump()
        return result

    def push_voice_campaign(
        self,
        request: VoiceCampaignRequest,
        *,
        output_dir: Path,
    ) -> VoiceCampaignResponse:
        records = self._export.build_records(
            profile_types=request.profile_types,
            limit=request.limit,
            min_conversion_probability=request.min_conversion_probability,
        )
        if not records:
            raise VoiceBridgeError("No engagement records matched the filters")

        csv_path = output_dir / "tara_engagement_leads.csv"
        export_result = self._export.export_csv(
            csv_path,
            profile_types=request.profile_types,
            limit=request.limit,
            min_conversion_probability=request.min_conversion_probability,
        )
        csv_text = self._export.records_to_csv_text(export_result.records)

        push_result = self._voice.push_campaign(
            records=records,
            campaign_name=request.campaign_name,
            agent_id=request.agent_id,
            csv_text=csv_text,
            start_campaign=request.start_campaign,
        )

        return VoiceCampaignResponse(
            message="Voice campaign created and leads uploaded",
            campaign_id=push_result.get("campaign_id"),
            campaign_name=request.campaign_name,
            agent_id=request.agent_id,
            leads_pushed=push_result.get("leads_pushed", len(records)),
            upload_result=push_result.get("upload_result"),
            dialer_result=push_result.get("dialer_result"),
            file_path=str(csv_path),
        )

    def start_ai_callback(
        self,
        *,
        phone: str,
        entity_id: str,
        entity_type: str = "External",
        name: str | None = None,
        campaign: str | None = None,
        source_channel: str | None = None,
    ):
        from app.engagement.callback_orchestrator import CallbackOrchestrator

        return CallbackOrchestrator(self._db, voice_bridge=self._voice).start_callback(
            phone=phone,
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            campaign=campaign,
            source_channel=source_channel,
        )

    def get_callback_session_context(self, session_id: str):
        from app.engagement.callback_orchestrator import CallbackOrchestrator

        return CallbackOrchestrator(self._db, voice_bridge=self._voice).get_session_context(
            session_id
        )

    def run_voice_callback(
        self,
        phone: str,
        entity_id: str | None = None,
        entity_type: str = "External",
        *,
        source_channel: str | None = "Web",
        campaign: str | None = None,
        skip_dedup: bool = False,
    ):
        from app.engagement.callback_orchestrator import CallbackOrchestrator

        resolved_entity_id = entity_id
        if not resolved_entity_id:
            digits = "".join(c for c in phone if c.isdigit())[-10:]
            resolved_entity_id = f"phone:{digits}" if digits else None
        if not resolved_entity_id:
            from app.schemas.voice_session import VoiceAgentContext, VoiceCallbackStartResponse

            return VoiceCallbackStartResponse(
                session_id="",
                triggered=False,
                context=VoiceAgentContext(name="Customer", customer_id="", phone=phone),
                reason="entity_id is required for AI callback",
                message="Missing lead/customer id in callback link",
            )

        return CallbackOrchestrator(self._db, voice_bridge=self._voice).start_callback(
            phone=phone,
            entity_id=resolved_entity_id,
            entity_type=entity_type,
            source_channel=source_channel,
            campaign=campaign,
            skip_dedup=skip_dedup,
        )

    def trigger_voice_callback(
        self,
        phone: str,
        entity_id: str | None = None,
        entity_type: str = "External",
        *,
        source_channel: str | None = "Web",
        campaign: str | None = None,
    ) -> dict:
        result = self.run_voice_callback(
            phone=phone,
            entity_id=entity_id,
            entity_type=entity_type,
            source_channel=source_channel,
            campaign=campaign,
        )
        if not result.triggered:
            raise VoiceBridgeError(result.reason or "Callback not started")
        return {
            "session_id": result.session_id,
            "call_sid": result.call_sid,
            "call": result.call,
            "timing_ms": result.timing_ms,
            "context": result.context.model_dump(),
        }

    @staticmethod
    def _to_result_response(result) -> ChannelDeliveryResultResponse:
        return ChannelDeliveryResultResponse(
            channel=result.channel,
            success=result.success,
            entity_id=result.entity_id,
            recipient=result.recipient,
            provider_sid=result.provider_sid,
            status=result.status,
            error=result.error,
        )

    @staticmethod
    def _to_outreach_response(run: OutreachRunResult) -> OutreachResponse:
        return OutreachResponse(
            message="Engagement outreach completed",
            total=run.total,
            succeeded=run.succeeded,
            failed=run.failed,
            skipped=run.skipped,
            dry_run=run.dry_run,
            by_channel=run.by_channel,
            voice_campaign_id=run.voice_campaign_id,
            sequences_created=run.sequences_created,
            results=[
                EngagementService._to_result_response(r)
                for r in run.results
            ],
        )

    def create_sequence(self, entity_id: str, *, entity_type: str = "External") -> dict:
        from app.engagement.sequence_service import EngagementSequenceService

        seq_id = EngagementSequenceService(self._db, self._orchestrator).create_sequence(
            entity_id, entity_type=entity_type
        )
        return {"sequence_id": seq_id, "entity_id": entity_id, "status": "active"}

    def process_due_sequences(self, *, dry_run: bool = False, limit: int = 50) -> dict:
        from app.engagement.sequence_service import EngagementSequenceService

        return EngagementSequenceService(self._db, self._orchestrator).process_due_touches(
            dry_run=dry_run, limit=limit
        )

    def process_sms_inbound(self, form: dict) -> dict:
        from app.engagement.conversation_service import ConversationService

        body = (form.get("Body") or "").strip()
        sender = form.get("From") or ""
        sid = form.get("MessageSid") or form.get("SmsSid")
        return ConversationService(self._db).process_inbound(
            channel="SMS",
            body=body,
            phone=sender,
            provider_sid=sid,
        )

    def process_email_inbound(self, body: dict) -> dict:
        from app.engagement.conversation_service import ConversationService

        text = (body.get("text") or body.get("body") or "").strip()
        return ConversationService(self._db).process_inbound(
            channel="Email",
            body=text,
            email=body.get("email"),
            phone=body.get("phone"),
            entity_id=body.get("entity_id") or body.get("lead_id"),
            entity_type=body.get("entity_type", "External"),
        )

    def process_whatsapp_inbound(self, form: dict) -> dict:
        from app.engagement.conversation_service import ConversationService

        body = (form.get("Body") or "").strip()
        button = (form.get("ButtonPayload") or form.get("ButtonText") or "").strip()
        sender = form.get("From") or form.get("WaId") or ""
        sid = form.get("MessageSid") or form.get("SmsSid")
        return ConversationService(self._db).process_inbound(
            channel="WhatsApp",
            body=body or button,
            phone=sender,
            button_payload=button or None,
            provider_sid=sid,
        )

    def sync_conversation_turn(self, payload: dict) -> dict:
        from app.engagement.conversation_service import ConversationService

        return ConversationService(self._db).sync_turn(
            channel=payload.get("channel", "WhatsApp"),
            phone=payload.get("phone"),
            email=payload.get("email"),
            customer_body=payload.get("customer_body", ""),
            agent_body=payload.get("agent_body"),
            entity_id=payload.get("entity_id"),
            entity_type=payload.get("entity_type"),
            provider_sid=payload.get("provider_sid"),
            session_id=payload.get("session_id"),
        )

    def get_conversation_thread(
        self,
        entity_id: str,
        *,
        channel: str | None = None,
        limit: int = 100,
    ) -> dict:
        from app.engagement.conversation_service import ConversationService

        return ConversationService(self._db).get_thread(
            entity_id, channel=channel, limit=limit
        )

    def list_conversation_inbox(self, limit: int = 50) -> list[dict]:
        from app.engagement.conversation_service import ConversationService

        return ConversationService(self._db).list_recent_inbox(limit=limit)

    def record_cta_click(self, token: str) -> str:
        from datetime import datetime
        from uuid import uuid4

        from app.config import get_settings

        doc = self._db.email_cta_clicks.find_one({"token": token})
        settings = get_settings()
        redirect = settings.engagement_email_cta_url
        if doc:
            redirect = doc.get("target_url") or redirect
            self._db.email_cta_clicks.update_one(
                {"token": token},
                {"$inc": {"click_count": 1}, "$set": {"last_clicked_at": datetime.utcnow()}},
            )
        else:
            self._db.email_cta_clicks.insert_one(
                {
                    "click_id": str(uuid4()),
                    "token": token,
                    "target_url": redirect,
                    "click_count": 1,
                    "created_at": datetime.utcnow(),
                    "last_clicked_at": datetime.utcnow(),
                }
            )
        return redirect

    def check_sms_compliance(self, entity_id: str) -> dict:
        record = self._export.build_record_for_entity(entity_id, "External")
        if not record:
            return {"error": "Lead not found"}
        message = PersonalizeService(db=self._db).build(record)
        result = self._orchestrator._sms.compliance_check(record, message)
        return {
            "entity_id": entity_id,
            "allowed": result.allowed,
            "checks": result.checks,
            "reasons": result.reasons,
            "template_id": result.template_id,
            "sender_id": result.sender_id,
        }
