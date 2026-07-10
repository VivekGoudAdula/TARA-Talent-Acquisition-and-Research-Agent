"""Pydantic schemas for Lead Conversion Prediction API."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ConversionTrainResponse(BaseModel):
    message: str
    best_model: str
    records_used: int
    train_size: int
    test_size: int
    cv_scores: dict[str, float]
    test_metrics: dict[str, Any]
    model_path: str
    metrics_path: str
    feature_importance_path: str


class ConversionPredictRequest(BaseModel):
    lead_id: UUID | None = Field(default=None, description="External lead ID to resolve features")
    features: dict[str, Any] | None = Field(
        default=None, description="Engineered feature dictionary for direct prediction"
    )

    @model_validator(mode="after")
    def require_lead_or_features(self) -> "ConversionPredictRequest":
        if self.lead_id is None and self.features is None:
            raise ValueError("Either lead_id or features must be provided")
        return self


class ConversionPredictResponse(BaseModel):
    lead_id: UUID | None = None
    conversion_probability: float = Field(description="Predicted conversion probability 0–100%")
    lead_priority: str = Field(description="High / Medium / Low sales priority")
    marketing_priority: str = Field(description="High / Medium / Low marketing outreach priority")
    model_used: str


class ConversionModelInfoResponse(BaseModel):
    model_exists: bool
    best_model: str | None = None
    trained_at: str | None = None
    feature_columns: list[str] = Field(default_factory=list)
    records_used: int | None = None
    model_path: str | None = None
    metrics_path: str | None = None
    feature_importance_path: str | None = None
    metrics: dict[str, Any] | None = None
    feature_importance: dict[str, float] | None = None
