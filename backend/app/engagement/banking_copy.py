"""Professional banking language for customer-facing outreach copy."""

from __future__ import annotations

import re

from app.schemas.engagement import EngagementLeadRecord

# Raw explainability / ML phrases → never show to customers
_JARGON_PATTERNS = re.compile(
    r"machine learning|ml model|model has|llm|algorithm|neural|"
    r"lead priority|marketing priority|conversion probability|"
    r"explainability|feature store|dataset",
    re.IGNORECASE,
)

_REASON_LABELS: dict[str, str] = {
    "stable salary": "Stable income",
    "elevated emi burden": "Existing loan obligations",
    "credit score needs review": "Credit profile under review",
    "high income": "Strong income profile",
    "low debt": "Comfortable debt position",
    "verified consent": "Service consent on record",
}


def humanize_reasons(reason_codes: list[str]) -> str:
    if not reason_codes:
        return "your banking profile and repayment history"
    labels: list[str] = []
    for code in reason_codes[:3]:
        key = code.strip().lower().replace("_", " ")
        labels.append(_REASON_LABELS.get(key, _strip_jargon(code)))
    return ", ".join(labels)


def eligibility_label(conversion_probability: float | None) -> str:
    if conversion_probability is None:
        return "Eligible"
    if conversion_probability >= 80:
        return "High"
    if conversion_probability >= 60:
        return "Good"
    return "Moderate"


def repayment_label(capacity: str | None) -> str:
    if not capacity:
        return "Under review"
    mapping = {
        "high": "Strong",
        "medium": "Adequate",
        "low": "Limited",
    }
    return mapping.get(capacity.strip().lower(), capacity.title())


def professional_insight(record: EngagementLeadRecord) -> str:
    """Short banker-style note — never paste raw LLM explainability text."""
    name = record.name or "you"
    product = record.recommended_product or "a suitable lending product"
    bank_reason = humanize_reasons(record.reason_codes)
    repayment = repayment_label(record.repayment_capacity)

    return (
        f"Based on a review of your profile, {name}, we believe a {product} "
        f"aligns with your needs. Key considerations include {bank_reason}. "
        f"Your indicative repayment comfort is assessed as {repayment}."
    )


def sanitize_text(text: str) -> str:
    """Drop or replace jargon-heavy explainability summaries."""
    if not text or _JARGON_PATTERNS.search(text):
        return ""
    return text.strip()


def format_inr_amount(amount: int | float) -> str:
    """Format as Indian currency e.g. 1500000 -> ₹15,00,000"""
    value = int(amount)
    s = str(value)
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    parts: list[str] = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"₹{','.join(parts + [last3])}"


def _strip_jargon(text: str) -> str:
    cleaned = _JARGON_PATTERNS.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip(" ,.") or text
