"""Schemas for pipeline orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineStepResponse(BaseModel):
    step: str
    status: str
    detail: str | None = None
    duration_ms: int = 0


class PipelineRunResponse(BaseModel):
    run_id: str
    pipeline_type: str
    success: bool
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)


class PipelineStatusResponse(BaseModel):
    run_id: str
    pipeline_type: str
    success: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
