"""Business-rule eligibility engine for lending products."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.ml.product_recommendation.catalog import LendingProduct, PRODUCT_CATALOG
from app.ml.product_recommendation.customer_context import CustomerContext


@dataclass(frozen=True)
class EligibilityResult:
    """Eligibility outcome for a single product."""

    product_name: str
    eligible: bool
    reasons: list[str]
    rule_score: float


class EligibilityEngine:
    """Applies deterministic business rules before ML ranking."""

    def evaluate(self, customer: CustomerContext, product: LendingProduct) -> EligibilityResult:
        reasons: list[str] = []
        checks_passed = 0
        total_checks = 5

        if customer.monthly_income is None:
            reasons.append("Monthly income unavailable")
        elif customer.monthly_income < product.min_monthly_income:
            reasons.append(
                f"Income below minimum (₹{product.min_monthly_income:,.0f}/month required)"
            )
        else:
            checks_passed += 1

        if customer.credit_score is None:
            reasons.append("Credit score unavailable")
        elif customer.credit_score < product.min_credit_score:
            reasons.append(f"Credit score below minimum ({product.min_credit_score} required)")
        else:
            checks_passed += 1

        if customer.emi_ratio is None:
            checks_passed += 1
        elif customer.emi_ratio > product.max_emi_ratio:
            reasons.append(f"EMI burden exceeds maximum ({product.max_emi_ratio}% allowed)")
        else:
            checks_passed += 1

        if customer.age is None:
            reasons.append("Age unavailable")
        elif customer.age < product.min_age or customer.age > product.max_age:
            reasons.append(f"Age outside eligible range ({product.min_age}–{product.max_age})")
        else:
            checks_passed += 1

        persona_match = self._persona_match(customer.persona, product.target_personas)
        if not persona_match:
            reasons.append(f"Persona not in target segment ({', '.join(product.target_personas)})")
        else:
            checks_passed += 1

        relationship_ok = self._relationship_match(customer, product.relationship_preference)
        if not relationship_ok:
            reasons.append(f"Relationship preference not met ({product.relationship_preference})")
            checks_passed = max(0, checks_passed - 1)

        repayment_ok = customer.repayment_capacity not in (None, "Low")
        if not repayment_ok:
            reasons.append("Repayment capacity too low for lending products")

        eligible = len(reasons) == 0 and repayment_ok
        rule_score = checks_passed / total_checks if total_checks else 0.0

        return EligibilityResult(
            product_name=product.name,
            eligible=eligible,
            reasons=reasons,
            rule_score=rule_score,
        )

    def evaluate_all(self, customer: CustomerContext) -> list[EligibilityResult]:
        return [self.evaluate(customer, product) for product in PRODUCT_CATALOG]

    @staticmethod
    def _persona_match(persona: str | None, targets: tuple[str, ...]) -> bool:
        if persona is None:
            return True
        persona_lower = persona.lower()
        return any(t.lower() in persona_lower or persona_lower in t.lower() for t in targets)

    @staticmethod
    def _relationship_match(
        customer: CustomerContext,
        preference: str,
    ) -> bool:
        if preference == "Any":
            return True
        if preference == "Existing":
            return customer.is_existing_customer or (
                customer.relationship_score is not None
                and customer.relationship_score >= Decimal("50")
            )
        if preference == "New":
            return not customer.is_existing_customer
        return True
