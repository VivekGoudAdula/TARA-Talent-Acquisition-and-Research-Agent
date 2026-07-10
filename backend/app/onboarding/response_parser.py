"""Map channel payloads and voice intents to lead response types."""

from __future__ import annotations

_INTERESTED = {
    "interested",
    "interest",
    "apply",
    "apply_now",
    "yes",
    "haan",
    "proceed",
    "loan_interest",
    "positive",
    "convert",
    "want",
}
_DECLINED = {
    "declined",
    "decline",
    "not_interested",
    "not interested",
    "no",
    "nahi",
    "nahin",
    "stop",
    "unsubscribe",
}
_CALLBACK = {
    "callback",
    "callback_requested",
    "talk_to_us",
    "talk to us",
    "talk to me",
    "call me",
    "call back",
    "call me back",
    "voice_call",
    "voice call",
    "speak to advisor",
    "speak to agent",
    "contact me",
    "phone call",
    "rm",
}
_CONTACT_PHRASES = (
    "talk to us",
    "talk to me",
    "call me",
    "call back",
    "call me back",
    "speak to",
    "contact me",
    "phone call",
    "voice call",
    "callback",
    "ring me",
    "dial me",
    "agent se baat",
    "call cheyandi",
    "call pannunga",
)
_NO_ANSWER = {"no_answer", "no-answer", "busy", "failed", "canceled", "cancelled"}


def classify_response(
    *,
    response_type: str | None = None,
    raw_text: str | None = None,
    button_payload: str | None = None,
    intent: str | None = None,
    call_status: str | None = None,
) -> str:
    """Return: interested | declined | callback_requested | no_answer | neutral | unknown."""
    if response_type:
        normalized = response_type.strip().lower().replace(" ", "_")
        if normalized in _INTERESTED:
            return "interested"
        if normalized in _DECLINED:
            return "declined"
        if normalized in _CALLBACK:
            return "callback_requested"
        if normalized in _NO_ANSWER:
            return "no_answer"
        return normalized

    for source in (button_payload, intent, raw_text, call_status):
        if not source:
            continue
        text = source.strip().lower().replace("-", "_")
        tokens = set(text.replace(",", " ").split())
        if tokens & _INTERESTED or any(k in text for k in _INTERESTED):
            return "interested"
        if tokens & _DECLINED or any(k in text for k in _DECLINED):
            return "declined"
        if tokens & _CALLBACK or any(k in text for k in _CALLBACK):
            return "callback_requested"
        if text in _NO_ANSWER or any(k in text for k in _NO_ANSWER):
            return "no_answer"

    if call_status and call_status.lower() in ("completed", "answered"):
        return "neutral"

    return "unknown"


def is_contact_intent(
    *,
    response_type: str | None = None,
    raw_text: str | None = None,
    button_payload: str | None = None,
    intent: str | None = None,
) -> bool:
    """True when the customer wants to talk to the AI voice agent."""
    classified = classify_response(
        response_type=response_type,
        raw_text=raw_text,
        button_payload=button_payload,
        intent=intent,
    )
    if classified == "callback_requested":
        return True
    haystack = " ".join(
        s for s in (raw_text, button_payload, intent) if s
    ).lower()
    return any(phrase in haystack for phrase in _CONTACT_PHRASES)
