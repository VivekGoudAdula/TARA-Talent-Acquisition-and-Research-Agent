"""Input schema for external lead analytics engines."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ExternalLeadAnalyticsInput(BaseModel):
    """
    Combined lead + profile data used by external analytics engines.

    Sourced only from external_leads and external_customer_profile.
    No banking transaction data is included.
    """

    lead_id: UUID
    external_reference: str
    full_name: str
    phone_number: str
    email: str
    age: int
    gender: str
    occupation: str
    employer: str
    estimated_income: Decimal
    credit_score: int
    city: str
    state: str
    preferred_language: str
    referral_source: str
    campaign: str
    consent: bool
    lead_status: str
    lead_created_date: date | None = None

    # From external_customer_profile (enrichment prerequisite)
    income_segment: str | None = None
    customer_persona: str | None = None
    relationship_potential: Decimal = Field(default=Decimal("0"))
    financial_stability: Decimal = Field(default=Decimal("0"))
    digital_adoption: Decimal = Field(default=Decimal("0"))
    preferred_channel: str | None = None
    preferred_contact_time: str | None = None
    cross_sell_potential: Decimal = Field(default=Decimal("0"))
    lead_score: Decimal = Field(default=Decimal("0"))
    existing_bank: str | None = None
    existing_products: str | None = None
    monthly_emi: Decimal = Field(default=Decimal("0"))
    home_owner: bool = False
