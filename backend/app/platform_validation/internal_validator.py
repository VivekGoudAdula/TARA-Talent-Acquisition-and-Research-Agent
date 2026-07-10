"""Internal Intelligence pipeline coverage validation."""

from __future__ import annotations

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe

INTERNAL_PIPELINE_STAGES: list[tuple[str, str]] = [
    ("Customer360", "customer_360_profile"),
    ("Financial Analytics", "customer_360_profile.monthly_expense"),
    ("Transaction Analytics", "transaction_analytics"),
    ("Behaviour Analytics", "behaviour_analytics"),
    ("Relationship Analytics", "relationship_analytics"),
    ("Digital & Channel Analytics", "digital_channel_analytics"),
    ("Customer Health Analytics", "customer_health_analytics"),
    ("Feature Store", "internal_pipeline"),
]


class InternalIntelligenceValidator:
    """Validates every customer completed the internal intelligence pipeline."""

    CATEGORY = "Internal Intelligence"

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> list[ValidationCheck]:
        if not self._probe.table_exists("customers"):
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Internal pipeline coverage",
                    status="FAIL",
                    reason="customers table missing",
                )
            ]

        customer_count = self._probe.count_rows("customers")
        checks: list[ValidationCheck] = []

        profile_count = (
            self._probe.count_rows("customer_360_profile")
            if self._probe.table_exists("customer_360_profile")
            else 0
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Customer360 coverage",
                status="PASS" if profile_count == customer_count else "FAIL",
                reason=f"profiles={profile_count}, customers={customer_count}",
            )
        )

        financial_ready = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM customer_360_profile
                WHERE monthly_expense IS NOT NULL AND cash_flow_score IS NOT NULL
                """
            )
            or 0
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Financial Analytics coverage",
                status="PASS" if financial_ready == customer_count else "FAIL",
                reason=f"profiles_with_financial_kpis={financial_ready}/{customer_count}",
            )
        )

        for stage_name, source_module in INTERNAL_PIPELINE_STAGES[2:]:
            covered = int(
                self._probe.scalar(
                    """
                    SELECT COUNT(DISTINCT customer_id) FROM feature_store
                    WHERE source_module = :source_module
                    """,
                    {"source_module": source_module},
                )
                or 0
            )
            checks.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"{stage_name} coverage",
                    status="PASS" if covered == customer_count else "FAIL",
                    reason=f"customers_with_stage={covered}/{customer_count}",
                    details={"source_module": source_module},
                )
            )

        pipeline_completed = int(
            self._probe.scalar(
                """
                SELECT COUNT(DISTINCT customer_id) FROM feature_store
                WHERE source_module = 'internal_pipeline'
                  AND feature_name = 'pipeline_completed'
                """
            )
            or 0
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Pipeline completion markers",
                status="PASS" if pipeline_completed == customer_count else "FAIL",
                reason=f"pipeline_completed={pipeline_completed}/{customer_count}",
            )
        )

        return checks
