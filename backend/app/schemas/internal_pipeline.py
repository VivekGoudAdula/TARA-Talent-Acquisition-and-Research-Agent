"""Pydantic schemas for the Internal Customer Intelligence Pipeline."""

from uuid import UUID

from pydantic import BaseModel, Field


class PipelineStageLog(BaseModel):
    """Single stage completion record for one customer."""

    stage: str
    status: str = "completed"


class CustomerPipelineResult(BaseModel):
    """Outcome of running the pipeline for one customer."""

    customer_id: UUID
    success: bool
    stages_completed: list[str] = Field(default_factory=list)
    failed_stage: str | None = None
    error: str | None = None


class PipelineValidationDetail(BaseModel):
    """Row-level validation comparison."""

    customers: int
    profiles: int
    feature_store_customers: int
    feature_store_rows: int
    pipeline_completed: int
    is_valid: bool
    mismatches: list[str] = Field(default_factory=list)


class PipelineBuildSummary(BaseModel):
    """Summary returned after a build-all or build-one run."""

    customers: int
    profiles: int
    feature_store: int
    completed: int
    failed: int
    success_rate: str
    failed_customer_ids: list[str] = Field(default_factory=list)
    validation: PipelineValidationDetail | None = None
    results: list[CustomerPipelineResult] = Field(default_factory=list)


class PipelineStatusResponse(BaseModel):
    """Current pipeline coverage across the customer base."""

    total_customers: int
    profiles_built: int
    feature_store_built: int
    pipeline_completed: int
    pending_customers: int
    failed_customers: int
    success_percentage: str
    pending_customer_ids: list[str] = Field(default_factory=list)
    failed_customer_ids: list[str] = Field(default_factory=list)
    is_running: bool = False
