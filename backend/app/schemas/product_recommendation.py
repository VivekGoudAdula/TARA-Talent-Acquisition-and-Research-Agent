"""Pydantic schemas for Product Recommendation API."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ProductCatalogItem(BaseModel):
    name: str
    description: str
    min_monthly_income: Decimal
    min_credit_score: int
    max_emi_ratio: Decimal
    min_age: int
    max_age: int
    target_personas: list[str]
    relationship_preference: str


class ProductCatalogResponse(BaseModel):
    products: list[ProductCatalogItem]
    total_products: int


class ProductRecommendRequest(BaseModel):
    profile_id: UUID = Field(description="Internal or External customer profile ID")
    top_n: int = Field(default=5, ge=1, le=5, description="Number of products to return (max 5)")


class ProductRecommendationItem(BaseModel):
    product_name: str
    confidence_score: float = Field(description="Overall recommendation confidence 0–99%")
    eligible: bool
    probability: float = Field(description="Fit probability 0–99%")
    eligibility_reasons: list[str] = Field(default_factory=list)


class ProductRecommendResponse(BaseModel):
    profile_id: UUID
    profile_type: str
    repayment_capacity: str
    repayment_confidence: float
    top_recommendation: str | None
    recommendations: list[ProductRecommendationItem]
