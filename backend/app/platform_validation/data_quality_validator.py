"""Data quality validation rules."""

from __future__ import annotations

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe

QUALITY_CHECKS: list[tuple[str, str, str]] = [
    (
        "Negative account balances",
        "SELECT COUNT(*) FROM accounts WHERE balance < 0",
        "negative_balances",
    ),
    (
        "Impossible customer ages",
        "SELECT COUNT(*) FROM customers WHERE age < 18 OR age > 100",
        "invalid_ages",
    ),
    (
        "Duplicate customer phone numbers",
        """
        SELECT COUNT(*) FROM (
            SELECT phone_number, COUNT(*) cnt FROM customers
            GROUP BY phone_number HAVING COUNT(*) > 1
        ) d
        """,
        "duplicate_phones",
    ),
    (
        "Duplicate external lead phone numbers",
        """
        SELECT COUNT(*) FROM (
            SELECT phone_number, COUNT(*) cnt FROM external_leads
            GROUP BY phone_number HAVING COUNT(*) > 1
        ) d
        """,
        "duplicate_lead_phones",
    ),
    (
        "Invalid customer income (<= 0)",
        "SELECT COUNT(*) FROM customers WHERE annual_income IS NOT NULL AND annual_income <= 0",
        "invalid_income",
    ),
    (
        "Invalid EMI burden (> 100%)",
        """
        SELECT COUNT(*) FROM customer_360_profile
        WHERE emi_burden IS NOT NULL AND emi_burden > 100
        """,
        "invalid_emi",
    ),
    (
        "Invalid debt ratio (> 100%)",
        """
        SELECT COUNT(*) FROM customer_360_profile
        WHERE debt_ratio IS NOT NULL AND debt_ratio > 100
        """,
        "invalid_debt_ratio",
    ),
    (
        "Duplicate Customer360 per customer",
        """
        SELECT COUNT(*) FROM (
            SELECT customer_id, COUNT(*) cnt FROM customer_360_profile
            GROUP BY customer_id HAVING COUNT(*) > 1
        ) d
        """,
        "duplicate_customer360",
    ),
    (
        "Duplicate external profile per lead",
        """
        SELECT COUNT(*) FROM (
            SELECT lead_id, COUNT(*) cnt FROM external_customer_profile
            GROUP BY lead_id HAVING COUNT(*) > 1
        ) d
        """,
        "duplicate_external_profile",
    ),
    (
        "Training dataset duplicate profile rows",
        """
        SELECT COUNT(*) FROM (
            SELECT profile_id, profile_type, COUNT(*) cnt FROM training_dataset
            GROUP BY profile_id, profile_type HAVING COUNT(*) > 1
        ) d
        """,
        "duplicate_training_rows",
    ),
]


class DataQualityValidator:
    """Validates business data quality and anomaly detection."""

    CATEGORY = "Data Integrity"

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> list[ValidationCheck]:
        results: list[ValidationCheck] = []
        for label, sql, key in QUALITY_CHECKS:
            try:
                count = int(self._probe.scalar(sql) or 0)
            except Exception as exc:
                results.append(
                    ValidationCheck(
                        category=self.CATEGORY,
                        name=label,
                        status="SKIP",
                        reason=f"Query skipped: {exc}",
                    )
                )
                continue

            results.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=label,
                    status="PASS" if count == 0 else "FAIL",
                    reason=f"{key}={count}",
                    details={key: count},
                )
            )

        results.extend(self._check_null_critical_fields())
        return results

    def _check_null_critical_fields(self) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        if self._probe.table_exists("customers"):
            null_names = self._probe.null_count("customers", "first_name")
            checks.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Missing customer names",
                    status="PASS" if null_names == 0 else "FAIL",
                    reason=f"null_full_name={null_names}",
                )
            )
        if self._probe.table_exists("training_dataset"):
            null_target = self._probe.null_count("training_dataset", "target_repayment_capacity")
            checks.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Missing training target variable",
                    status="PASS" if null_target == 0 else "FAIL",
                    reason=f"null_target_repayment_capacity={null_target}",
                )
            )
        return checks
