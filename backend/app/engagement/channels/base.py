"""Shared types for engagement channel delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChannelDeliveryResult:
    channel: str
    success: bool
    entity_id: str
    recipient: str
    provider_sid: str | None = None
    status: str = "pending"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
