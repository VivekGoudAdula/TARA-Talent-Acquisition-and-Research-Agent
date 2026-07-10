"""Pydantic schemas for Repayment Capacity Prediction API."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RepaymentTrainResponse(BaseModel):
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


class RepaymentPredictRequest(BaseModel):
    profile_type: str | None = Field(
        default=None, description="Internal or External — used with profile_id lookup"
    )
    profile_id: UUID | None = Field(
        default=None, description="Resolve features from training dataset record"
    )
    features: dict[str, Any] | None = Field(
        default=None, description="Engineered feature dictionary for direct prediction"
    )

    @model_validator(mode="after")
    def require_features_or_profile(self) -> "RepaymentPredictRequest":
        if self.features is None and self.profile_id is None:
            raise ValueError("Either features or profile_id must be provided")
        return self


class RepaymentPredictResponse(BaseModel):
    repayment_capacity: str
    confidence: float
    probabilities: dict[str, float]
    model_used: str


class RepaymentModelInfoResponse(BaseModel):
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
