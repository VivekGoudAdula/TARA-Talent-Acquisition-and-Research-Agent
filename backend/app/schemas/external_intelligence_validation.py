"""Input schema for external lead intelligence engines."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ExternalLeadIntelligenceInput(BaseModel):
    """
    Combined lead + profile context for intelligence validation engines.

    Sourced from external_leads, external_customer_profile, and duplicate checks.
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
    referral_source: str
    campaign: str
    consent: bool
    lead_created_date: date | None = None
    income_segment: str | None = None
    monthly_emi: Decimal = Field(default=Decimal("0"))

    # Populated by service layer duplicate screening
    duplicate_phone: bool = False
    duplicate_email: bool = False
    duplicate_lead_reference: bool = False
