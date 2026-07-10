"""Behaviour analytics output schemas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ShoppingBehaviourResult(BaseModel):
    shopping_score: Decimal
    monthly_shopping_spend: Decimal
    shopping_frequency: Decimal
    average_shopping_amount: Decimal
    luxury_shopping_ratio: Decimal
    budget_shopping_ratio: Decimal
    top_shopping_merchant: str | None
    preferred_shopping_day: str | None


class FoodBehaviourResult(BaseModel):
    food_score: Decimal
    restaurant_spend: Decimal
    food_delivery_spend: Decimal
    dining_frequency: Decimal
    weekend_food_spend: Decimal
    favourite_food_merchant: str | None


class TravelBehaviourResult(BaseModel):
    travel_score: Decimal
    travel_frequency: Decimal
    travel_spend: Decimal
    transport_preference: str | None
    top_travel_merchant: str | None


class HealthcareBehaviourResult(BaseModel):
    healthcare_score: Decimal
    medical_spend: Decimal
    pharmacy_spend: Decimal
    hospital_spend: Decimal


class EntertainmentBehaviourResult(BaseModel):
    entertainment_score: Decimal
    ott_spend: Decimal
    movie_spend: Decimal
    music_subscription_spend: Decimal
    gaming_spend: Decimal


class InvestmentBehaviourResult(BaseModel):
    investment_score: Decimal
    investment_spend: Decimal
    investment_frequency: Decimal
    sip_frequency: Decimal
    mutual_fund_transactions: int
    stock_transactions: int
    investment_consistency: Decimal


class FuelBehaviourResult(BaseModel):
    fuel_score: Decimal
    fuel_spend: Decimal
    fuel_frequency: Decimal


class EducationBehaviourResult(BaseModel):
    education_score: Decimal
    learning_spend: Decimal
    course_frequency: Decimal


class BehaviourProfile(BaseModel):
    """Unified behaviour profile for a customer."""

    customer_id: UUID
    shopping_score: Decimal
    travel_score: Decimal
    food_score: Decimal
    healthcare_score: Decimal
    investment_score: Decimal
    fuel_score: Decimal
    education_score: Decimal
    entertainment_score: Decimal
    top_interest: str | None
    secondary_interest: str | None
    third_interest: str | None
    lifestyle_tags: list[str] = Field(default_factory=list)
    shopping: ShoppingBehaviourResult | None = None
    food: FoodBehaviourResult | None = None
    travel: TravelBehaviourResult | None = None
    healthcare: HealthcareBehaviourResult | None = None
    entertainment: EntertainmentBehaviourResult | None = None
    investment: InvestmentBehaviourResult | None = None
    fuel: FuelBehaviourResult | None = None
    education: EducationBehaviourResult | None = None


class BehaviourAnalyticsResponse(BaseModel):
    message: str
    behaviour_profile: BehaviourProfile


class BehaviourBuildAllResponse(BaseModel):
    message: str
    customers_processed: int
    customers_succeeded: int
    customers_failed: int
