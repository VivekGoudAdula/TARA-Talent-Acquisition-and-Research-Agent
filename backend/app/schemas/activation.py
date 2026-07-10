"""Schemas for simulated UPI / YONO activation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ActivationStartRequest(BaseModel):
    entity_id: str
    entity_type: str = "External"
    phone: str
    product: str | None = None


class ActivationStartResponse(BaseModel):
    message: str
    activation_id: str
    deep_link: str | None = None
    steps_total: int = 0


class ActivationStepRequest(BaseModel):
    activation_id: str
    step: str = Field(description="app_download | mobile_verify | upi_id_create | yono_login | product_activate")


class ActivationStatusResponse(BaseModel):
    activation_id: str
    entity_id: str
    entity_type: str
    phone: str
    product: str | None = None
    status: str
    channel: str
    deep_link: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None
    completed_at: datetime | None = None
