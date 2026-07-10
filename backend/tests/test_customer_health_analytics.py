"""Unit tests for Customer Health Analytics Engine."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.analytics.customer_health_analytics import (
    CustomerHealthAnalytics,
    ExplanationEngine,
    FinancialStressAnalyzer,
    RiskBandClassifier,
)
from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.customer_health_input import CustomerHealthAnalyticsInput
from app.schemas.digital_channel_analytics import DigitalChannelProfile
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


def _financial(**kwargs) -> FinancialProfile:
    defaults = dict(
        monthly_income=Decimal("100000"),
        monthly_expense=Decimal("60000"),
        monthly_savings=Decimal("40000"),
        savings_ratio=Decimal("40"),
        average_balance=Decimal("300000"),
        cash_flow_score=Decimal("85"),
        liquidity_score=Decimal("80"),
        debt_ratio=Decimal("10"),
        investment_ratio=Decimal("12"),
        emi_burden=Decimal("10"),
    )
    defaults.update(kwargs)
    return FinancialProfile(**defaults)


def _transaction(**kwargs) -> TransactionAnalyticsProfile:
    defaults = dict(
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
        largest_credit_transaction=Decimal("100000"),
        largest_debit_transaction=Decimal("50000"),
        transaction_consistency_score=Decimal("85"),
        income_regularity_score=Decimal("95"),
        expense_stability_score=Decimal("80"),
        weekend_transaction_percentage=Decimal("25"),
        night_transaction_percentage=Decimal("5"),
    )
    defaults.update(kwargs)
    return TransactionAnalyticsProfile(**defaults)


class FinancialStressTests(unittest.TestCase):
    def test_low_stress_healthy_customer(self) -> None:
        score = FinancialStressAnalyzer().analyze(_financial(), _transaction())
        self.assertLess(score, Decimal("30"))

    def test_high_stress(self) -> None:
        score = FinancialStressAnalyzer().analyze(
            _financial(savings_ratio=Decimal("5"), debt_ratio=Decimal("50"), cash_flow_score=Decimal("30")),
            _transaction(income_regularity_score=Decimal("40")),
        )
        self.assertGreater(score, Decimal("40"))


class RiskBandTests(unittest.TestCase):
    def test_healthy_band(self) -> None:
        band = RiskBandClassifier.classify(Decimal("85"), Decimal("20"), Decimal("15"), "Low")
        self.assertEqual(band, "Healthy")

    def test_critical_band(self) -> None:
        band = RiskBandClassifier.classify(Decimal("25"), Decimal("80"), Decimal("85"), "High")
        self.assertEqual(band, "Critical")


class ExplanationEngineTests(unittest.TestCase):
    def test_generates_reasons(self) -> None:
        reasons = ExplanationEngine.generate(
            Decimal("85"), Decimal("20"), Decimal("15"), "Low",
            _financial(), _transaction(), _digital(), _relationship(),
        )
        self.assertGreater(len(reasons), 0)
        self.assertTrue(any("income" in r.lower() or "savings" in r.lower() for r in reasons))


def _digital() -> DigitalChannelProfile:
    return DigitalChannelProfile(
        customer_id=uuid4(),
        digital_adoption_score=Decimal("85"),
        digital_maturity="Digital",
        preferred_channel="Mobile App",
        secondary_channel="WhatsApp",
        preferred_contact_time="Evening",
        preferred_contact_day="Weekday",
        voice_readiness_score=Decimal("70"),
        sms_readiness_score=Decimal("80"),
        whatsapp_readiness_score=Decimal("85"),
        email_readiness_score=Decimal("60"),
        engagement_score=Decimal("88"),
    )


def _relationship() -> RelationshipProfile:
    return RelationshipProfile(
        customer_id=uuid4(),
        number_of_accounts=2,
        number_of_products=4,
        relationship_age=Decimal("6"),
        relationship_strength_score=Decimal("75"),
        loyalty_score=Decimal("80"),
        product_penetration_score=Decimal("30"),
        product_diversity_score=Decimal("40"),
        bank_dependency_score=Decimal("70"),
        relationship_tier="Gold",
        estimated_customer_value=Decimal("800000"),
        missing_products=["Credit Card"],
        engagement_score=Decimal("75"),
        relationship_stability=Decimal("82"),
        primary_banking_score=Decimal("78"),
    )


def _behaviour(cid) -> BehaviourProfile:
    return BehaviourProfile(
        customer_id=cid,
        shopping_score=Decimal("70"),
        travel_score=Decimal("50"),
        food_score=Decimal("60"),
        healthcare_score=Decimal("30"),
        investment_score=Decimal("65"),
        fuel_score=Decimal("40"),
        education_score=Decimal("20"),
        entertainment_score=Decimal("35"),
        top_interest="Shopping",
        secondary_interest="Investment",
        third_interest=None,
        lifestyle_tags=["Digital Shopper"],
    )


class CustomerHealthEngineTests(unittest.TestCase):
    def test_full_health_profile(self) -> None:
        cid = uuid4()
        data = CustomerHealthAnalyticsInput(
            aggregate=CustomerAggregate(
                customer=__import__("app.schemas.banking", fromlist=["CustomerSchema"]).CustomerSchema(
                    customer_id=cid, first_name="A", last_name="B", gender="Male",
                    date_of_birth=datetime(1990, 1, 1).date(), age=35,
                    phone_number="+919999999999", email="a@b.com", occupation="Engineer",
                    annual_income=Decimal("1200000"), city="Mumbai", state="Maharashtra",
                    preferred_language="English", is_existing_customer=True,
                    created_at=datetime(2018, 1, 1), updated_at=datetime(2025, 1, 1),
                ),
                accounts=[], products=[], transactions=[],
            ),
            profile=Customer360ProfileResponse(
                profile_id=uuid4(), customer_id=cid, age=35, gender="Male",
                occupation="Engineer", annual_income=Decimal("1200000"),
                city="Mumbai", state="Maharashtra", preferred_language="English",
                customer_since=datetime(2018, 1, 1).date(),
                average_balance=Decimal("300000"), monthly_income=Decimal("100000"),
                monthly_expense=None, monthly_savings=None,
                shopping_score=None, travel_score=None, food_score=None,
                investment_score=None, digital_banking_score=None,
                customer_segment=None, preferred_channel=None,
                preferred_contact_time=None, risk_score=None,
                last_updated=datetime.utcnow(),
            ),
            financial=_financial(),
            transaction=_transaction(),
            behaviour=_behaviour(cid),
            relationship=_relationship(),
            digital=_digital(),
        )
        result = CustomerHealthAnalytics().calculate(data)
        self.assertGreater(result.customer_health_score, Decimal("0"))
        self.assertIn(result.risk_band, {"Healthy", "Monitor", "At Risk", "Critical"})
        self.assertIn(result.dormancy_risk, {"Low", "Medium", "High"})
        self.assertGreater(len(result.reason_codes), 0)


if __name__ == "__main__":
    unittest.main()
