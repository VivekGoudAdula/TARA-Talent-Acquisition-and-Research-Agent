"""Schemas for Behaviour Analytics Summary Layer."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BehaviourSummaryResponse(BaseModel):
    """Standardized behaviour analytics summary for internal or external profiles."""

    profile_id: UUID
    profile_type: str = Field(description="Internal or External")
    entity_id: UUID = Field(description="customer_id for Internal, lead_id for External")
    financial_health_score: Decimal = Field(description="Aggregated financial health 0–100")
    repayment_behaviour_score: Decimal = Field(description="Aggregated repayment behaviour 0–100")
    digital_engagement_score: Decimal = Field(description="Aggregated digital engagement 0–100")


class BehaviourSummaryBuildResponse(BaseModel):
    message: str
    summary: BehaviourSummaryResponse


class BehaviourSummaryBuildAllResponse(BaseModel):
    message: str
    profiles_processed: int
    internal_succeeded: int
    external_succeeded: int
    profiles_failed: int
