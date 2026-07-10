"""Schemas for Tara Operations Desk."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RmDashboardResponse(BaseModel):
    total_handoffs: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    overdue_sla: int = 0
    avg_wait_hours: float | None = None


class RmHandoffQueueItem(BaseModel):
    handoff_id: str
    entity_id: str
    entity_type: str = "External"
    customer_name: str
    phone: str
    product: str | None = None
    priority: str = "normal"
    status: str = "pending"
    reason: str | None = None
    source_channel: str | None = None
    talking_points: str | None = None
    assigned_rm: str | None = None
    assigned_rm_name: str | None = None
    assigned_rm_id: str | None = None
    assigned_at: datetime | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    sla_deadline: datetime | None = None
    sla_breached: bool = False
    rm_notes: str | None = None
    status_notes: str | None = None


class RmAssignRequest(BaseModel):
    rm_name: str
    rm_id: str | None = None


class RmStatusUpdateRequest(BaseModel):
    status: str = Field(description="in_progress | completed | converted | lost | declined")
    notes: str | None = None


class KycDocumentUploadRequest(BaseModel):
    entity_id: str
    document_type: str = Field(description="aadhaar | pan | income_proof | address_proof | photo")
    file_name: str
    file_size_kb: int | None = None
    checksum: str | None = Field(default=None, description="Simulated document hash")


class KycDocumentResponse(BaseModel):
    document_id: str
    entity_id: str
    document_type: str
    file_name: str
    status: str
    uploaded_at: datetime | None = None
