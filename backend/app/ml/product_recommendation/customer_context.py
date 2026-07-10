"""Unified customer context for product recommendation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CustomerContext:
    """Normalized customer view consumed by eligibility and ranking engines."""

    profile_id: UUID
    profile_type: str
    is_existing_customer: bool
    age: int | None
    monthly_income: Decimal | None
    credit_score: int | None
    emi_ratio: Decimal | None
    persona: str | None
    occupation: str | None
    city: str | None
    relationship_score: Decimal | None
    financial_health_score: Decimal | None
    financial_capacity_score: Decimal | None
    customer_value_score: Decimal | None
    repayment_capacity: str | None
    repayment_confidence: float
    repayment_probabilities: dict[str, float]
