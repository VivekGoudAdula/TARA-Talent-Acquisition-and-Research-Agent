"""WhatsApp rich message types for IDBI AI Banking engagement."""

from __future__ import annotations

from enum import Enum

from app.schemas.engagement import EngagementLeadRecord


class WhatsAppMessageType(str, Enum):
    WELCOME = "welcome"           # Image + caption
    MAIN_MENU = "main_menu"       # List message
    LOAN_MEDIA = "loan_media"  # Media image + loan offer body
    LOAN_CAROUSEL = "loan_carousel"  # Alias for loan_media (backward compat)
    PREAPPROVED_BUTTONS = "preapproved_buttons"  # Rich buttons
    CREDIT_CARD_OFFER = "credit_card_offer"  # Quick reply credit card
    TEXT = "text"                 # Plain custom text fallback


def resolve_whatsapp_message_type(
    record: EngagementLeadRecord,
    override: str | None = None,
) -> WhatsAppMessageType:
    if override:
        key = override.lower()
        if key == "loan_carousel":
            return WhatsAppMessageType.LOAN_MEDIA
        try:
            return WhatsAppMessageType(key)
        except ValueError:
            return WhatsAppMessageType.TEXT

    conv = record.conversion_probability or 0
    products = record.product_recommendations or []

    if conv >= 70 and record.recommended_product:
        return WhatsAppMessageType.PREAPPROVED_BUTTONS
    if record.recommended_product or len(products) >= 1:
        return WhatsAppMessageType.LOAN_MEDIA
    return WhatsAppMessageType.WELCOME
