"""Derive conversion training labels from real outreach outcomes."""

from __future__ import annotations

from typing import Any

# Response → conversion probability (0–100)
RESPONSE_TYPE_LABELS: dict[str, float] = {
    "interested": 100.0,
    "apply": 95.0,
    "callback_requested": 85.0,
    "neutral": 50.0,
    "no_answer": 20.0,
    "declined": 0.0,
}

JOURNEY_STATUS_LABELS: dict[str, float] = {
    "handoff_pending": 90.0,
    "kyc_nudge_sent": 70.0,
    "engaged": 55.0,
    "awaiting_contact": 25.0,
    "closed_declined": 0.0,
    "open": 40.0,
}

HANDOFF_STATUS_LABELS: dict[str, float] = {
    "converted": 100.0,
    "completed": 95.0,
    "in_progress": 80.0,
    "pending": 75.0,
    "lost": 0.0,
    "declined": 0.0,
}


def label_from_response_type(response_type: str | None) -> float | None:
    if not response_type:
        return None
    return RESPONSE_TYPE_LABELS.get(response_type.strip().lower())


def label_from_journey_status(status: str | None) -> float | None:
    if not status:
        return None
    return JOURNEY_STATUS_LABELS.get(status.strip().lower())


def label_from_handoff_status(status: str | None) -> float | None:
    if not status:
        return None
    return HANDOFF_STATUS_LABELS.get(status.strip().lower())


def derive_conversion_label(
    *,
    response_type: str | None = None,
    journey_status: str | None = None,
    handoff_status: str | None = None,
) -> tuple[float | None, str]:
    """
    Combine outcome signals into a single conversion label.

    Priority: handoff resolution > response type > journey status.
    """
    handoff_label = label_from_handoff_status(handoff_status)
    if handoff_label is not None and handoff_status not in (None, "pending"):
        return handoff_label, "handoff_outcome"

    response_label = label_from_response_type(response_type)
    if response_label is not None:
        return response_label, "lead_response"

    journey_label = label_from_journey_status(journey_status)
    if journey_label is not None:
        return journey_label, "journey_status"

    return None, "unknown"


def build_label_record(
    *,
    entity_id: str,
    entity_type: str,
    lead_id: str | None,
    response_type: str | None,
    journey_status: str | None,
    handoff_status: str | None,
    channel: str | None,
) -> dict[str, Any] | None:
    label, source = derive_conversion_label(
        response_type=response_type,
        journey_status=journey_status,
        handoff_status=handoff_status,
    )
    if label is None:
        return None

    return {
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "lead_id": lead_id,
        "conversion_label": round(label, 2),
        "label_source": source,
        "response_type": response_type,
        "journey_status": journey_status,
        "handoff_status": handoff_status,
        "channel": channel,
    }
