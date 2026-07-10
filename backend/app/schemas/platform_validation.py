"""Pydantic schemas for Platform Validation API and reports."""

from typing import Any

from pydantic import BaseModel, Field


class ValidationCheckResponse(BaseModel):
    category: str
    name: str
    status: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class CategorySummaryResponse(BaseModel):
    category: str
    status: str
    passed: int
    failed: int
    warned: int
    skipped: int
    checks: list[ValidationCheckResponse] = Field(default_factory=list)


class SystemHealthResponse(BaseModel):
    database: str
    internal: str
    external: str
    customer360: str
    feature_store: str
    behaviour_analytics: str
    ml: str
    repayment_model: str
    product_recommendation: str
    lead_conversion: str
    api: str
    data_integrity: str
    end_to_end_workflow: str
    overall_health: str


class ValidationReportResponse(BaseModel):
    generated_at: str
    overall_health: str
    system_health: SystemHealthResponse
    categories: list[CategorySummaryResponse]
    report_paths: dict[str, str] = Field(default_factory=dict)
