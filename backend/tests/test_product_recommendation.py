"""Unit tests for Product Recommendation Engine."""

import unittest
from decimal import Decimal
from uuid import uuid4

from app.ml.product_recommendation.catalog import PRODUCT_PERSONAL_LOAN, get_product_catalog
from app.ml.product_recommendation.customer_context import CustomerContext
from app.ml.product_recommendation.eligibility import EligibilityEngine
from app.ml.product_recommendation.ranking import ProductRankingEngine


def _eligible_customer(**overrides) -> CustomerContext:
    base = dict(
        profile_id=uuid4(),
        profile_type="Internal",
        is_existing_customer=True,
        age=35,
        monthly_income=Decimal("120000"),
        credit_score=780,
        emi_ratio=Decimal("20"),
        persona="Salary Elite",
        occupation="Engineer",
        city="Mumbai",
        relationship_score=Decimal("75"),
        financial_health_score=Decimal("82"),
        financial_capacity_score=None,
        customer_value_score=Decimal("70"),
        repayment_capacity="Very High",
        repayment_confidence=0.92,
        repayment_probabilities={
            "Low": 0.02,
            "Medium": 0.06,
            "High": 0.22,
            "Very High": 0.70,
        },
    )
    base.update(overrides)
    return CustomerContext(**base)


class ProductCatalogTests(unittest.TestCase):
    def test_catalog_has_five_lending_products(self) -> None:
        catalog = get_product_catalog()
        self.assertEqual(len(catalog), 5)
        names = {p.name for p in catalog}
        self.assertIn("Personal Loan", names)
        self.assertIn("Home Loan", names)
        self.assertIn("Auto Loan", names)
        self.assertIn("Mortgage Loan", names)
        self.assertIn("Education Loan", names)


class EligibilityEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EligibilityEngine()

    def test_eligible_customer_passes_personal_loan(self) -> None:
        customer = _eligible_customer()
        product = next(p for p in get_product_catalog() if p.name == PRODUCT_PERSONAL_LOAN)
        result = self.engine.evaluate(customer, product)
        self.assertTrue(result.eligible)
        self.assertEqual(result.reasons, [])

    def test_low_repayment_fails_eligibility(self) -> None:
        customer = _eligible_customer(repayment_capacity="Low")
        product = next(p for p in get_product_catalog() if p.name == PRODUCT_PERSONAL_LOAN)
        result = self.engine.evaluate(customer, product)
        self.assertFalse(result.eligible)
        self.assertTrue(any("Repayment capacity" in r for r in result.reasons))

    def test_low_income_fails_mortgage(self) -> None:
        customer = _eligible_customer(monthly_income=Decimal("40000"))
        product = next(p for p in get_product_catalog() if p.name == "Mortgage Loan")
        result = self.engine.evaluate(customer, product)
        self.assertFalse(result.eligible)


class ProductRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.eligibility = EligibilityEngine()
        self.ranking = ProductRankingEngine()

    def test_rank_returns_top_products_sorted(self) -> None:
        customer = _eligible_customer()
        eligibility = self.eligibility.evaluate_all(customer)
        ranked = self.ranking.rank(customer, eligibility, top_n=5)
        self.assertEqual(len(ranked), 5)
        self.assertGreater(ranked[0].probability, 0)
        self.assertGreaterEqual(ranked[0].probability, ranked[-1].probability)

    def test_ineligible_products_rank_lower(self) -> None:
        customer = _eligible_customer(
            monthly_income=Decimal("15000"),
            credit_score=550,
            repayment_capacity="Low",
        )
        eligibility = self.eligibility.evaluate_all(customer)
        ranked = self.ranking.rank(customer, eligibility, top_n=5)
        eligible_probs = [r.probability for r in ranked if r.eligible]
        ineligible_probs = [r.probability for r in ranked if not r.eligible]
        if eligible_probs and ineligible_probs:
            self.assertGreater(max(eligible_probs), max(ineligible_probs))


if __name__ == "__main__":
    unittest.main()
