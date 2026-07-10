"""Unit tests for the Financial Analytics Engine (deterministic rules)."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.schemas.banking import (
    AccountSchema,
    CustomerProductSchema,
    CustomerSchema,
    ProductSchema,
    TransactionSchema,
)
from app.schemas.customer360 import CustomerAggregate


def _customer(**overrides) -> CustomerSchema:
    defaults = dict(
        customer_id=uuid4(),
        first_name="Arjun",
        last_name="Reddy",
        gender="Male",
        date_of_birth=datetime(1990, 5, 15).date(),
        age=35,
        phone_number="+919876543210",
        email="arjun@test.com",
        occupation="Software Engineer",
        annual_income=Decimal("900000.00"),
        city="Hyderabad",
        state="Telangana",
        preferred_language="Telugu",
        is_existing_customer=True,
        created_at=datetime(2020, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )
    defaults.update(overrides)
    return CustomerSchema(**defaults)


def _salary_txn(account_id, year: int, month: int, amount: str = "75000.00") -> TransactionSchema:
    return TransactionSchema(
        transaction_id=uuid4(),
        account_id=account_id,
        date=datetime(year, month, 1),
        amount=Decimal(amount),
        merchant="SBI Payroll",
        category="Salary",
        transaction_type="CREDIT",
        channel="NEFT",
    )


def _debit_txn(account_id, year: int, month: int, amount: str, category: str = "Shopping") -> TransactionSchema:
    return TransactionSchema(
        transaction_id=uuid4(),
        account_id=account_id,
        date=datetime(year, month, 15),
        amount=Decimal(amount),
        merchant="Amazon",
        category=category,
        transaction_type="DEBIT",
        channel="UPI",
    )


class FinancialAnalyticsEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = FinancialAnalyticsEngine()

    def _build_aggregate(self) -> CustomerAggregate:
        customer = _customer()
        account_id = uuid4()
        account = AccountSchema(
            account_id=account_id,
            customer_id=customer.customer_id,
            account_number="12345678901",
            account_type="Salary",
            branch="SBI Hyderabad",
            ifsc="SBIN0020001",
            balance=Decimal("240000.00"),
            opened_date=datetime(2020, 1, 1).date(),
            status="Active",
        )
        account2 = AccountSchema(
            account_id=uuid4(),
            customer_id=customer.customer_id,
            account_number="12345678902",
            account_type="Savings",
            branch="SBI Hyderabad",
            ifsc="SBIN0020001",
            balance=Decimal("240000.00"),
            opened_date=datetime(2021, 1, 1).date(),
            status="Active",
        )

        transactions = []
        for month in range(1, 13):
            transactions.append(_salary_txn(account_id, 2025, month))
            transactions.append(_debit_txn(account_id, 2025, month, "48000.00"))
            transactions.append(
                _debit_txn(account_id, 2025, month, "9000.00", category="Investment")
            )

        home_loan = CustomerProductSchema(
            customer_product_id=uuid4(),
            customer_id=customer.customer_id,
            product_id=uuid4(),
            opened_date=datetime(2022, 1, 1).date(),
            status="Active",
            product=ProductSchema(
                product_id=uuid4(),
                product_name="Home Loan",
                product_type="Loan",
                description="SBI Home Loan",
            ),
        )

        return CustomerAggregate(
            customer=customer,
            accounts=[account, account2],
            transactions=transactions,
            products=[home_loan],
            consent=None,
        )

    def test_monthly_income_from_salary_credits(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        self.assertEqual(result.monthly_income, Decimal("75000.00"))

    def test_monthly_expense_from_debits(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        # 48000 shopping + 9000 investment = 57000 per month average
        self.assertEqual(result.monthly_expense, Decimal("57000.00"))

    def test_monthly_savings(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        self.assertEqual(result.monthly_savings, Decimal("18000.00"))

    def test_savings_ratio(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        # 18000 / 75000 * 100 = 24%
        self.assertEqual(result.savings_ratio, Decimal("24.00"))

    def test_average_balance(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        self.assertEqual(result.average_balance, Decimal("240000.00"))

    def test_debt_ratio_with_active_home_loan(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        # Home loan EMI = 4% of monthly income = 3000; ratio = 3000/75000*100 = 4%
        self.assertEqual(result.debt_ratio, Decimal("4.00"))
        self.assertEqual(result.emi_burden, Decimal("4.00"))

    def test_investment_ratio(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        # 9000 * 12 = 108000 total; 108000 / 75000 * 100 = 144%
        self.assertEqual(result.investment_ratio, Decimal("144.00"))

    def test_cash_flow_score_in_valid_range(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        self.assertGreaterEqual(result.cash_flow_score, Decimal("0"))
        self.assertLessEqual(result.cash_flow_score, Decimal("100"))

    def test_liquidity_score_in_valid_range(self) -> None:
        aggregate = self._build_aggregate()
        result = self.engine.calculate(aggregate)
        self.assertGreaterEqual(result.liquidity_score, Decimal("0"))
        self.assertLessEqual(result.liquidity_score, Decimal("100"))

    def test_fallback_income_when_no_salary_credits(self) -> None:
        customer = _customer(annual_income=Decimal("600000.00"))
        aggregate = CustomerAggregate(
            customer=customer,
            accounts=[],
            transactions=[_debit_txn(uuid4(), 2025, 6, "10000.00")],
            products=[],
        )
        result = self.engine.calculate(aggregate)
        self.assertEqual(result.monthly_income, Decimal("50000.00"))

    def test_zero_income_produces_zero_ratios(self) -> None:
        customer = _customer(annual_income=Decimal("0.00"))
        aggregate = CustomerAggregate(customer=customer, accounts=[], transactions=[], products=[])
        result = self.engine.calculate(aggregate)
        self.assertEqual(result.debt_ratio, Decimal("0.00"))
        self.assertEqual(result.investment_ratio, Decimal("0.00"))
        self.assertEqual(result.savings_ratio, Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
