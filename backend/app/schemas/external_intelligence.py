"""Pydantic schemas for external CRM leads."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExternalLeadResponse(BaseModel):
    """API response for a single external lead."""

    model_config = ConfigDict(from_attributes=True)

    lead_id: UUID
    external_reference: str
    full_name: str
    phone_number: str
    email: str
    age: int | None
    gender: str | None
    occupation: str | None
    employer: str | None
    estimated_income: Decimal | None
    credit_score: int | None
    city: str | None
    state: str | None
    preferred_language: str | None
    referral_source: str | None
    campaign: str | None
    lead_status: str
    consent: bool
    lead_created_date: date | None
    created_at: datetime
    updated_at: datetime


class ExternalLeadListResponse(BaseModel):
    """Paginated list of external leads."""

    total: int
    leads: list[ExternalLeadResponse]


class ExternalImportResponse(BaseModel):
    """Result of Excel import operation."""

    message: str
    file_path: str
    leads_imported: int
    leads_skipped: int
    leads_updated: int


class ExternalEnrichResponse(BaseModel):
    """Result of batch enrichment operation."""

    message: str
    leads_processed: int
    leads_enriched: int
    leads_failed: int


class ExternalLeadSimulateRequest(BaseModel):
    """Quick demo payload for Lead Intelligence Engine."""

    source: str = "Instagram"
    campaign: str = "Home Loan July"
    name: str = "Krishna"
    salary: int = Field(default=85000, ge=0)


class ExternalLeadCreateRequest(BaseModel):
    """University / web portal lead capture."""

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    email: str = Field(min_length=3, max_length=200)
    salary: int = Field(ge=0)
    city: str = Field(min_length=1, max_length=80)
    interested_product: str = Field(min_length=1, max_length=120)
    source: str = Field(default="University Portal", max_length=80)


class ExternalLeadCreateResponse(BaseModel):
    """Result of creating a single external lead."""

    message: str
    lead_id: UUID
    external_reference: str
    pipeline_started: bool
    lead: ExternalLeadResponse


class ExternalCustomerProfileResponse(BaseModel):
    """Enriched intelligence profile for an external lead."""

    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    lead_id: UUID
    income_segment: str | None
    occupation_segment: str | None = Field(
        default=None, description="Derived occupation segment (enrichment output)"
    )
    customer_persona: str | None
    relationship_potential: Decimal | None
    financial_stability: Decimal | None
    digital_adoption: Decimal | None
    preferred_channel: str | None
    preferred_contact_time: str | None
    cross_sell_potential: Decimal | None
    lead_score: Decimal | None
    existing_bank: str | None
    existing_products: str | None
    monthly_emi: Decimal | None
    home_owner: bool | None
    preferred_language: str | None = None
    last_updated: datetime
    lead: ExternalLeadResponse | None = None
