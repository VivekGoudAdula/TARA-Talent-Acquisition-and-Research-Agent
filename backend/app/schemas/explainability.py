"""Pydantic schemas for Explainable AI API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ExplainabilityGenerateRequest(BaseModel):
    profile_id: UUID | None = Field(
        default=None, description="Internal or External profile UUID"
    )
    customer_id: UUID | None = Field(
        default=None,
        description="Internal customer_id or external lead_id (alternative to profile_id)",
    )

    @model_validator(mode="after")
    def require_identifier(self) -> "ExplainabilityGenerateRequest":
        if self.profile_id is None and self.customer_id is None:
            raise ValueError("Either profile_id or customer_id must be provided")
        return self


class ExplanationResponse(BaseModel):
    summary: str
    repayment_explanation: str
    product_explanation: str
    conversion_explanation: str
    confidence_summary: str
    reason_codes: list[str]


class ExplainabilityReportResponse(BaseModel):
    report_id: UUID
    customer_id: UUID
    profile_type: str
    repayment_prediction: str | None = None
    recommended_product: str | None = None
    conversion_probability: float | None = None
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime
    explanation: ExplanationResponse
    decision_summary: dict[str, Any] | None = Field(
        default=None, description="Full decision summary (included on generate only)"
    )
