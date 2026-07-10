"""External Intelligence pipeline coverage validation."""

from __future__ import annotations

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe

EXTERNAL_STAGES: list[tuple[str, str, str]] = [
    ("Import", "external_leads", "lead_id"),
    ("Enrichment", "external_customer_profile", "profile_id"),
    ("Lead Analytics", "lead_feature_store", "external_lead_analytics"),
    ("Lead Intelligence", "lead_feature_store", "external_lead_intelligence"),
    ("Behaviour Summary", "lead_feature_store", "behaviour_summary"),
]


class ExternalIntelligenceValidator:
    """Validates every external lead completed the external intelligence pipeline."""

    CATEGORY = "External Intelligence"

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> list[ValidationCheck]:
        if not self._probe.table_exists("external_leads"):
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="External pipeline coverage",
                    status="FAIL",
                    reason="external_leads table missing",
                )
            ]

        lead_count = self._probe.count_rows("external_leads")
        checks: list[ValidationCheck] = []

        profile_count = (
            self._probe.count_rows("external_customer_profile")
            if self._probe.table_exists("external_customer_profile")
            else 0
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Lead enrichment coverage",
                status="PASS" if profile_count == lead_count else "FAIL",
                reason=f"profiles={profile_count}, leads={lead_count}",
            )
        )

        for stage_name, _table, marker in EXTERNAL_STAGES[2:]:
            if marker in ("external_lead_analytics", "external_lead_intelligence", "behaviour_summary"):
                covered = int(
                    self._probe.scalar(
                        """
                        SELECT COUNT(DISTINCT lead_id) FROM lead_feature_store
                        WHERE source_module = :source_module
                        """,
                        {"source_module": marker},
                    )
                    or 0
                )
            else:
                covered = 0

            checks.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"{stage_name} coverage",
                    status="PASS" if covered == lead_count else "FAIL",
                    reason=f"leads_with_stage={covered}/{lead_count}",
                    details={"source_module": marker},
                )
            )

        analytics_ready = int(
            self._probe.scalar(
                "SELECT COUNT(*) FROM external_leads WHERE lead_status = 'ANALYTICS_READY'"
            )
            or 0
        )
        intelligence_ready = int(
            self._probe.scalar(
                "SELECT COUNT(*) FROM external_leads WHERE lead_status = 'INTELLIGENCE_VALIDATED'"
            )
            or 0
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Lead status ANALYTICS_READY",
                status="PASS" if analytics_ready == lead_count else "WARN",
                reason=f"analytics_ready={analytics_ready}/{lead_count}",
            )
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Lead status INTELLIGENCE_VALIDATED",
                status="PASS" if intelligence_ready == lead_count else "WARN",
                reason=f"intelligence_validated={intelligence_ready}/{lead_count}",
            )
        )

        feature_leads = int(
            self._probe.scalar(
                "SELECT COUNT(DISTINCT lead_id) FROM lead_feature_store"
            )
            or 0
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Lead Feature Store coverage",
                status="PASS" if feature_leads == lead_count else "FAIL",
                reason=f"leads_in_feature_store={feature_leads}/{lead_count}",
            )
        )

        return checks
