"""Layer 5 state machine — response → KYC nudge or RM handoff."""

from __future__ import annotations

from app.config import get_settings
from app.db.mongo import MongoDatabase
from app.engagement.export_service import EngagementExportService
from app.engagement.channels.sms_channel import SMSChannel
from app.engagement.channels.whatsapp_channel import WhatsAppChannel
from app.engagement.personalize_service import PersonalizedMessage
from app.onboarding.kyc_assessment import assess_kyc_from_lead
from app.onboarding.repository import OnboardingRepository
from app.onboarding.response_parser import classify_response
from app.schemas.engagement import EngagementLeadRecord, VoiceCallOutcomeRequest
from app.schemas.onboarding import LeadResponseCaptureRequest, OnboardingProcessResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class OnboardingOrchestrator:
    """
    Lead Response Captured → Onboarding Nudge → RM Handoff

    Aligns with IDBI Innovate 2026 Layer 5 architecture.
    """

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._repo = OnboardingRepository(db)
        self._export = EngagementExportService(db)
        self._settings = get_settings()

    def process_voice_outcome(self, outcome: VoiceCallOutcomeRequest) -> OnboardingProcessResponse | None:
        if outcome.call_status.lower() in ("no-answer", "busy", "failed", "canceled"):
            return self.process_lead_response(
                LeadResponseCaptureRequest(
                    entity_id=outcome.entity_id,
                    entity_type=outcome.entity_type,
                    channel="Voice",
                    call_sid=outcome.call_sid,
                    intent=outcome.intent,
                    raw_text=outcome.transcript_preview,
                    phone=outcome.recipient,
                    response_type="no_answer",
                )
            )

        response_type = classify_response(
            response_type=outcome.outcome,
            intent=outcome.intent,
            raw_text=outcome.transcript_preview,
            call_status=outcome.call_status,
        )
        name = None
        if outcome.metadata:
            name = outcome.metadata.get("customer_name")
        return self.process_lead_response(
            LeadResponseCaptureRequest(
                entity_id=outcome.entity_id,
                entity_type=outcome.entity_type,
                channel="Voice",
                response_type=response_type,
                call_sid=outcome.call_sid,
                intent=outcome.intent,
                raw_text=outcome.transcript_preview,
                phone=outcome.recipient,
                name=name,
            )
        )

    def process_lead_response(
        self,
        request: LeadResponseCaptureRequest,
    ) -> OnboardingProcessResponse:
        response_type = classify_response(
            response_type=request.response_type,
            raw_text=request.raw_text,
            button_payload=request.button_payload,
            intent=request.intent,
        )

        lead_doc = self._load_lead_doc(request.entity_id, request.entity_type)
        kyc_readiness, kyc_missing = assess_kyc_from_lead(
            lead_doc, db=self._db, entity_id=request.entity_id
        )
        record = self._build_record(request, lead_doc)
        product = record.recommended_product

        response_id = self._repo.save_lead_response(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            channel=request.channel,
            response_type=response_type,
            raw_text=request.raw_text,
            button_payload=request.button_payload,
            call_sid=request.call_sid,
            intent=request.intent,
        )

        next_action = "recorded"
        journey_status = "open"
        handoff_id: str | None = None
        nudge_sent = False
        nudge_channel: str | None = None

        if response_type == "declined":
            journey_status = "closed_declined"
            next_action = "journey_closed"
        elif response_type == "no_answer":
            journey_status = "awaiting_contact"
            next_action = "retry_outreach"
        elif response_type in ("interested", "callback_requested"):
            if kyc_readiness == "Ready" or response_type == "callback_requested":
                handoff_id = self._repo.create_handoff(
                    entity_id=request.entity_id,
                    entity_type=request.entity_type,
                    customer_name=record.name,
                    phone=record.phone,
                    product=product,
                    priority="high" if response_type == "callback_requested" else "normal",
                    reason=self._handoff_reason(response_type, product),
                    source_channel=request.channel,
                    talking_points=record.talking_points,
                    call_sid=request.call_sid,
                )
                journey_status = "handoff_pending"
                next_action = "rm_handoff_created"
                if not request.dry_run and response_type != "callback_requested":
                    nudge_sent, nudge_channel = self._send_rm_confirmation(record)
            else:
                if not request.dry_run:
                    nudge_sent, nudge_channel = self._send_kyc_nudge(
                        record, kyc_readiness, kyc_missing
                    )
                journey_status = "kyc_nudge_sent"
                next_action = "kyc_nudge"
        elif response_type == "neutral":
            journey_status = "engaged"
            next_action = "monitor"
        else:
            journey_status = "open"
            next_action = "awaiting_clear_signal"

        journey_id = self._repo.upsert_journey(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            status=journey_status,
            kyc_readiness=kyc_readiness,
            kyc_missing_items=kyc_missing,
            last_response_type=response_type,
            last_channel=request.channel,
            product=product,
            handoff_id=handoff_id,
            increment_nudge=nudge_sent,
        )

        activation_id = None
        if not request.dry_run and journey_status == "handoff_pending":
            activation_id = self._start_activation_journey(request, record)

        voice_trigger = None
        if not request.dry_run:
            voice_trigger = self._maybe_voice_callback(request, response_type, record)
            if voice_trigger and voice_trigger.get("triggered"):
                next_action = "voice_callback_initiated"
                nudge_sent, nudge_channel = self._send_voice_callback_confirmation(
                    record, request.channel
                )

        response = OnboardingProcessResponse(
            message=f"Lead response processed — {next_action}",
            response_id=response_id,
            journey_id=journey_id,
            response_type=response_type,
            kyc_readiness=kyc_readiness,
            journey_status=journey_status,
            next_action=next_action,
            handoff_id=handoff_id,
            nudge_sent=nudge_sent,
            nudge_channel=nudge_channel,
            activation_id=activation_id,
        )
        if voice_trigger:
            response.message = (
                f"{response.message} Voice AI callback "
                f"{'placed' if voice_trigger.get('triggered') else 'skipped'}."
            )
        return response

    def _maybe_voice_callback(
        self,
        request: LeadResponseCaptureRequest,
        response_type: str,
        record: EngagementLeadRecord,
    ) -> dict | None:
        try:
            from app.engagement.contact_voice import ContactVoiceTrigger

            return ContactVoiceTrigger(self._db).maybe_trigger_from_response(
                request,
                response_type=response_type,
                record=record,
            )
        except Exception as exc:
            logger.warning("Voice callback trigger failed: %s", exc)
            return None

    def _start_activation_journey(
        self,
        request: LeadResponseCaptureRequest,
        record: EngagementLeadRecord,
    ) -> str | None:
        try:
            from app.activation.repository import ActivationRepository

            repo = ActivationRepository(self._db)
            return repo.start(
                entity_id=request.entity_id,
                entity_type=request.entity_type,
                phone=record.phone or request.phone or "",
                product=record.recommended_product,
            )
        except Exception as exc:
            logger.warning("Activation start skipped: %s", exc)
            return None

    def _load_lead_doc(self, entity_id: str, entity_type: str) -> dict | None:
        if entity_id.startswith("phone:"):
            digits = entity_id.split(":", 1)[-1]
            return self._db.external_leads.find_one(
                {"phone_number": {"$regex": digits[-10:]}}
            )
        if entity_type.lower() == "external":
            return self._db.external_leads.find_one({"lead_id": str(entity_id)})
        return self._db.customers.find_one({"customer_id": str(entity_id)})

    def _build_record(
        self,
        request: LeadResponseCaptureRequest,
        lead_doc: dict | None,
    ) -> EngagementLeadRecord:
        record = self._export.build_record_for_entity(
            request.entity_id, request.entity_type
        )
        if record:
            if request.phone or request.name:
                return record.model_copy(
                    update={
                        "phone": request.phone or record.phone,
                        "name": request.name or record.name,
                    }
                )
            return record

        if lead_doc:
            return EngagementLeadRecord(
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                phone=request.phone or lead_doc.get("phone_number", ""),
                name=request.name or lead_doc.get("full_name", "Customer"),
                email=lead_doc.get("email"),
                recommended_product="Personal Loan",
                consent=bool(lead_doc.get("consent")),
            )

        return EngagementLeadRecord(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            phone=request.phone or "",
            name=request.name or "Customer",
            recommended_product="Personal Loan",
            consent=True,
        )

    def _handoff_reason(self, response_type: str, product: str | None) -> str:
        product_label = product or "lending offer"
        if response_type == "callback_requested":
            return f"Customer requested a callback regarding {product_label}"
        return f"Customer expressed interest in {product_label}"

    def _send_kyc_nudge(
        self,
        record: EngagementLeadRecord,
        kyc_readiness: str,
        missing: list[str],
    ) -> tuple[bool, str | None]:
        bank = self._settings.engagement_bank_name
        missing_text = ", ".join(missing[:4]) if missing else "required documents"
        if kyc_readiness == "Partially Ready":
            body = (
                f"Dear {record.name}, thank you for your interest in {bank}'s "
                f"{record.recommended_product or 'loan'} offer. To proceed, please upload "
                f"{missing_text} via the IDBI mobile app or visit your nearest branch. "
                f"Reply if you need assistance."
            )
        else:
            body = (
                f"Dear {record.name}, thank you for connecting with {bank}. "
                f"To complete your application, we need: {missing_text}. "
                f"Our team will guide you through the next steps."
            )

        channel = "WhatsApp" if record.phone else "SMS"
        result = self._send_custom_message(record, channel, body)
        return result.success, channel if result.success else None

    def _send_voice_callback_confirmation(
        self,
        record: EngagementLeadRecord,
        source_channel: str,
    ) -> tuple[bool, str | None]:
        bank = self._settings.engagement_bank_name
        body = (
            f"Dear {record.name}, thank you for reaching out to {bank}. "
            f"Our AI voice banking specialist is calling you now — please answer the incoming call. "
            f"We will discuss your {record.recommended_product or 'lending'} offer in your preferred language."
        )
        channel = source_channel if source_channel in ("WhatsApp", "SMS") else "SMS"
        result = self._send_custom_message(record, channel, body)
        if not result.success and channel != "WhatsApp":
            result = self._send_custom_message(record, "WhatsApp", body)
            channel = "WhatsApp"
        return result.success, channel if result.success else None

    def _send_rm_confirmation(self, record: EngagementLeadRecord) -> tuple[bool, str | None]:
        bank = self._settings.engagement_bank_name
        rm_phone = self._settings.engagement_callback_phone or "1800-209-435"
        body = (
            f"Dear {record.name}, thank you for your interest in {bank}'s "
            f"{record.recommended_product or 'loan'} offer. "
            f"A Relationship Manager will contact you shortly. "
            f"You may also reach us at {rm_phone}."
        )
        channel = "SMS"
        result = self._send_custom_message(record, channel, body)
        if not result.success:
            result = self._send_custom_message(record, "WhatsApp", body)
            channel = "WhatsApp"
        return result.success, channel if result.success else None

    def _send_custom_message(
        self,
        record: EngagementLeadRecord,
        channel: str,
        body: str,
    ):
        msg = PersonalizedMessage(
            sms_body=body,
            whatsapp_body=body,
            email_subject="IDBI Bank — Next Steps",
            email_text=body,
            email_html=f"<p>{body}</p>",
        )
        if channel == "SMS":
            result = SMSChannel().send(record, msg)
        else:
            result = WhatsAppChannel().send(record, msg)
        if result.success:
            try:
                from app.engagement.conversation_service import ConversationService

                ConversationService(self._db).record_outbound(
                    entity_id=record.entity_id,
                    entity_type=record.entity_type,
                    channel=channel,
                    body=body,
                    provider_sid=result.provider_sid,
                )
            except Exception:
                pass
        return result
