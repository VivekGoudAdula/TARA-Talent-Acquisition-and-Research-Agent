"""Channel conversation message schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChannelMessageResponse(BaseModel):
    message_id: str
    thread_id: str
    entity_id: str
    entity_type: str
    channel: str
    direction: str = Field(description="inbound | outbound")
    role: str = Field(description="customer | agent | system")
    body: str
    response_type: str | None = None
    provider_sid: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | str | None = None


class ConversationThreadResponse(BaseModel):
    entity_id: str
    entity_type: str
    channel: str | None = None
    messages: list[ChannelMessageResponse]
    total: int


class InboundMessageRequest(BaseModel):
    channel: str
    body: str
    phone: str | None = None
    email: str | None = None
    entity_id: str | None = None
    entity_type: str = "External"
    button_payload: str | None = None
    provider_sid: str | None = None
