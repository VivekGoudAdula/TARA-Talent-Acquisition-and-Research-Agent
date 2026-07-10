"""Layer 5 — Conversion & Onboarding schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LeadResponseCaptureRequest(BaseModel):
    """Capture interest / disinterest from any channel."""

    entity_id: str
    entity_type: str = "External"
    channel: str = Field(description="Voice, WhatsApp, SMS, Email")
    response_type: str | None = Field(
        default=None,
        description="interested | declined | callback_requested | neutral | no_answer",
    )
    raw_text: str | None = None
    button_payload: str | None = None
    phone: str | None = None
    name: str | None = None
    call_sid: str | None = None
    intent: str | None = None
    dry_run: bool = False


class OnboardingProcessResponse(BaseModel):
    message: str
    response_id: str
    journey_id: str
    response_type: str
    kyc_readiness: str
    journey_status: str
    next_action: str
    handoff_id: str | None = None
    nudge_sent: bool = False
    nudge_channel: str | None = None
    activation_id: str | None = None


class OnboardingJourneyResponse(BaseModel):
    journey_id: str
    entity_id: str
    entity_type: str
    status: str
    kyc_readiness: str
    kyc_missing_items: list[str] = Field(default_factory=list)
    last_response_type: str | None = None
    last_channel: str | None = None
    handoff_id: str | None = None
    nudge_count: int = 0
    product: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RmHandoffResponse(BaseModel):
    handoff_id: str
    entity_id: str
    entity_type: str
    customer_name: str
    phone: str
    product: str | None = None
    priority: str
    status: str
    reason: str
    source_channel: str
    talking_points: str | None = None
    created_at: datetime | None = None


class OnboardingStatusResponse(BaseModel):
    entity_id: str
    journey: OnboardingJourneyResponse | None = None
    responses: list[dict[str, Any]] = Field(default_factory=list)
    handoffs: list[RmHandoffResponse] = Field(default_factory=list)
