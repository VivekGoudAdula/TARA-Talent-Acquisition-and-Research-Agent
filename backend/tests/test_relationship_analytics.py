"""Unit tests for Relationship Analytics Engine."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.analytics.relationship_analytics import (
    AccountAnalytics,
    ProductGapAnalyzer,
    ProductPortfolioAnalyzer,
    RelationshipAnalytics,
    SBI_PRODUCT_CATALOG,
)
from app.schemas.banking import AccountSchema, CustomerProductSchema, CustomerSchema, ProductSchema
from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_input import RelationshipAnalyticsInput
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


def _customer() -> CustomerSchema:
    return CustomerSchema(
        customer_id=uuid4(),
        first_name="Ravi",
        last_name="Kumar",
        gender="Male",
        date_of_birth=datetime(1988, 1, 1).date(),
        age=37,
        phone_number="+919999999999",
        email="ravi@test.com",
        occupation="Engineer",
        annual_income=Decimal("1500000"),
        city="Chennai",
        state="Tamil Nadu",
        preferred_language="Tamil",
        is_existing_customer=True,
        created_at=datetime(2018, 6, 1),
        updated_at=datetime(2025, 1, 1),
    )


def _product(name: str) -> CustomerProductSchema:
    return CustomerProductSchema(
        customer_product_id=uuid4(),
        customer_id=uuid4(),
        product_id=uuid4(),
        opened_date=datetime(2020, 1, 1).date(),
        status="Active",
        product=ProductSchema(
            product_id=uuid4(),
            product_name=name,
            product_type="Deposit",
            description=None,
        ),
    )


class AccountAnalyticsTests(unittest.TestCase):
    def test_account_counts(self) -> None:
        customer = _customer()
        accounts = [
            AccountSchema(
                account_id=uuid4(),
                customer_id=customer.customer_id,
                account_number="111",
                account_type="Savings",
                branch="SBI",
                ifsc="SBIN0001",
                balance=Decimal("100000"),
                opened_date=datetime(2019, 1, 1).date(),
                status="Active",
            ),
            AccountSchema(
                account_id=uuid4(),
                customer_id=customer.customer_id,
                account_number="222",
                account_type="Salary",
                branch="SBI",
                ifsc="SBIN0001",
                balance=Decimal("50000"),
                opened_date=datetime(2021, 1, 1).date(),
                status="Active",
            ),
        ]
        aggregate = CustomerAggregate(customer=customer, accounts=accounts)
        result = AccountAnalytics().analyze(aggregate)
        self.assertEqual(result.number_of_accounts, 2)
        self.assertEqual(result.savings_accounts, 1)
        self.assertEqual(result.salary_accounts, 1)


class ProductGapTests(unittest.TestCase):
    def test_missing_products(self) -> None:
        customer = _customer()
        products = [
            _product("Savings Account"),
            _product("Fixed Deposit"),
            _product("Life Insurance"),
        ]
        for p in products:
            p.customer_id = customer.customer_id
        aggregate = CustomerAggregate(customer=customer, products=products)
        missing = ProductGapAnalyzer().analyze(aggregate)
        self.assertIn("Credit Card", missing)
        self.assertIn("Home Loan", missing)
        self.assertNotIn("Savings Account", missing)

    def test_penetration_score(self) -> None:
        score = ProductGapAnalyzer.penetration_score(3, len(SBI_PRODUCT_CATALOG))
        self.assertGreater(score, Decimal("0"))


class RelationshipEngineTests(unittest.TestCase):
    def _minimal_input(self) -> RelationshipAnalyticsInput:
        customer = _customer()
        products = [_product("Savings Account"), _product("Credit Card"), _product("Fixed Deposit")]
        for p in products:
            p.customer_id = customer.customer_id
        aggregate = CustomerAggregate(
            customer=customer,
            accounts=[
                AccountSchema(
                    account_id=uuid4(),
                    customer_id=customer.customer_id,
                    account_number="111",
                    account_type="Salary",
                    branch="SBI",
                    ifsc="SBIN0001",
                    balance=Decimal("300000"),
                    opened_date=datetime(2019, 1, 1).date(),
                    status="Active",
                )
            ],
            products=products,
            transactions=[],
        )
        financial = FinancialProfile(
            monthly_income=Decimal("125000"),
            monthly_expense=Decimal("80000"),
            monthly_savings=Decimal("45000"),
            savings_ratio=Decimal("36"),
            average_balance=Decimal("300000"),
            cash_flow_score=Decimal("85"),
            liquidity_score=Decimal("80"),
            debt_ratio=Decimal("5"),
            investment_ratio=Decimal("10"),
            emi_burden=Decimal("5"),
        )
        transaction = TransactionAnalyticsProfile(
            average_transaction_amount=Decimal("2000"),
            monthly_transaction_count=Decimal("80"),
            debit_transaction_count=70,
            credit_transaction_count=10,
            debit_credit_ratio=Decimal("7"),
            cash_withdrawal_frequency=Decimal("2"),
            cash_deposit_frequency=Decimal("0"),
            upi_transaction_count=50,
            card_transaction_count=20,
            net_banking_transaction_count=5,
            mobile_banking_transaction_count=10,
            digital_payment_ratio=Decimal("90"),
            merchant_diversity=15,
            category_diversity=6,
            most_frequent_merchant="Amazon",
            most_frequent_category="Shopping",
            highest_transaction_amount=Decimal("50000"),
            lowest_transaction_amount=Decimal("100"),
            largest_credit_transaction=Decimal("125000"),
            largest_debit_transaction=Decimal("50000"),
            transaction_consistency_score=Decimal("85"),
            income_regularity_score=Decimal("95"),
            expense_stability_score=Decimal("80"),
            weekend_transaction_percentage=Decimal("25"),
            night_transaction_percentage=Decimal("5"),
        )
        behaviour = BehaviourProfile(
            customer_id=customer.customer_id,
            shopping_score=Decimal("70"),
            travel_score=Decimal("40"),
            food_score=Decimal("60"),
            healthcare_score=Decimal("30"),
            investment_score=Decimal("55"),
            fuel_score=Decimal("45"),
            education_score=Decimal("20"),
            entertainment_score=Decimal("35"),
            top_interest="Shopping",
            secondary_interest="Food",
            third_interest=None,
            lifestyle_tags=["Digital Shopper"],
        )
        profile = Customer360ProfileResponse(
            profile_id=uuid4(),
            customer_id=customer.customer_id,
            age=37,
            gender="Male",
            occupation="Engineer",
            annual_income=Decimal("1500000"),
            city="Chennai",
            state="Tamil Nadu",
            preferred_language="Tamil",
            customer_since=datetime(2018, 6, 1).date(),
            average_balance=Decimal("300000"),
            monthly_income=Decimal("125000"),
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
        return RelationshipAnalyticsInput(
            aggregate=aggregate,
            profile=profile,
            financial=financial,
            transaction=transaction,
            behaviour=behaviour,
        )

    def test_full_relationship_profile(self) -> None:
        result = RelationshipAnalytics().calculate(self._minimal_input())
        self.assertGreater(result.relationship_age, Decimal("5"))
        self.assertEqual(result.number_of_products, 3)
        self.assertIn(result.relationship_tier, {"Bronze", "Silver", "Gold", "Platinum", "Diamond"})
        self.assertGreater(result.relationship_strength_score, Decimal("0"))
        self.assertIsInstance(result.missing_products, list)


if __name__ == "__main__":
    unittest.main()
