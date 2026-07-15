"""Schemas for AI Callback session orchestration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceAgentContext(BaseModel):
    """Full context injected into the voice agent for callback calls."""

    name: str
    lang: str = "English"
    campaign: str | None = None
    intent: str = "callback"
    product: str | None = None
    top3_reasons: list[str] = Field(default_factory=list)
    confidence: float | None = Field(
        default=None,
        description="Model confidence 0–100 (conversion probability)",
    )
    eligibility: str | None = None
    customer_id: str
    entity_type: str = "External"
    phone: str
    repayment_capacity: str | None = None
    talking_points: str | None = None
    agent_instructions: str = Field(
        default="",
        description="Behavior rules for the voice agent",
    )


class VoiceCallbackStartRequest(BaseModel):
    phone: str
    entity_id: str | None = None
    entity_type: str = "External"
    name: str | None = Field(
        default=None,
        description="Display name override for the voice agent (e.g. Voice Console dialer)",
    )
    campaign: str | None = None
    source_channel: str | None = Field(
        default=None,
        description="Email | WhatsApp | SMS | Web — how the customer triggered the callback",
    )


class VoiceCallbackStartResponse(BaseModel):
    session_id: str
    triggered: bool
    context: VoiceAgentContext
    timing_ms: dict[str, float] = Field(default_factory=dict)
    call: dict | None = None
    call_sid: str | None = None
    reason: str | None = None
    message: str | None = None
