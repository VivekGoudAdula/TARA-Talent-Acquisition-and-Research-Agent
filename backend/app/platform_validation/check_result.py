"""Shared validation check result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CheckStatus = Literal["PASS", "FAIL", "WARN", "SKIP"]


@dataclass
class ValidationCheck:
    """Single auditable validation result."""

    category: str
    name: str
    status: CheckStatus
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CategorySummary:
    """Aggregated status for a validation domain."""

    category: str
    status: CheckStatus
    passed: int
    failed: int
    warned: int
    skipped: int
    checks: list[ValidationCheck] = field(default_factory=list)


def summarize_category(category: str, checks: list[ValidationCheck]) -> CategorySummary:
    passed = sum(1 for c in checks if c.status == "PASS")
    failed = sum(1 for c in checks if c.status == "FAIL")
    warned = sum(1 for c in checks if c.status == "WARN")
    skipped = sum(1 for c in checks if c.status == "SKIP")

    if failed > 0:
        status: CheckStatus = "FAIL"
    elif warned > 0:
        status = "WARN"
    elif passed == 0 and skipped > 0:
        status = "SKIP"
    else:
        status = "PASS"

    return CategorySummary(
        category=category,
        status=status,
        passed=passed,
        failed=failed,
        warned=warned,
        skipped=skipped,
        checks=checks,
    )


def overall_percentage(checks: list[ValidationCheck]) -> str:
    scored = [c for c in checks if c.status in ("PASS", "FAIL")]
    if not scored:
        return "0%"
    rate = round((sum(1 for c in scored if c.status == "PASS") / len(scored)) * 100, 1)
    if rate == int(rate):
        return f"{int(rate)}%"
    return f"{rate}%"
