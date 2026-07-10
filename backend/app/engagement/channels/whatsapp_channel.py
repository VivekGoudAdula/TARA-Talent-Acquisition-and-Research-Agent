"""Twilio WhatsApp channel — plain text and rich messages."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.personalize_service import PersonalizedMessage
from app.engagement.whatsapp.message_types import WhatsAppMessageType, resolve_whatsapp_message_type
from app.engagement.whatsapp.rich_sender import WhatsAppRichSender
from app.engagement.channels.twilio_client import TwilioMessagingClient
from app.engagement.channels.phone_utils import to_whatsapp_address
from app.schemas.engagement import EngagementLeadRecord


class WhatsAppChannel:
    CHANNEL = "WhatsApp"

    def __init__(
        self,
        settings: Settings | None = None,
        twilio: TwilioMessagingClient | None = None,
        rich_sender: WhatsAppRichSender | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._twilio = twilio or TwilioMessagingClient(self._settings)
        self._rich = rich_sender or WhatsAppRichSender(self._settings, self._twilio)

    @property
    def is_configured(self) -> bool:
        return self._twilio.is_configured and bool(self._settings.twilio_whatsapp_from)

    def send(
        self,
        record: EngagementLeadRecord,
        message: PersonalizedMessage,
        *,
        message_type: str | None = None,
    ) -> ChannelDeliveryResult:
        resolved = resolve_whatsapp_message_type(record, message_type)

        if resolved != WhatsAppMessageType.TEXT:
            return self._rich.send(record, resolved)

        return self._send_plain_text(record, message)

    def _send_plain_text(
        self, record: EngagementLeadRecord, message: PersonalizedMessage
    ) -> ChannelDeliveryResult:
        from app.engagement.test_routing import TestRecipientRouter

        router = TestRecipientRouter(self._settings)
        original_phone = record.phone
        to_addr = (
            router.whatsapp_to(record.phone)
            if router.enabled
            else to_whatsapp_address(record.phone)
        )
        if not to_addr:
            return ChannelDeliveryResult(
                channel=self.CHANNEL,
                success=False,
                entity_id=record.entity_id,
                recipient="",
                status="failed",
                error="Invalid WhatsApp phone number",
            )

        from_addr = self._format_whatsapp_from()
        use_template = (
            self._settings.twilio_whatsapp_use_template
            and bool(self._settings.twilio_whatsapp_content_sid)
        )

        if use_template:
            ok, sid, status_or_error = self._twilio.send_whatsapp(
                to=to_addr,
                from_=from_addr,
                content_sid=self._settings.twilio_whatsapp_content_sid,
                content_variables=message.whatsapp_content_variables,
            )
            mode = "template"
        else:
            ok, sid, status_or_error = self._twilio.send_whatsapp(
                to=to_addr,
                from_=from_addr,
                body=message.whatsapp_body,
            )
            mode = "custom_body"

        return ChannelDeliveryResult(
            channel=self.CHANNEL,
            success=ok,
            entity_id=record.entity_id,
            recipient=to_addr,
            provider_sid=sid,
            status=status_or_error if ok else "failed",
            error=None if ok else status_or_error,
            metadata={
                "mode": mode,
                "original_phone": original_phone if router.enabled else None,
                "test_routed": router.enabled,
            },
        )

    def _format_whatsapp_from(self) -> str:
        from_addr = self._settings.twilio_whatsapp_from
        if not from_addr:
            return ""
        if from_addr.startswith("whatsapp:"):
            return from_addr
        digits = from_addr.lstrip("+")
        return f"whatsapp:+{digits}"
