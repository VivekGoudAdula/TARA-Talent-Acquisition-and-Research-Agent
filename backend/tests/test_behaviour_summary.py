"""Unit tests for Behaviour Analytics Summary aggregators."""

import unittest
from decimal import Decimal

from app.behaviour_summary.external_aggregator import (
    ExternalBehaviourSummaryAggregator,
    ExternalSummaryInput,
)
from app.behaviour_summary.internal_aggregator import (
    InternalBehaviourSummaryAggregator,
    InternalSummaryInput,
)


class InternalBehaviourSummaryAggregatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.aggregator = InternalBehaviourSummaryAggregator()

    def test_aggregate_returns_three_scores_in_range(self) -> None:
        data = InternalSummaryInput(
            customer_health_score=Decimal("85"),
            financial_stress_score=Decimal("20"),
            monthly_income=Decimal("100000"),
            monthly_savings=Decimal("25000"),
            cash_flow_score=Decimal("80"),
            liquidity_score=Decimal("75"),
            debt_ratio=Decimal("30"),
            income_regularity_score=Decimal("90"),
            emi_burden=Decimal("25"),
            expense_stability_score=Decimal("70"),
            digital_payment_ratio=Decimal("65"),
            digital_adoption_score=Decimal("88"),
            voice_readiness_score=Decimal("80"),
            sms_readiness_score=Decimal("75"),
            whatsapp_readiness_score=Decimal("90"),
            email_readiness_score=Decimal("70"),
            upi_usage_score=Decimal("85"),
            net_banking_usage_score=Decimal("60"),
        )
        financial, repayment, digital = self.aggregator.aggregate(data)
        for score in (financial, repayment, digital):
            self.assertGreaterEqual(score, Decimal("0"))
            self.assertLessEqual(score, Decimal("100"))

    def test_financial_health_uses_inverted_stress_and_debt(self) -> None:
        low_stress = InternalSummaryInput(
            customer_health_score=Decimal("90"),
            financial_stress_score=Decimal("10"),
            monthly_income=Decimal("100000"),
            monthly_savings=Decimal("30000"),
            cash_flow_score=Decimal("85"),
            liquidity_score=Decimal("80"),
            debt_ratio=Decimal("15"),
            income_regularity_score=None,
            emi_burden=None,
            expense_stability_score=None,
            digital_payment_ratio=None,
            digital_adoption_score=None,
            voice_readiness_score=None,
            sms_readiness_score=None,
            whatsapp_readiness_score=None,
            email_readiness_score=None,
            upi_usage_score=None,
            net_banking_usage_score=None,
        )
        high_stress = InternalSummaryInput(
            customer_health_score=Decimal("90"),
            financial_stress_score=Decimal("80"),
            monthly_income=Decimal("100000"),
            monthly_savings=Decimal("30000"),
            cash_flow_score=Decimal("85"),
            liquidity_score=Decimal("80"),
            debt_ratio=Decimal("85"),
            income_regularity_score=None,
            emi_burden=None,
            expense_stability_score=None,
            digital_payment_ratio=None,
            digital_adoption_score=None,
            voice_readiness_score=None,
            sms_readiness_score=None,
            whatsapp_readiness_score=None,
            email_readiness_score=None,
            upi_usage_score=None,
            net_banking_usage_score=None,
        )
        low_score = self.aggregator.aggregate(low_stress)[0]
        high_score = self.aggregator.aggregate(high_stress)[0]
        self.assertGreater(low_score, high_score)


class ExternalBehaviourSummaryAggregatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.aggregator = ExternalBehaviourSummaryAggregator()

    def test_aggregate_returns_three_scores_in_range(self) -> None:
        data = ExternalSummaryInput(
            financial_capacity_score=Decimal("82"),
            lead_quality_score=Decimal("78"),
            income_confidence_score=Decimal("75"),
            estimated_repayment_capacity=Decimal("15000"),
            estimated_income=Decimal("600000"),
            income_stability_score=Decimal("75"),
            credit_quality="Good",
            lead_authenticity_score=Decimal("88"),
            digital_readiness_score=Decimal("80"),
            communication_readiness_score=Decimal("72"),
            campaign_engagement_score=Decimal("68"),
            preferred_channel="WhatsApp",
        )
        financial, repayment, digital = self.aggregator.aggregate(data)
        for score in (financial, repayment, digital):
            self.assertGreaterEqual(score, Decimal("0"))
            self.assertLessEqual(score, Decimal("100"))

    def test_financial_health_weighted_from_capacity_quality_confidence(self) -> None:
        data = ExternalSummaryInput(
            financial_capacity_score=Decimal("90"),
            lead_quality_score=Decimal("80"),
            income_confidence_score=Decimal("70"),
            estimated_repayment_capacity=None,
            estimated_income=None,
            income_stability_score=None,
            credit_quality=None,
            lead_authenticity_score=None,
            digital_readiness_score=None,
            communication_readiness_score=None,
            campaign_engagement_score=None,
            preferred_channel=None,
        )
        score = self.aggregator.aggregate(data)[0]
        self.assertEqual(score, Decimal("81.00"))


if __name__ == "__main__":
    unittest.main()
