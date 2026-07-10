"""Output schemas for external lead intelligence validation APIs."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LeadAuthenticityResult(BaseModel):
    lead_authenticity_score: Decimal = Field(description="Trustworthiness and completeness 0–100")
    reason_codes: list[str] = Field(default_factory=list)


class IncomeConfidenceResult(BaseModel):
    income_confidence_score: Decimal = Field(description="Confidence in reported income 0–100")
    income_confidence_level: str = Field(description="High, Medium, or Low")
    reason_codes: list[str] = Field(default_factory=list)


class FraudScreeningResult(BaseModel):
    fraud_score: Decimal = Field(description="Fraud risk indicator 0–100 (higher = more risk)")
    fraud_risk: str = Field(description="Low, Medium, or High")
    fraud_reason_codes: list[str] = Field(default_factory=list)


class KycReadinessResult(BaseModel):
    kyc_readiness: str = Field(description="Ready, Partially Ready, or Not Ready")
    kyc_missing_items: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ExternalLeadIntelligenceProfile(BaseModel):
    """Complete external lead intelligence validation output."""

    lead_id: UUID
    lead_authenticity_score: Decimal
    income_confidence_score: Decimal
    income_confidence_level: str
    fraud_score: Decimal
    fraud_risk: str
    kyc_readiness: str
    kyc_missing_items: list[str]
    reason_codes: list[str]
    fraud_reason_codes: list[str]
    last_validation_timestamp: datetime
    authenticity: LeadAuthenticityResult
    income_confidence: IncomeConfidenceResult
    fraud_screening: FraudScreeningResult
    kyc: KycReadinessResult


class ExternalLeadIntelligenceResponse(BaseModel):
    message: str
    intelligence: ExternalLeadIntelligenceProfile


class ExternalLeadIntelligenceBuildAllResponse(BaseModel):
    message: str
    leads_processed: int
    leads_succeeded: int
    leads_failed: int
