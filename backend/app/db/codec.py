"""BSON ↔ Python type conversion for MongoDB documents."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


UUID_FIELDS = frozenset(
    {
        "customer_id",
        "account_id",
        "transaction_id",
        "product_id",
        "customer_product_id",
        "consent_id",
        "profile_id",
        "lead_id",
        "feature_id",
        "record_id",
        "report_id",
    }
)


def encode_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, dict):
        return {k: encode_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode_value(v) for v in value]
    return value


DECIMAL_FIELDS = frozenset(
    {
        "annual_income",
        "balance",
        "amount",
        "emi_burden",
        "debt_ratio",
        "monthly_expense",
        "monthly_income",
        "monthly_savings",
        "monthly_emi",
        "credit_limit",
        "interest_rate",
        "loan_amount",
        "estimated_income",
        "estimated_repayment_capacity",
        "financial_health_score",
        "repayment_behaviour_score",
        "digital_engagement_score",
        "cash_flow_score",
        "relationship_score",
        "channel_engagement_score",
        "health_score",
        "customer_health_score",
        "financial_stress_score",
        "liquidity_score",
        "income_regularity_score",
        "expense_stability_score",
        "digital_payment_ratio",
        "digital_adoption_score",
        "voice_readiness_score",
        "sms_readiness_score",
        "whatsapp_readiness_score",
        "email_readiness_score",
        "lead_score",
        "credit_score",
        "financial_capacity_score",
        "lead_quality_score",
        "campaign_engagement_score",
        "digital_readiness_score",
        "communication_readiness_score",
        "lead_authenticity_score",
        "income_confidence_score",
        "fraud_score",
        "cross_sell_potential",
        "relationship_potential",
        "financial_stability",
        "feature_value_numeric",
        "conversion_probability",
        "repayment_probability",
        "repayment_confidence",
        "repayment_capacity_predicted",
        "top_product_confidence",
        "conversion_probability",
    }
)


def _is_decimal_field(key: str) -> bool:
    if key in DECIMAL_FIELDS:
        return True
    return key.endswith(
        ("_score", "_ratio", "_burden", "_capacity", "_emi", "_savings", "_probability")
    ) or key.startswith(("monthly_", "estimated_"))


def decode_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in UUID_FIELDS and isinstance(value, str):
        return UUID(value)
    if _is_decimal_field(key) and isinstance(value, str):
        try:
            return Decimal(value)
        except Exception:
            pass
    if isinstance(value, datetime) and key.endswith("_date") and "since" not in key:
        return value.date()
    return value


def encode_document(data: dict[str, Any]) -> dict[str, Any]:
    encoded = {k: encode_value(v) for k, v in data.items() if v is not None}
    if "_id" in encoded:
        del encoded["_id"]
    return encoded


def decode_document(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    result = {k: decode_value(k, v) for k, v in doc.items() if k != "_id"}
    return result
