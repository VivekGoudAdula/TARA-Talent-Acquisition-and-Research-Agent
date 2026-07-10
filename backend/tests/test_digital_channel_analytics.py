"""Unit tests for Digital & Channel Analytics Engine."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.analytics.digital_channel_analytics import (
    ContactTimeAnalyzer,
    DigitalBankingAnalyzer,
    DigitalChannelAnalytics,
)
from app.schemas.banking import ConsentSchema, CustomerSchema, TransactionSchema
from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.digital_channel_input import DigitalChannelAnalyticsInput
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


def _txn(channel: str, hour: int = 14) -> TransactionSchema:
    return TransactionSchema(
        transaction_id=uuid4(),
        account_id=uuid4(),
        date=datetime(2025, 6, 10, hour, 30),
        amount=Decimal("1000"),
        merchant="Amazon",
        category="Shopping",
        transaction_type="DEBIT",
        channel=channel,
    )


class DigitalBankingAnalyzerTests(unittest.TestCase):
    def test_digital_maturity(self) -> None:
        aggregate = CustomerAggregate(
            customer=CustomerSchema(
                customer_id=uuid4(),
                first_name="A",
                last_name="B",
                gender="Male",
                date_of_birth=datetime(1990, 1, 1).date(),
                age=35,
                phone_number="+919999999999",
                email="a@b.com",
                occupation="Engineer",
                annual_income=Decimal("900000"),
                city="Mumbai",
                state="Maharashtra",
                preferred_language="English",
                is_existing_customer=True,
                created_at=datetime(2020, 1, 1),
                updated_at=datetime(2025, 1, 1),
            ),
            transactions=[_txn("UPI"), _txn("Mobile Banking"), _txn("UPI")],
        )
        transaction = TransactionAnalyticsProfile(
            average_transaction_amount=Decimal("1000"),
            monthly_transaction_count=Decimal("50"),
            debit_transaction_count=3,
            credit_transaction_count=1,
            debit_credit_ratio=Decimal("3"),
            cash_withdrawal_frequency=Decimal("0"),
            cash_deposit_frequency=Decimal("0"),
            upi_transaction_count=2,
            card_transaction_count=0,
            net_banking_transaction_count=0,
            mobile_banking_transaction_count=1,
            digital_payment_ratio=Decimal("95"),
            merchant_diversity=2,
            category_diversity=1,
            most_frequent_merchant="Amazon",
            most_frequent_category="Shopping",
            highest_transaction_amount=Decimal("1000"),
            lowest_transaction_amount=Decimal("1000"),
            largest_credit_transaction=Decimal("0"),
            largest_debit_transaction=Decimal("1000"),
            transaction_consistency_score=Decimal("90"),
            income_regularity_score=Decimal("90"),
            expense_stability_score=Decimal("85"),
            weekend_transaction_percentage=Decimal("10"),
            night_transaction_percentage=Decimal("5"),
        )
        result = DigitalBankingAnalyzer().analyze(aggregate, transaction)
        self.assertIn(result.digital_maturity, {"Traditional", "Emerging Digital", "Digital", "Digital First"})
        self.assertGreater(result.digital_adoption_score, Decimal("50"))


class ContactTimeAnalyzerTests(unittest.TestCase):
    def test_preferred_time(self) -> None:
        txns = [_txn("UPI", 18), _txn("UPI", 19), _txn("UPI", 20)]
        aggregate = CustomerAggregate(
            customer=CustomerSchema(
                customer_id=uuid4(),
                first_name="A",
                last_name="B",
                gender="Male",
                date_of_birth=datetime(1990, 1, 1).date(),
                age=35,
                phone_number="+919999999999",
                email="a@b.com",
                occupation="Engineer",
                annual_income=Decimal("900000"),
                city="Mumbai",
                state="Maharashtra",
                preferred_language="English",
                is_existing_customer=True,
                created_at=datetime(2020, 1, 1),
                updated_at=datetime(2025, 1, 1),
            ),
            transactions=txns,
        )
        time, day, _ = ContactTimeAnalyzer().analyze(aggregate)
        self.assertEqual(time, "Evening")


if __name__ == "__main__":
    unittest.main()
