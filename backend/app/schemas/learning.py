"""Schemas for Layer 6 — Learning & Continuous Performance Improvement."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OutcomeLabelRecord(BaseModel):
    entity_id: str
    entity_type: str
    lead_id: str | None = None
    conversion_label: float = Field(ge=0, le=100)
    label_source: str
    response_type: str | None = None
    journey_status: str | None = None
    channel: str | None = None
    handoff_status: str | None = None
    updated_at: datetime | None = None


class ChannelPerformance(BaseModel):
    channel: str
    outreach_count: int = 0
    response_count: int = 0
    interested_count: int = 0
    declined_count: int = 0
    conversion_rate: float | None = None
    response_rate: float | None = None


class PredictionAccuracy(BaseModel):
    labeled_leads: int
    mean_absolute_error: float | None = None
    within_15_points: float | None = Field(
        None, description="Share of predictions within ±15 points of actual outcome label"
    )
    over_predicted: int = 0
    under_predicted: int = 0


class FunnelMetrics(BaseModel):
    total_responses: int = 0
    interested: int = 0
    declined: int = 0
    callback_requested: int = 0
    no_answer: int = 0
    handoffs_created: int = 0
    kyc_nudges_sent: int = 0
    interest_rate: float | None = None
    handoff_rate: float | None = None


class PerformanceSummaryResponse(BaseModel):
    message: str
    snapshot_id: str | None = None
    captured_at: datetime
    funnel: FunnelMetrics
    channels: list[ChannelPerformance]
    prediction_accuracy: PredictionAccuracy
    outcome_labels_count: int
    synthetic_labels_count: int
    retrain_recommended: bool
    retrain_reason: str | None = None


class BuildOutcomeLabelsRequest(BaseModel):
    limit: int = Field(default=5000, ge=1, le=20000)
    persist: bool = True


class BuildOutcomeLabelsResponse(BaseModel):
    message: str
    labels_built: int
    labels_persisted: int
    label_distribution: dict[str, int]


class RetrainRequest(BaseModel):
    label_source: str = Field(
        default="outcomes",
        description="outcomes | synthetic | blended — blended uses outcomes where available",
    )
    min_outcome_labels: int = Field(default=5, ge=1)
    refresh_scores: bool = Field(
        default=True,
        description="Re-run scoring persistence after retrain",
    )


class RetrainResponse(BaseModel):
    message: str
    run_id: str | None = None
    label_source: str
    records_used: int
    outcome_labels_used: int
    best_model: str | None = None
    test_metrics: dict[str, Any] | None = None
    prediction_accuracy: PredictionAccuracy | None = None
    scores_refreshed: bool = False


class ModelRunSummary(BaseModel):
    run_id: str
    model_name: str
    best_model: str
    records_used: int
    label_source: str | None = None
    outcome_labels_used: int | None = None
    test_metrics: dict[str, Any] | None = None
    created_at: datetime | None = None


class PerformanceSnapshotResponse(BaseModel):
    snapshot_id: str
    captured_at: datetime
    funnel: FunnelMetrics
    channels: list[ChannelPerformance]
    prediction_accuracy: PredictionAccuracy
    outcome_labels_count: int
    notes: str | None = None


class IngestOutcomeRequest(BaseModel):
    entity_id: str
    entity_type: str = "External"
    response_type: str | None = None
    channel: str | None = None
    journey_status: str | None = None
