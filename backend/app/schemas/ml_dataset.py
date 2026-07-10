"""Pydantic schemas for ML Dataset Builder API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MLDatasetRecordResponse(BaseModel):
    """Single training dataset record."""

    model_config = ConfigDict(from_attributes=True)

    record_id: UUID
    profile_type: str
    profile_id: UUID
    age: int | None = None
    income: Decimal | None = None
    credit_score: int | None = None
    financial_health_score: Decimal | None = None
    repayment_behaviour_score: Decimal | None = None
    digital_engagement_score: Decimal | None = None
    financial_capacity_score: Decimal | None = None
    lead_score: Decimal | None = None
    lead_quality_score: Decimal | None = None
    lead_authenticity_score: Decimal | None = None
    income_confidence_score: Decimal | None = None
    relationship_score: Decimal | None = None
    savings_ratio: Decimal | None = None
    emi_burden: Decimal | None = None
    cash_flow_score: Decimal | None = None
    digital_adoption_score: Decimal | None = None
    customer_value_score: Decimal | None = None
    occupation: str | None = None
    employment_type: str | None = None
    city: str | None = None
    target_repayment_capacity: str
    created_at: datetime


class MLDatasetBuildResponse(BaseModel):
    message: str
    records_persisted: int
    internal_records: int
    external_records: int
    duplicates_removed: int
    csv_path: str
    parquet_path: str
    target_distribution: dict[str, int]


class MLDatasetPreviewResponse(BaseModel):
    total_records: int
    preview_limit: int = Field(description="Number of records returned in preview")
    records: list[MLDatasetRecordResponse]


class MLDatasetStatsResponse(BaseModel):
    total_records: int
    internal_records: int
    external_records: int
    feature_count: int
    missing_values: dict[str, int]
    target_distribution: dict[str, int]
    export_paths: dict[str, str]
