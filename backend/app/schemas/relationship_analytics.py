"""Relationship analytics output schemas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AccountAnalyticsResult(BaseModel):
    number_of_accounts: int
    savings_accounts: int
    salary_accounts: int
    current_accounts: int
    dormant_accounts: int
    closed_accounts: int
    average_account_age_years: Decimal
    oldest_account_years: Decimal
    newest_account_years: Decimal


class ProductPortfolioResult(BaseModel):
    number_of_active_products: int
    savings_account_count: int
    current_account_count: int
    credit_card_count: int
    loan_count: int
    insurance_count: int
    mutual_fund_count: int
    fixed_deposit_count: int
    recurring_deposit_count: int
    demat_account_count: int


class RelationshipProfile(BaseModel):
    """Unified banking relationship analytics output."""

    customer_id: UUID
    number_of_accounts: int
    number_of_products: int
    relationship_age: Decimal = Field(description="Years with the bank")
    relationship_strength_score: Decimal = Field(description="Overall relationship health 0–100")
    loyalty_score: Decimal = Field(description="Customer loyalty 0–100")
    product_penetration_score: Decimal = Field(description="Share of catalog owned 0–100")
    product_diversity_score: Decimal = Field(description="Breadth of product types 0–100")
    bank_dependency_score: Decimal = Field(description="Reliance on bank for banking 0–100")
    relationship_tier: str
    estimated_customer_value: Decimal
    missing_products: list[str] = Field(default_factory=list)
    engagement_score: Decimal = Field(description="Overall engagement 0–100")
    relationship_stability: Decimal = Field(description="Stability of relationship 0–100")
    primary_banking_score: Decimal = Field(description="Primary bank indicator 0–100")
    account_analytics: AccountAnalyticsResult | None = None
    product_portfolio: ProductPortfolioResult | None = None


class RelationshipAnalyticsResponse(BaseModel):
    message: str
    relationship_profile: RelationshipProfile


class RelationshipBuildAllResponse(BaseModel):
    message: str
    customers_processed: int
    customers_succeeded: int
    customers_failed: int
