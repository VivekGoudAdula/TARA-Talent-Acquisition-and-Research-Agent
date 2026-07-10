"""Unit tests for Transaction Analytics Engine."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.analytics.transaction_analytics import TransactionAnalytics
from app.schemas.banking import CustomerSchema, TransactionSchema
from app.schemas.customer360 import CustomerAggregate


def _txn(
    *,
    txn_type: str = "DEBIT",
    channel: str = "UPI",
    category: str = "Shopping",
    merchant: str = "Amazon",
    amount: str = "1000.00",
    year: int = 2025,
    month: int = 6,
    day: int = 10,
    hour: int = 14,
) -> TransactionSchema:
    return TransactionSchema(
        transaction_id=uuid4(),
        account_id=uuid4(),
        date=datetime(year, month, day, hour, 0, 0),
        amount=Decimal(amount),
        merchant=merchant,
        category=category,
        transaction_type=txn_type,
        channel=channel,
    )


def _customer() -> CustomerSchema:
    return CustomerSchema(
        customer_id=uuid4(),
        first_name="Test",
        last_name="User",
        gender="Male",
        date_of_birth=datetime(1990, 1, 1).date(),
        age=35,
        phone_number="+919999999999",
        email="test@test.com",
        occupation="Engineer",
        annual_income=Decimal("900000"),
        city="Mumbai",
        state="Maharashtra",
        preferred_language="English",
        is_existing_customer=True,
        created_at=datetime(2020, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


class TransactionAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TransactionAnalytics()

    def _sample_aggregate(self) -> CustomerAggregate:
        txns = []
        for month in range(1, 13):
            txns.append(_txn(txn_type="CREDIT", category="Salary", channel="NEFT", merchant="SBI Payroll", amount="75000", month=month))
            for _ in range(5):
                txns.append(_txn(channel="UPI", merchant="Amazon", month=month))
                txns.append(_txn(channel="Debit Card", merchant="Flipkart", month=month))
            txns.append(_txn(category="ATM Withdrawal", channel="ATM", month=month))
        txns.append(_txn(amount="50000", merchant="IRCTC", category="Travel"))
        return CustomerAggregate(customer=_customer(), accounts=[], transactions=txns, products=[])

    def test_average_transaction_amount(self) -> None:
        agg = self._sample_aggregate()
        txns = self.engine._window_transactions(agg)
        result = self.engine.average_transaction_amount(txns)
        self.assertGreater(result, Decimal("0"))

    def test_debit_credit_ratio(self) -> None:
        agg = self._sample_aggregate()
        txns = self.engine._window_transactions(agg)
        debits = self.engine.debit_transaction_count(txns)
        credits = self.engine.credit_transaction_count(txns)
        ratio = self.engine.debit_credit_ratio(txns)
        self.assertEqual(ratio, (Decimal(debits) / Decimal(credits)).quantize(Decimal("0.01")))

    def test_digital_payment_ratio(self) -> None:
        agg = self._sample_aggregate()
        txns = self.engine._window_transactions(agg)
        ratio = self.engine.digital_payment_ratio(txns)
        self.assertGreater(ratio, Decimal("80"))

    def test_merchant_diversity(self) -> None:
        agg = self._sample_aggregate()
        txns = self.engine._window_transactions(agg)
        self.assertGreaterEqual(self.engine.merchant_diversity(txns), 3)

    def test_most_frequent_merchant(self) -> None:
        agg = self._sample_aggregate()
        txns = self.engine._window_transactions(agg)
        self.assertEqual(self.engine.most_frequent_merchant(txns), "Amazon")

    def test_scores_in_range(self) -> None:
        result = self.engine.calculate(self._sample_aggregate())
        for score in (
            result.transaction_consistency_score,
            result.income_regularity_score,
            result.expense_stability_score,
        ):
            self.assertGreaterEqual(score, Decimal("0"))
            self.assertLessEqual(score, Decimal("100"))

    def test_full_calculate_returns_all_fields(self) -> None:
        result = self.engine.calculate(self._sample_aggregate())
        self.assertIsNotNone(result.most_frequent_category)
        self.assertGreater(result.monthly_transaction_count, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
