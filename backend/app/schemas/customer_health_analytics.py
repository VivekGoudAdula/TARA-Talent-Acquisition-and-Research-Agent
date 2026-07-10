"""Customer health & risk analytics output schemas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerHealthProfile(BaseModel):
    """CRM-oriented customer health and business risk analytics."""

    customer_id: UUID
    customer_health_score: Decimal = Field(description="Overall customer health 0–100 (higher is healthier)")
    financial_stress_score: Decimal = Field(description="Financial stress 0–100 (higher = more stress)")
    churn_risk_score: Decimal = Field(description="Churn probability indicator 0–100")
    dormancy_risk: str = Field(description="Low | Medium | High")
    relationship_stability: Decimal
    retention_score: Decimal
    cross_sell_readiness: Decimal
    risk_band: str = Field(description="Healthy | Monitor | At Risk | Critical")
    reason_codes: list[str] = Field(default_factory=list)


class CustomerHealthAnalyticsResponse(BaseModel):
    message: str
    health_profile: CustomerHealthProfile


class CustomerHealthBuildAllResponse(BaseModel):
    message: str
    customers_processed: int
    customers_succeeded: int
    customers_failed: int
