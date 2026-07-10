"""Schemas for engagement export and voice bridge."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EngagementLeadRecord(BaseModel):
    """One lead/customer ready for voice outreach."""

    entity_type: str
    entity_id: str
    profile_id: str | None = None
    phone: str
    name: str
    email: str | None = None
    # UI aliases (populated by adapt_engagement_lead)
    full_name: str | None = None
    phone_number: str | None = None
    lead_id: str | None = None
    profile_type: str | None = None
    recommended_product: str | None = None
    conversion_probability: float | None = None
    marketing_priority: str | None = None
    lead_priority: str | None = None
    preferred_channel: str | None = None
    repayment_capacity: str | None = None
    talking_points: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    consent: bool | None = None
    product_recommendations: list[str] = Field(
        default_factory=list,
        description="Top product names for WhatsApp carousel",
    )


class EngagementExportResponse(BaseModel):
    message: str
    file_path: str
    records_exported: int
    records: list[EngagementLeadRecord]


class VoiceCampaignRequest(BaseModel):
    campaign_name: str = "Tara Lending Outreach"
    agent_id: str = "lending_offer_agent"
    limit: int | None = Field(default=None, ge=1, le=1000)
    profile_types: list[str] = Field(default_factory=lambda: ["External"])
    min_conversion_probability: float | None = Field(default=None, ge=0, le=100)
    start_campaign: bool = False


class VoiceCampaignResponse(BaseModel):
    message: str
    campaign_id: int | None = None
    campaign_name: str
    agent_id: str
    leads_pushed: int
    upload_result: dict | None = None
    dialer_result: dict | None = None
    file_path: str | None = None


class OutreachRequest(BaseModel):
    """Run multi-channel engagement outreach."""

    channel: str | None = Field(
        default=None,
        description="Force channel: Voice, WhatsApp, SMS, Email. Omit to use preferred_channel per lead.",
    )
    campaign_name: str = "Tara Lending Outreach"
    agent_id: str = "lending_offer_agent"
    limit: int | None = Field(default=None, ge=1, le=1000)
    offset: int = Field(
        default=0,
        ge=0,
        description="Skip first N records per profile type (e.g. 50 = next batch)",
    )
    profile_types: list[str] = Field(default_factory=lambda: ["External"])
    min_conversion_probability: float | None = Field(default=None, ge=0, le=100)
    require_consent: bool = Field(default=True, description="Only leads/customers with consent")
    dry_run: bool = Field(default=True, description="Preview without sending")
    start_voice_campaign: bool = Field(
        default=False,
        description="Start Twilio dialer immediately (Voice channel only)",
    )
    auto_sequence: bool = Field(
        default=True,
        description="Create multi-touch engagement sequence for each lead after outreach",
    )


class ChannelDeliveryResultResponse(BaseModel):
    channel: str
    success: bool
    entity_id: str
    recipient: str
    provider_sid: str | None = None
    status: str
    error: str | None = None


class OutreachResponse(BaseModel):
    message: str
    total: int
    succeeded: int
    failed: int
    skipped: int
    dry_run: bool
    by_channel: dict[str, int]
    voice_campaign_id: int | None = None
    sequences_created: int = 0
    results: list[ChannelDeliveryResultResponse] = Field(default_factory=list)


class ChannelStatusResponse(BaseModel):
    channels: list[dict[str, str]]


class CustomSendRequest(BaseModel):
    """Send a personalized custom message to one phone/email."""

    channel: str = Field(description="WhatsApp, SMS, or Email")
    phone: str = Field(description="E.164 or 10-digit Indian mobile")
    name: str = "Customer"
    email: str | None = None
    message: str | None = Field(
        default=None,
        description="Optional override. If empty, uses Tara ML + explainability personalization.",
    )
    use_tara_intelligence: bool = Field(
        default=True,
        description="Use top scored lead's product + talking points in the message",
    )
    whatsapp_message_type: str | None = Field(
        default=None,
        description="welcome | main_menu | loan_carousel | preapproved_buttons | text",
    )
    dry_run: bool = False


class CustomSendResponse(BaseModel):
    message: str
    result: ChannelDeliveryResultResponse
    personalized_text: str | None = None


class VoiceCallOutcomeRequest(BaseModel):
    """Posted by bank/bank voice runtime when a Twilio call ends."""

    call_sid: str
    entity_id: str = Field(description="Tara lead/customer id (from campaign CSV customer_id)")
    entity_type: str = "External"
    recipient: str = Field(description="E.164 phone number")
    call_status: str = Field(description="Twilio CallStatus e.g. completed, no-answer")
    duration_seconds: int = 0
    agent_id: str = "lending_offer_agent"
    direction: str = "outbound"
    intent: str | None = None
    outcome: str | None = Field(
        default=None,
        description="interested | declined | callback_requested | neutral",
    )
    transcript_preview: str | None = None
    campaign_lead_id: int | None = None
    metadata: dict = Field(default_factory=dict)


class VoiceCallOutcomeResponse(BaseModel):
    message: str
    event_id: str
