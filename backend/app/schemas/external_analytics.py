"""Output schemas for external lead analytics APIs."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LeadBehaviourAnalyticsResult(BaseModel):
    campaign_engagement_score: Decimal = Field(description="Campaign relevance and engagement potential 0–100")
    referral_quality_score: Decimal = Field(description="Quality of acquisition referral source 0–100")
    digital_readiness_score: Decimal = Field(description="Readiness for digital channels 0–100")
    communication_readiness_score: Decimal = Field(description="Overall communication readiness 0–100")
    consent_strength: Decimal = Field(description="Marketing consent strength 0–100")
    preferred_contact_channel: str
    preferred_contact_time: str
    marketing_responsiveness_score: Decimal = Field(description="Likely marketing response rate 0–100")
    customer_persona_confidence: Decimal = Field(description="Confidence in assigned persona 0–100")


class FinancialCapacityAnalyticsResult(BaseModel):
    financial_capacity_score: Decimal = Field(description="Overall financial capacity 0–100")
    estimated_repayment_capacity: Decimal = Field(description="Estimated monthly repayment capacity in INR")
    income_segment: str
    income_stability: Decimal = Field(description="Rule-based income stability 0–100")
    emi_burden: Decimal = Field(description="EMI as percentage of monthly income")
    credit_quality: str
    affordability_level: str


class LeadQualityAnalyticsResult(BaseModel):
    lead_quality_score: Decimal = Field(description="Composite lead quality 0–100")
    conversion_readiness: Decimal = Field(description="Readiness to convert 0–100")
    qualification_status: str
    kyc_readiness: Decimal = Field(description="KYC data completeness 0–100")
    priority_level: str
    sales_readiness: Decimal = Field(description="Sales outreach readiness 0–100")


class ExternalLeadAnalyticsProfile(BaseModel):
    """Unified external lead analytics output."""

    lead_id: UUID
    lead_quality_score: Decimal
    financial_capacity_score: Decimal
    campaign_engagement_score: Decimal
    digital_readiness_score: Decimal
    communication_readiness_score: Decimal
    qualification_status: str
    priority_level: str
    preferred_channel: str
    preferred_contact_time: str
    estimated_repayment_capacity: Decimal
    conversion_readiness: Decimal
    sales_readiness: Decimal
    income_stability: Decimal
    emi_burden: Decimal
    credit_quality: str
    affordability_level: str
    referral_quality_score: Decimal
    marketing_responsiveness_score: Decimal
    customer_persona_confidence: Decimal
    behaviour: LeadBehaviourAnalyticsResult
    financial_capacity: FinancialCapacityAnalyticsResult
    lead_quality: LeadQualityAnalyticsResult


class ExternalLeadAnalyticsResponse(BaseModel):
    message: str
    analytics: ExternalLeadAnalyticsProfile


class ExternalLeadAnalyticsBuildAllResponse(BaseModel):
    message: str
    leads_processed: int
    leads_succeeded: int
    leads_failed: int
