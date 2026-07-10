"""Lending product catalogue and eligibility rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

RelationshipPreference = Literal["Any", "Existing", "New"]

PRODUCT_PERSONAL_LOAN = "Personal Loan"
PRODUCT_HOME_LOAN = "Home Loan"
PRODUCT_AUTO_LOAN = "Auto Loan"
PRODUCT_MORTGAGE_LOAN = "Mortgage Loan"
PRODUCT_EDUCATION_LOAN = "Education Loan"

LENDING_PRODUCTS: tuple[str, ...] = (
    PRODUCT_PERSONAL_LOAN,
    PRODUCT_HOME_LOAN,
    PRODUCT_AUTO_LOAN,
    PRODUCT_MORTGAGE_LOAN,
    PRODUCT_EDUCATION_LOAN,
)


@dataclass(frozen=True)
class LendingProduct:
    """A lending product with deterministic eligibility criteria."""

    name: str
    min_monthly_income: Decimal
    min_credit_score: int
    max_emi_ratio: Decimal
    min_age: int
    max_age: int
    target_personas: tuple[str, ...]
    relationship_preference: RelationshipPreference
    description: str


PRODUCT_CATALOG: tuple[LendingProduct, ...] = (
    LendingProduct(
        name=PRODUCT_PERSONAL_LOAN,
        min_monthly_income=Decimal("25000"),
        min_credit_score=650,
        max_emi_ratio=Decimal("50"),
        min_age=21,
        max_age=60,
        target_personas=(
            "Young Professional",
            "Salary Elite",
            "Mass Market",
            "Business Owner",
            "Premium",
        ),
        relationship_preference="Any",
        description="Unsecured personal financing for short-to-medium term needs",
    ),
    LendingProduct(
        name=PRODUCT_HOME_LOAN,
        min_monthly_income=Decimal("50000"),
        min_credit_score=700,
        max_emi_ratio=Decimal("40"),
        min_age=25,
        max_age=60,
        target_personas=("Family", "Salary Elite", "High Net Worth", "Premium"),
        relationship_preference="Existing",
        description="Long-term housing finance for property purchase or construction",
    ),
    LendingProduct(
        name=PRODUCT_AUTO_LOAN,
        min_monthly_income=Decimal("30000"),
        min_credit_score=680,
        max_emi_ratio=Decimal("45"),
        min_age=21,
        max_age=65,
        target_personas=("Young Professional", "Family", "Mass Market", "Salary Elite"),
        relationship_preference="Any",
        description="Vehicle financing for new or pre-owned automobiles",
    ),
    LendingProduct(
        name=PRODUCT_MORTGAGE_LOAN,
        min_monthly_income=Decimal("75000"),
        min_credit_score=720,
        max_emi_ratio=Decimal("35"),
        min_age=28,
        max_age=58,
        target_personas=("High Net Worth", "Premium", "Family", "Business Owner"),
        relationship_preference="Existing",
        description="Premium mortgage financing for high-value residential property",
    ),
    LendingProduct(
        name=PRODUCT_EDUCATION_LOAN,
        min_monthly_income=Decimal("20000"),
        min_credit_score=600,
        max_emi_ratio=Decimal("50"),
        min_age=18,
        max_age=45,
        target_personas=("Student", "Young Professional", "Family"),
        relationship_preference="Any",
        description="Education financing for domestic and international studies",
    ),
)


def get_product_catalog() -> list[LendingProduct]:
    return list(PRODUCT_CATALOG)


def get_product_by_name(name: str) -> LendingProduct | None:
    for product in PRODUCT_CATALOG:
        if product.name == name:
            return product
    return None
