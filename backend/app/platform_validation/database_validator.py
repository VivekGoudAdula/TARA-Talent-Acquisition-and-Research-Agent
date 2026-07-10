"""Database structure and population validation."""

from __future__ import annotations

from app.config import get_settings
from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe


def _expected_tables() -> dict[str, dict[str, str | tuple[int | None, int | None]]]:
    settings = get_settings()
    customers = settings.expected_customer_count
    leads = settings.expected_lead_count
    min_transactions = max(100, customers * 10)
    return {
        "customers": {"pk": "customer_id", "count": (customers, customers)},
        "accounts": {"pk": "account_id", "count": (customers, None)},
        "transactions": {"pk": "transaction_id", "count": (min_transactions, None)},
        "products": {"pk": "product_id", "count": (1, None)},
        "customer_products": {"pk": "customer_product_id", "count": (1, None)},
        "consent": {"pk": "consent_id", "count": (customers, None)},
        "customer_360_profile": {"pk": "profile_id", "count": "match_customers"},
        "feature_store": {"pk": "feature_id", "count": "match_customers_distinct"},
        "external_leads": {"pk": "lead_id", "count": (leads, leads)},
        "external_customer_profile": {"pk": "profile_id", "count": (leads, leads)},
        "lead_feature_store": {"pk": "feature_id", "count": "match_leads_distinct"},
        "training_dataset": {"pk": "record_id", "count": (1, None)},
        "explainability_reports": {"pk": "report_id", "count": (0, None)},
    }

FK_CHECKS: list[tuple[str, str]] = [
    (
        "Orphan accounts (no customer)",
        """
        SELECT COUNT(*) FROM accounts a
        LEFT JOIN customers c ON a.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """,
    ),
    (
        "Orphan transactions (no account)",
        """
        SELECT COUNT(*) FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.account_id
        WHERE a.account_id IS NULL
        """,
    ),
    (
        "Orphan customer_products (no customer)",
        """
        SELECT COUNT(*) FROM customer_products cp
        LEFT JOIN customers c ON cp.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """,
    ),
    (
        "Orphan customer_products (no product)",
        """
        SELECT COUNT(*) FROM customer_products cp
        LEFT JOIN products p ON cp.product_id = p.product_id
        WHERE p.product_id IS NULL
        """,
    ),
    (
        "Orphan consent (no customer)",
        """
        SELECT COUNT(*) FROM consent co
        LEFT JOIN customers c ON co.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """,
    ),
    (
        "Orphan Customer360 profiles (no customer)",
        """
        SELECT COUNT(*) FROM customer_360_profile p
        LEFT JOIN customers c ON p.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """,
    ),
    (
        "Orphan feature_store rows (no customer)",
        """
        SELECT COUNT(*) FROM feature_store f
        LEFT JOIN customers c ON f.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """,
    ),
    (
        "Orphan external profiles (no lead)",
        """
        SELECT COUNT(*) FROM external_customer_profile p
        LEFT JOIN external_leads l ON p.lead_id = l.lead_id
        WHERE l.lead_id IS NULL
        """,
    ),
    (
        "Orphan lead_feature_store rows (no lead)",
        """
        SELECT COUNT(*) FROM lead_feature_store f
        LEFT JOIN external_leads l ON f.lead_id = l.lead_id
        WHERE l.lead_id IS NULL
        """,
    ),
]


class DatabaseValidator:
    """Validates table existence, keys, counts, and referential integrity."""

    CATEGORY = "Database"

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        checks.extend(self._validate_tables())
        checks.extend(self._validate_counts())
        checks.extend(self._validate_referential_integrity())
        checks.extend(self._validate_behaviour_summary_coverage())
        return checks

    def _validate_tables(self) -> list[ValidationCheck]:
        results: list[ValidationCheck] = []
        for table, meta in _expected_tables().items():
            exists = self._probe.table_exists(table)
            if not exists:
                results.append(
                    ValidationCheck(
                        category=self.CATEGORY,
                        name=f"Table exists: {table}",
                        status="FAIL",
                        reason=f"Table '{table}' not found in public schema",
                    )
                )
                continue

            pk = str(meta["pk"])
            pk_cols = self._probe.primary_key_columns(table)
            idx_count = self._probe.index_count(table)
            constraint_count = self._probe.constraint_count(table)
            dup_pk = self._probe.duplicate_pk_count(table, pk)

            status = "PASS" if pk in pk_cols and dup_pk == 0 else "FAIL"
            reason = (
                f"PK={pk_cols}, indexes={idx_count}, constraints={constraint_count}, "
                f"duplicate_pk_groups={dup_pk}"
            )
            results.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Table structure: {table}",
                    status=status,
                    reason=reason,
                    details={
                        "primary_key": pk_cols,
                        "index_count": idx_count,
                        "constraint_count": constraint_count,
                        "duplicate_pk_groups": dup_pk,
                    },
                )
            )
        return results

    def _validate_counts(self) -> list[ValidationCheck]:
        results: list[ValidationCheck] = []
        customer_count = (
            self._probe.count_rows("customers")
            if self._probe.table_exists("customers")
            else 0
        )
        lead_count = (
            self._probe.count_rows("external_leads")
            if self._probe.table_exists("external_leads")
            else 0
        )

        for table, meta in _expected_tables().items():
            if not self._probe.table_exists(table):
                continue

            count_spec = meta["count"]
            actual = self._probe.count_rows(table)

            if count_spec == "match_customers":
                expected, op = customer_count, "eq"
            elif count_spec == "match_customers_distinct":
                actual = self._probe.count_distinct("feature_store", "customer_id")
                expected, op = customer_count, "eq"
            elif count_spec == "match_leads_distinct":
                actual = self._probe.count_distinct("lead_feature_store", "lead_id")
                expected, op = lead_count, "eq"
            else:
                min_count, max_count = count_spec  # type: ignore[misc]
                expected = min_count
                if max_count is not None:
                    op = "eq"
                    expected = max_count
                else:
                    op = "gte"

            if op == "eq":
                ok = actual == expected
                reason = f"count={actual}, expected={expected}"
            else:
                ok = actual >= (expected or 0)
                reason = f"count={actual}, expected>={expected}"

            results.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Record count: {table}",
                    status="PASS" if ok else "FAIL",
                    reason=reason,
                    details={"actual": actual, "expected": expected, "operator": op},
                )
            )
        return results

    def _validate_referential_integrity(self) -> list[ValidationCheck]:
        results: list[ValidationCheck] = []
        for label, sql in FK_CHECKS:
            if not any(
                self._probe.table_exists(t)
                for t in ("customers", "accounts", "external_leads")
            ):
                continue
            orphans = int(self._probe.scalar(sql) or 0)
            results.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Referential integrity: {label}",
                    status="PASS" if orphans == 0 else "FAIL",
                    reason=f"orphan_rows={orphans}",
                )
            )
        return results

    def _validate_behaviour_summary_coverage(self) -> list[ValidationCheck]:
        """behaviour_summary is stored in feature_store, not a standalone table."""
        if not self._probe.table_exists("feature_store"):
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Behaviour summary coverage",
                    status="SKIP",
                    reason="feature_store table not available",
                )
            ]

        internal = int(
            self._probe.scalar(
                """
                SELECT COUNT(DISTINCT customer_id) FROM feature_store
                WHERE source_module = 'behaviour_summary'
                """
            )
            or 0
        )
        lead_rows = 0
        if self._probe.table_exists("lead_feature_store"):
            lead_rows = int(
                self._probe.scalar(
                    """
                    SELECT COUNT(DISTINCT lead_id) FROM lead_feature_store
                    WHERE source_module = 'behaviour_summary'
                    """
                )
                or 0
            )

        return [
            ValidationCheck(
                category=self.CATEGORY,
                name="Behaviour summary (internal feature_store)",
                status="PASS" if internal > 0 else "WARN",
                reason=f"customers_with_behaviour_summary={internal}",
            ),
            ValidationCheck(
                category=self.CATEGORY,
                name="Behaviour summary (lead_feature_store)",
                status="PASS" if lead_rows > 0 else "WARN",
                reason=f"leads_with_behaviour_summary={lead_rows}",
            ),
        ]
