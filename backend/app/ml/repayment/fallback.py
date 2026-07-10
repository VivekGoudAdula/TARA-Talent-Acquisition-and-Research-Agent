"""Rule-based repayment capacity when the trained model is unavailable."""

from __future__ import annotations

from typing import Any

from app.schemas.repayment import RepaymentPredictResponse

TIERS = ("Very High", "High", "Medium", "Low")


def _tier_from_signals(
    *,
    income: float | None,
    credit: int | None,
    savings: float | None,
    emi: float | None,
    health: float | None,
) -> str:
    if income is not None and income > 100_000 and credit and credit > 760:
        return "Very High"
    if income is not None and income > 75_000 and credit and credit > 700:
        return "High"
    strength = (
        (credit is not None and credit > 650)
        or (savings is not None and savings > 15.0)
        or (health is not None and health > 60.0)
    )
    if income is not None and income > 40_000 and strength and (emi is None or emi < 45.0):
        return "Medium"
    if health is not None and health >= 50:
        return "Medium"
    return "Low"


def rule_based_repayment_predict(features: dict[str, Any]) -> RepaymentPredictResponse:
    income = features.get("income")
    credit = features.get("credit_score")
    savings = features.get("savings_ratio")
    emi = features.get("emi_burden")
    health = features.get("financial_health_score")

    tier = _tier_from_signals(
        income=float(income) if income is not None else None,
        credit=int(credit) if credit is not None else None,
        savings=float(savings) if savings is not None else None,
        emi=float(emi) if emi is not None else None,
        health=float(health) if health is not None else None,
    )
    confidence = {"Very High": 0.82, "High": 0.78, "Medium": 0.72, "Low": 0.68}[tier]
    probs = {t: 0.05 for t in TIERS}
    probs[tier] = confidence
    remainder = max(0.0, 1.0 - confidence - 0.05 * (len(TIERS) - 1))
    for other in TIERS:
        if other != tier:
            probs[other] += remainder / (len(TIERS) - 1)

    return RepaymentPredictResponse(
        repayment_capacity=tier,
        confidence=confidence,
        probabilities=probs,
        model_used="rule_based_fallback",
    )
