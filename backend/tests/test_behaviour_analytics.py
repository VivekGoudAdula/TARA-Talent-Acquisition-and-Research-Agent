"""Unit tests for Behaviour Analytics Engine."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.analytics.behaviour_analytics import (
    BehaviourAnalyticsEngine,
    FoodBehaviourAnalyzer,
    MerchantCategoryConfig,
    ShoppingBehaviourAnalyzer,
)
from app.schemas.banking import CustomerSchema, TransactionSchema
from app.schemas.behaviour_input import BehaviourAnalyticsInput
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.financial_profile import FinancialProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


def _customer() -> CustomerSchema:
    return CustomerSchema(
        customer_id=uuid4(),
        first_name="A",
        last_name="B",
        gender="Female",
        date_of_birth=datetime(1992, 1, 1).date(),
        age=33,
        phone_number="+919999999999",
        email="a@b.com",
        occupation="Engineer",
        annual_income=Decimal("1200000"),
        city="Bangalore",
        state="Karnataka",
        preferred_language="English",
        is_existing_customer=True,
        created_at=datetime(2020, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


def _debit(merchant: str, amount: str, category: str = "Shopping", month: int = 6) -> TransactionSchema:
    return TransactionSchema(
        transaction_id=uuid4(),
        account_id=uuid4(),
        date=datetime(2025, month, 15, 12, 0),
        amount=Decimal(amount),
        merchant=merchant,
        category=category,
        transaction_type="DEBIT",
        channel="UPI",
    )


class MerchantCategoryConfigTests(unittest.TestCase):
    def test_resolve_from_config(self) -> None:
        config = MerchantCategoryConfig()
        self.assertEqual(config.resolve_category("Amazon", "Shopping"), "Shopping")
        self.assertEqual(config.resolve_category("Swiggy", "Food"), "Food")

    def test_luxury_flag(self) -> None:
        config = MerchantCategoryConfig()
        self.assertTrue(config.is_luxury("Myntra"))


class BehaviourAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = MerchantCategoryConfig()
        self.income = Decimal("100000")

    def test_shopping_analyzer(self) -> None:
        aggregate = CustomerAggregate(
            customer=_customer(),
            transactions=[
                _debit("Amazon", "2000"),
                _debit("Myntra", "8000"),
                _debit("DMart", "500"),
            ],
        )
        result = ShoppingBehaviourAnalyzer(self.config).analyze(aggregate, self.income)
        self.assertGreater(result.shopping_score, Decimal("0"))
        self.assertEqual(result.top_shopping_merchant, "Amazon")

    def test_food_analyzer(self) -> None:
        aggregate = CustomerAggregate(
            customer=_customer(),
            transactions=[_debit("Swiggy", "400", "Food"), _debit("Zomato", "600", "Food")],
        )
        result = FoodBehaviourAnalyzer(self.config).analyze(aggregate, self.income)
        self.assertGreater(result.food_score, Decimal("0"))


class BehaviourEngineTests(unittest.TestCase):
    def test_full_profile_with_lifestyle_tags(self) -> None:
        customer = _customer()
        aggregate = CustomerAggregate(
            customer=customer,
            transactions=[
                _debit("Amazon", "5000", "Shopping", 1),
                _debit("Flipkart", "3000", "Shopping", 2),
                _debit("Swiggy", "500", "Food", 1),
                _debit("Zomato", "600", "Food", 2),
                _debit("Groww", "10000", "Investment", 3),
                _debit("Netflix", "499", "Entertainment", 4),
            ],
        )
        financial = FinancialProfile(
            monthly_income=Decimal("100000"),
            monthly_expense=Decimal("60000"),
            monthly_savings=Decimal("40000"),
            savings_ratio=Decimal("40"),
            average_balance=Decimal("200000"),
            cash_flow_score=Decimal("80"),
            liquidity_score=Decimal("75"),
            debt_ratio=Decimal("0"),
            investment_ratio=Decimal("12"),
            emi_burden=Decimal("0"),
        )
        transaction = TransactionAnalyticsProfile(
            average_transaction_amount=Decimal("2000"),
            monthly_transaction_count=Decimal("10"),
            debit_transaction_count=6,
            credit_transaction_count=1,
            debit_credit_ratio=Decimal("6"),
            cash_withdrawal_frequency=Decimal("0"),
            cash_deposit_frequency=Decimal("0"),
            upi_transaction_count=6,
            card_transaction_count=0,
            net_banking_transaction_count=0,
            mobile_banking_transaction_count=0,
            digital_payment_ratio=Decimal("95"),
            merchant_diversity=5,
            category_diversity=4,
            most_frequent_merchant="Amazon",
            most_frequent_category="Shopping",
            highest_transaction_amount=Decimal("10000"),
            lowest_transaction_amount=Decimal("499"),
            largest_credit_transaction=Decimal("0"),
            largest_debit_transaction=Decimal("10000"),
            transaction_consistency_score=Decimal("85"),
            income_regularity_score=Decimal("90"),
            expense_stability_score=Decimal("80"),
            weekend_transaction_percentage=Decimal("20"),
            night_transaction_percentage=Decimal("5"),
        )
        profile = Customer360ProfileResponse(
            profile_id=uuid4(),
            customer_id=customer.customer_id,
            age=33,
            gender="Female",
            occupation="Engineer",
            annual_income=Decimal("1200000"),
            city="Bangalore",
            state="Karnataka",
            preferred_language="English",
            customer_since=datetime(2020, 1, 1).date(),
            average_balance=Decimal("200000"),
            monthly_income=Decimal("100000"),
            monthly_expense=None,
            monthly_savings=None,
            shopping_score=None,
            travel_score=None,
            food_score=None,
            investment_score=None,
            digital_banking_score=None,
            customer_segment=None,
            preferred_channel=None,
            preferred_contact_time=None,
            risk_score=None,
            last_updated=datetime.utcnow(),
        )
        data = BehaviourAnalyticsInput(
            aggregate=aggregate,
            financial=financial,
            transaction=transaction,
            profile=profile,
        )
        result = BehaviourAnalyticsEngine().calculate(data)
        self.assertGreater(result.shopping_score, Decimal("0"))
        self.assertIsNotNone(result.top_interest)
        self.assertIsInstance(result.lifestyle_tags, list)


if __name__ == "__main__":
    unittest.main()
