"""Send rich WhatsApp messages (image, list, carousel, buttons)."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.channels.phone_utils import to_whatsapp_address
from app.engagement.channels.twilio_client import TwilioMessagingClient
from app.engagement.whatsapp.content_builder import WhatsAppContentBuilder
from app.engagement.whatsapp.message_types import WhatsAppMessageType
from app.schemas.engagement import EngagementLeadRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class WhatsAppRichSender:
    def __init__(
        self,
        settings: Settings | None = None,
        twilio: TwilioMessagingClient | None = None,
        content_builder: WhatsAppContentBuilder | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._twilio = twilio or TwilioMessagingClient(self._settings)
        self._content = content_builder or WhatsAppContentBuilder(self._settings)

    def send(
        self,
        record: EngagementLeadRecord,
        message_type: WhatsAppMessageType,
    ) -> ChannelDeliveryResult:
        from app.engagement.test_routing import TestRecipientRouter

        router = TestRecipientRouter(self._settings)
        to_addr = (
            router.whatsapp_to(record.phone)
            if router.enabled
            else to_whatsapp_address(record.phone)
        )
        if not to_addr:
            return self._fail(record, "", "Invalid phone number")

        from_addr = self._format_from()
        if message_type == WhatsAppMessageType.WELCOME:
            return self._send_welcome(record, to_addr, from_addr)
        if message_type == WhatsAppMessageType.MAIN_MENU:
            return self._send_content_or_fallback(
                record, to_addr, from_addr,
                content_sid=self._settings.whatsapp_content_main_menu,
                variables=self._content.main_menu_variables(record),
                fallback_body=self._content.main_menu_fallback_text(record),
                meta_type="list",
            )
        if message_type in (WhatsAppMessageType.LOAN_MEDIA, WhatsAppMessageType.LOAN_CAROUSEL):
            return self._send_content_or_fallback(
                record, to_addr, from_addr,
                content_sid=self._settings.whatsapp_content_loan_media,
                variables=self._content.loan_media_variables(record),
                fallback_body=self._content.loan_media_fallback_text(record),
                meta_type="media",
            )
        if message_type == WhatsAppMessageType.PREAPPROVED_BUTTONS:
            return self._send_content_or_fallback(
                record, to_addr, from_addr,
                content_sid=self._settings.whatsapp_content_preapproved_buttons,
                variables=self._content.preapproved_buttons_variables(record),
                fallback_body=self._content.preapproved_fallback_text(record),
                meta_type="quick-reply",
            )
        if message_type == WhatsAppMessageType.CREDIT_CARD_OFFER:
            return self._send_content_or_fallback(
                record, to_addr, from_addr,
                content_sid=self._settings.whatsapp_content_credit_card_offer,
                variables=self._content.credit_card_offer_variables(record),
                fallback_body=self._content.credit_card_offer_fallback_text(record),
                meta_type="quick-reply",
            )
        return self._fail(record, to_addr, f"Unsupported message type: {message_type}")

    def _send_welcome(
        self, record: EngagementLeadRecord, to_addr: str, from_addr: str
    ) -> ChannelDeliveryResult:
        caption = self._content.welcome_caption(record)
        media_url = self._settings.whatsapp_welcome_media_url

        if media_url:
            ok, sid, status_or_error = self._twilio.send_whatsapp_media(
                to=to_addr,
                from_=from_addr,
                body=caption,
                media_url=media_url,
            )
            mode = "image_caption"
        else:
            ok, sid, status_or_error = self._twilio.send_whatsapp(
                to=to_addr,
                from_=from_addr,
                body=f"🖼️ {caption}",
            )
            mode = "text_welcome_no_image"

        return ChannelDeliveryResult(
            channel="WhatsApp",
            success=ok,
            entity_id=record.entity_id,
            recipient=to_addr,
            provider_sid=sid,
            status=status_or_error if ok else "failed",
            error=None if ok else status_or_error,
            metadata={"message_type": "welcome", "mode": mode},
        )

    def _send_content_or_fallback(
        self,
        record: EngagementLeadRecord,
        to_addr: str,
        from_addr: str,
        *,
        content_sid: str,
        variables: dict[str, str],
        fallback_body: str,
        meta_type: str,
    ) -> ChannelDeliveryResult:
        if content_sid:
            ok, sid, status_or_error = self._twilio.send_whatsapp(
                to=to_addr,
                from_=from_addr,
                content_sid=content_sid,
                content_variables=variables,
            )
            mode = f"content_{meta_type}"
        else:
            logger.info(
                "No Content SID for %s — sending structured text fallback", meta_type
            )
            ok, sid, status_or_error = self._twilio.send_whatsapp(
                to=to_addr,
                from_=from_addr,
                body=fallback_body,
            )
            mode = f"text_fallback_{meta_type}"

        return ChannelDeliveryResult(
            channel="WhatsApp",
            success=ok,
            entity_id=record.entity_id,
            recipient=to_addr,
            provider_sid=sid,
            status=status_or_error if ok else "failed",
            error=None if ok else status_or_error,
            metadata={"message_type": meta_type, "mode": mode, "variables": variables},
        )

    def _format_from(self) -> str:
        from_addr = self._settings.twilio_whatsapp_from
        if from_addr.startswith("whatsapp:"):
            return from_addr
        return f"whatsapp:+{from_addr.lstrip('+')}"

    @staticmethod
    def _fail(record: EngagementLeadRecord, recipient: str, error: str) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(
            channel="WhatsApp",
            success=False,
            entity_id=record.entity_id,
            recipient=recipient,
            status="failed",
            error=error,
        )
