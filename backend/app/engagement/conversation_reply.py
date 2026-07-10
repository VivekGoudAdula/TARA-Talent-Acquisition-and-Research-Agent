"""Build conversational agent replies for inbound WhatsApp / SMS / Email."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.onboarding.response_parser import is_contact_intent
from app.schemas.engagement import EngagementLeadRecord
from app.schemas.onboarding import OnboardingProcessResponse


def build_agent_reply(
    *,
    customer_text: str,
    response_type: str,
    record: EngagementLeadRecord | None,
    onboarding: OnboardingProcessResponse | None,
    settings: Settings | None = None,
) -> str:
    bank = (settings or get_settings()).engagement_bank_name
    name = (record.name if record else None) or "there"
    product = (record.recommended_product if record else None) or "lending offer"

    if onboarding and onboarding.next_action == "voice_callback_initiated":
        return (
            f"Dear {name}, thank you for reaching out to {bank}. "
            f"Our AI voice banking specialist is calling you now — please answer. "
            f"We can discuss your {product} in your preferred language."
        )

    if is_contact_intent(response_type=response_type, raw_text=customer_text):
        return (
            f"Hi {name}, we received your request to speak with us. "
            f"Our AI banking assistant will call you shortly on this number. "
            f"Reply INTERESTED anytime to learn more about {product}."
        )

    if response_type == "interested":
        return (
            f"Thank you {name}! We're glad you're interested in {bank}'s {product}. "
            f"Our team will share personalized details shortly. "
            f"Reply CALL ME if you'd prefer a voice conversation now."
        )

    if response_type == "declined":
        return (
            f"Understood {name}. We've noted that you're not interested at this time. "
            f"You won't receive further promotional messages unless you opt in again."
        )

    if response_type == "no_answer":
        return (
            f"Hi {name}, we tried reaching you about your {product} from {bank}. "
            f"Reply when convenient or text CALL ME for an AI voice callback."
        )

    text_lower = (customer_text or "").lower().strip()
    if any(w in text_lower for w in ("hi", "hello", "namaste", "hey")):
        return (
            f"Hello {name}! This is {bank}'s digital assistant. "
            f"Based on your profile, we have a pre-qualified {product} for you. "
            f"Reply INTERESTED, CALL ME, or ask any question."
        )

    if onboarding and onboarding.next_action == "kyc_nudge":
        return (
            f"Thanks for your message, {name}. To proceed with {product}, "
            f"please upload your KYC documents via the IDBI mobile app or visit a branch. "
            f"Reply if you need help."
        )

    return (
        f"Thanks for your message, {name}. We received: \"{customer_text[:120]}\". "
        f"Reply INTERESTED for {product}, CALL ME for a voice assistant, "
        f"or NOT INTERESTED to opt out."
    )
