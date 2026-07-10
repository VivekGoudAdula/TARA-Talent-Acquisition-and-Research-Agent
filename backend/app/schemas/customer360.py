"""Pydantic schemas for Customer360 profiles and aggregates."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.banking import (
    AccountSchema,
    ConsentSchema,
    CustomerProductSchema,
    CustomerSchema,
    TransactionSchema,
)


class CustomerAggregate(BaseModel):
    """
    Unified in-memory representation of all banking data for one customer.

    Produced by CustomerAggregationService; consumed by Customer360Service.
    No scores or analytics are computed at this stage.
    """

    customer: CustomerSchema
    accounts: list[AccountSchema] = Field(default_factory=list)
    transactions: list[TransactionSchema] = Field(default_factory=list)
    products: list[CustomerProductSchema] = Field(default_factory=list)
    consent: ConsentSchema | None = None


class Customer360ProfileResponse(BaseModel):
    """API response schema for a Customer360 profile."""

    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    customer_id: UUID
    age: int | None = None
    gender: str | None = None
    occupation: str | None = None
    annual_income: Decimal | None = None
    city: str | None = None
    state: str | None = None
    preferred_language: str | None = None
    customer_since: date | None = None
    average_balance: Decimal | None = None
    monthly_income: Decimal | None = None
    monthly_expense: Decimal | None = None
    monthly_savings: Decimal | None = None
    shopping_score: Decimal | None = None
    travel_score: Decimal | None = None
    food_score: Decimal | None = None
    investment_score: Decimal | None = None
    digital_banking_score: Decimal | None = None
    customer_segment: str | None = None
    preferred_channel: str | None = None
    preferred_contact_time: str | None = None
    risk_score: Decimal | None = None
    financial_health_score: Decimal | None = None
    repayment_behaviour_score: Decimal | None = None
    digital_engagement_score: Decimal | None = None
    digital_adoption_score: Decimal | None = None
    relationship_strength_score: Decimal | None = None
    last_updated: datetime | None = None


class Customer360BuildResponse(BaseModel):
    """Response returned after building or refreshing a profile."""

    message: str
    profile: Customer360ProfileResponse
