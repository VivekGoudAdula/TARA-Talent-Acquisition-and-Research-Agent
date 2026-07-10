"""Multi-channel engagement orchestrator — Personalize & Sequence."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.channels.email_channel import EmailChannel
from app.engagement.channels.sms_channel import SMSChannel
from app.engagement.channels.voice_channel import VoiceChannel
from app.engagement.channels.whatsapp_channel import WhatsAppChannel
from app.engagement.channels.other_channels import (
    InAppChannel,
    IvrMissedCallChannel,
    PushNotificationChannel,
)
from app.engagement.export_service import EngagementExportService
from app.engagement.personalize_service import PersonalizeService
from app.engagement.repository import EngagementRepository
from app.schemas.engagement import EngagementLeadRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

CHANNEL_ALIASES = {
    "voice": "Voice",
    "phone": "Voice",
    "call": "Voice",
    "whatsapp": "WhatsApp",
    "wa": "WhatsApp",
    "sms": "SMS",
    "text": "SMS",
    "mobile app": "WhatsApp",
    "email": "Email",
    "mail": "Email",
    "push": "Push",
    "in-app": "InApp",
    "inapp": "InApp",
    "notification": "Push",
    "ivr": "IVR",
    "missed call": "IVR",
    "branch": "SMS",
    "relationship manager": "SMS",
    "social": "Push",
}

FALLBACK_SEQUENCE = ["WhatsApp", "SMS", "Email", "Push", "IVR", "Voice"]
DEFAULT_CHANNEL = "WhatsApp"


@dataclass
class OutreachRunResult:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    by_channel: dict[str, int] = field(default_factory=dict)
    results: list[ChannelDeliveryResult] = field(default_factory=list)
    voice_campaign_id: int | None = None
    dry_run: bool = False
    sequences_created: int = 0


class EngagementOrchestrator:
    """
    Agent: Personalize & Sequence.

    Routes each lead to the best channel using preferred_channel from Tara intelligence,
    with fallback ordering WhatsApp → SMS → Email → Voice (Voice only when explicitly requested).
    """

    def __init__(
        self,
        export_service: EngagementExportService,
        repository: EngagementRepository,
        personalize: PersonalizeService | None = None,
        voice: VoiceChannel | None = None,
        sms: SMSChannel | None = None,
        whatsapp: WhatsAppChannel | None = None,
        email: EmailChannel | None = None,
        push: PushNotificationChannel | None = None,
        inapp: InAppChannel | None = None,
        ivr: IvrMissedCallChannel | None = None,
    ) -> None:
        self._export = export_service
        self._repo = repository
        self._personalize = personalize or PersonalizeService()
        self._voice = voice or VoiceChannel()
        self._sms = sms or SMSChannel()
        self._whatsapp = whatsapp or WhatsAppChannel()
        self._email = email or EmailChannel()
        self._push = push or PushNotificationChannel()
        self._inapp = inapp or InAppChannel()
        self._ivr = ivr or IvrMissedCallChannel()

    def resolve_channel(
        self,
        record: EngagementLeadRecord,
        override: str | None = None,
        *,
        allow_voice: bool = False,
    ) -> str:
        if override:
            key = override.strip().lower()
            resolved = CHANNEL_ALIASES.get(key, override.strip().title())
            if resolved == "Voice" and not allow_voice:
                return DEFAULT_CHANNEL
            return resolved

        preferred = (record.preferred_channel or "").strip()
        if preferred:
            key = preferred.lower()
            if key in CHANNEL_ALIASES:
                resolved = CHANNEL_ALIASES[key]
            elif preferred in FALLBACK_SEQUENCE:
                resolved = preferred
            elif key in ("branch", "relationship manager"):
                resolved = "SMS"
            else:
                resolved = DEFAULT_CHANNEL
            if resolved == "Voice" and not allow_voice:
                return DEFAULT_CHANNEL
            return resolved

        return DEFAULT_CHANNEL

    def channel_status(self) -> dict[str, dict]:
        return {
            "Voice": {
                "configured": self._voice.is_configured,
                "detail": self._voice.health(),
            },
            "SMS": {"configured": self._sms.is_configured},
            "WhatsApp": {"configured": self._whatsapp.is_configured},
            "Email": {"configured": self._email.is_configured},
            "Push": {"configured": self._push.is_configured, "simulated": True},
            "InApp": {"configured": self._inapp.is_configured, "simulated": True},
            "IVR": {"configured": self._ivr.is_configured, "simulated": True},
        }

    def send_one(
        self,
        record: EngagementLeadRecord,
        *,
        channel: str | None = None,
        dry_run: bool = False,
        whatsapp_message_type: str | None = None,
    ) -> ChannelDeliveryResult:
        resolved = self.resolve_channel(record, channel)
        message = self._personalize.build(record)

        if dry_run:
            preview = message.sms_body[:120]
            meta: dict = {"preview": preview}
            if resolved == "WhatsApp":
                from app.engagement.whatsapp.message_types import resolve_whatsapp_message_type
                mt = resolve_whatsapp_message_type(record, whatsapp_message_type)
                meta["whatsapp_message_type"] = mt.value
            return ChannelDeliveryResult(
                channel=resolved,
                success=True,
                entity_id=record.entity_id,
                recipient=record.phone if resolved != "Email" else (record.email or ""),
                status="dry_run",
                metadata=meta,
            )

        if resolved == "Voice":
            return ChannelDeliveryResult(
                channel="Voice",
                success=False,
                entity_id=record.entity_id,
                recipient=record.phone,
                status="skipped",
                error="Use run_outreach with channel=Voice for batch voice campaigns",
            )

        if resolved == "SMS":
            result = self._sms.send(record, message)
        elif resolved == "WhatsApp":
            result = self._whatsapp.send(
                record, message, message_type=whatsapp_message_type
            )
        elif resolved == "Email":
            result = self._email.send(record, message)
        elif resolved == "Push":
            result = self._push.send(record, message)
        elif resolved == "InApp":
            result = self._inapp.send(record, message)
        elif resolved == "IVR":
            result = self._ivr.send(record, message)
        else:
            result = ChannelDeliveryResult(
                channel=resolved,
                success=False,
                entity_id=record.entity_id,
                recipient="",
                status="failed",
                error=f"Unsupported channel: {resolved}",
            )

        preview = message.sms_body[:160] if resolved != "Email" else message.email_subject
        self._repo.save_event(
            entity_id=record.entity_id,
            entity_type=record.entity_type,
            channel=resolved,
            result=result,
            message_preview=preview,
        )
        if result.success and not dry_run:
            self._record_conversation_outbound(record, resolved, message, result)
        return result

    def _record_conversation_outbound(
        self,
        record: EngagementLeadRecord,
        channel: str,
        message,
        result: ChannelDeliveryResult,
    ) -> None:
        try:
            from app.engagement.conversation_service import ConversationService

            body = message.sms_body
            if channel == "WhatsApp":
                body = message.whatsapp_body
            elif channel == "Email":
                body = message.email_text or message.email_subject
            ConversationService(self._export._db).record_outbound(
                entity_id=record.entity_id,
                entity_type=record.entity_type,
                channel=channel,
                body=body,
                provider_sid=result.provider_sid,
                metadata={"status": result.status, "recipient": result.recipient},
            )
        except Exception as exc:
            logger.debug("Conversation outbound log skipped: %s", exc)

    def run_outreach(
        self,
        records: list[EngagementLeadRecord],
        *,
        channel: str | None = None,
        dry_run: bool = False,
        campaign_name: str = "Tara Multi-Channel Outreach",
        agent_id: str = "lending_offer_agent",
        start_voice_campaign: bool = False,
    ) -> OutreachRunResult:
        run = OutreachRunResult(total=len(records), dry_run=dry_run)
        if not records:
            return run

        resolved = self.resolve_channel(records[0], channel) if channel else None
        allow_voice = bool(
            channel and channel.strip().lower() in ("voice", "phone", "call")
        )

        if resolved == "Voice" or allow_voice:
            return self._run_voice_batch(
                records,
                campaign_name=campaign_name,
                agent_id=agent_id,
                start_campaign=start_voice_campaign,
                dry_run=dry_run,
            )

        if channel is None:
            return self._run_per_lead_outreach(records, dry_run=dry_run, allow_voice=False)

        target_channel = resolved
        for record in records:
            result = self.send_one(record, channel=target_channel, dry_run=dry_run)
            run.results.append(result)
            ch = result.channel
            run.by_channel[ch] = run.by_channel.get(ch, 0) + 1
            if result.success:
                run.succeeded += 1
            elif result.status == "skipped":
                run.skipped += 1
            else:
                run.failed += 1

        logger.info(
            "Outreach complete channel=%s total=%d ok=%d failed=%d dry_run=%s",
            target_channel,
            run.total,
            run.succeeded,
            run.failed,
            dry_run,
        )
        return run

    def _run_per_lead_outreach(
        self,
        records: list[EngagementLeadRecord],
        *,
        dry_run: bool,
        allow_voice: bool = False,
    ) -> OutreachRunResult:
        run = OutreachRunResult(total=len(records), dry_run=dry_run)
        voice_records: list[EngagementLeadRecord] = []
        for record in records:
            ch = self.resolve_channel(record, allow_voice=allow_voice)
            if ch == "Voice":
                voice_records.append(record)
                continue
            result = self.send_one(record, channel=ch, dry_run=dry_run)
            run.results.append(result)
            run.by_channel[ch] = run.by_channel.get(ch, 0) + 1
            if result.success:
                run.succeeded += 1
            elif result.status == "skipped":
                run.skipped += 1
            else:
                run.failed += 1

        if voice_records:
            voice_run = self._run_voice_batch(
                voice_records,
                campaign_name="Tara Voice Outreach",
                agent_id="lending_offer_agent",
                start_campaign=False,
                dry_run=dry_run,
            )
            run.results.extend(voice_run.results)
            run.by_channel["Voice"] = run.by_channel.get("Voice", 0) + len(voice_records)
            run.succeeded += voice_run.succeeded
            run.failed += voice_run.failed
            run.voice_campaign_id = voice_run.voice_campaign_id

        return run

    def _run_voice_batch(
        self,
        records: list[EngagementLeadRecord],
        *,
        campaign_name: str,
        agent_id: str,
        start_campaign: bool,
        dry_run: bool,
    ) -> OutreachRunResult:
        run = OutreachRunResult(total=len(records), dry_run=dry_run)

        if dry_run:
            for record in records:
                run.results.append(
                    ChannelDeliveryResult(
                        channel="Voice",
                        success=True,
                        entity_id=record.entity_id,
                        recipient=record.phone,
                        status="dry_run",
                    )
                )
            run.succeeded = len(records)
            run.by_channel["Voice"] = len(records)
            return run

        self._voice.raise_if_not_ready()
        csv_text = self._export.records_to_csv_text(records)
        push = self._voice.push_campaign(
            records=records,
            campaign_name=campaign_name,
            agent_id=agent_id,
            csv_text=csv_text,
            start_campaign=start_campaign,
        )
        run.voice_campaign_id = push.get("campaign_id")
        run.by_channel["Voice"] = len(records)
        run.succeeded = len(records)

        for record in records:
            result = self._voice.to_delivery_result(
                record,
                queued=True,
                detail=f"campaign_id={run.voice_campaign_id}",
            )
            run.results.append(result)
            self._repo.save_event(
                entity_id=record.entity_id,
                entity_type=record.entity_type,
                channel="Voice",
                result=result,
                campaign_id=str(run.voice_campaign_id) if run.voice_campaign_id else None,
                message_preview=record.recommended_product,
            )
        return run
