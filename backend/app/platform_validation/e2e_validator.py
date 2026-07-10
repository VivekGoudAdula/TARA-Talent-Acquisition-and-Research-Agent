"""End-to-end workflow validation (read-only inspection)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe


def _get_test_client() -> TestClient:
    from app.main import app

    return TestClient(app)


class EndToEndValidator:
    """Validates complete internal and external workflows without mutating data."""

    CATEGORY = "End to End Workflow"

    def __init__(self, probe: DatabaseProbe, client: TestClient | None = None) -> None:
        self._probe = probe
        self._client = client

    def run(self) -> list[ValidationCheck]:
        if self._client is not None:
            return self._run_with_client(self._client)
        with _get_test_client() as client:
            return self._run_with_client(client)

    def _run_with_client(self, client: TestClient) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        checks.extend(self._validate_internal_workflow(client))
        checks.extend(self._validate_external_workflow(client))
        return checks

    def _validate_internal_workflow(self, client: TestClient) -> list[ValidationCheck]:
        customer_id = self._probe.sample_customer_id()
        if customer_id is None:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Internal customer workflow",
                    status="SKIP",
                    reason="No customers in database",
                )
            ]

        profile_exists = int(
            self._probe.scalar(
                "SELECT COUNT(*) FROM customer_360_profile WHERE customer_id = :cid",
                {"cid": str(customer_id)},
            )
            or 0
        )
        feature_exists = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM feature_store
                WHERE customer_id = :cid AND source_module = 'internal_pipeline'
                  AND feature_name = 'pipeline_completed'
                """,
                {"cid": str(customer_id)},
            )
            or 0
        )
        training_exists = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM training_dataset t
                JOIN customer_360_profile p ON t.profile_id = p.profile_id
                WHERE p.customer_id = :cid AND t.profile_type = 'Internal'
                """,
                {"cid": str(customer_id)},
            )
            or 0
        )

        stages = {
            "Customer360": profile_exists > 0,
            "Feature Store": feature_exists > 0,
            "Training Dataset": training_exists > 0,
        }

        repayment_ok = False
        recommend_ok = False
        profile_id = self._probe.scalar(
            "SELECT profile_id FROM customer_360_profile WHERE customer_id = :cid",
            {"cid": str(customer_id)},
        )

        if profile_id and training_exists > 0:
            training_profile = self._probe.scalar(
                """
                SELECT profile_id FROM training_dataset t
                JOIN customer_360_profile p ON t.profile_id = p.profile_id
                WHERE p.customer_id = :cid AND t.profile_type = 'Internal'
                LIMIT 1
                """,
                {"cid": str(customer_id)},
            )
            repay = client.post(
                "/api/ml/repayment/predict",
                json={
                    "profile_type": "Internal",
                    "profile_id": str(training_profile),
                },
            )
            repayment_ok = repay.status_code == 200

            rec = client.post(
                "/api/ml/products/recommend",
                json={"profile_id": str(profile_id), "top_n": 3},
            )
            recommend_ok = rec.status_code == 200

        stages["Repayment Prediction"] = repayment_ok
        stages["Product Recommendation"] = recommend_ok

        failed = [name for name, ok in stages.items() if not ok]
        return [
            ValidationCheck(
                category=self.CATEGORY,
                name="Internal customer end-to-end workflow",
                status="PASS" if not failed else "FAIL",
                reason=f"stages_ok={list(stages.keys())}, failed={failed}",
                details=stages,
            )
        ]

    def _validate_external_workflow(self, client: TestClient) -> list[ValidationCheck]:
        lead_id = self._probe.sample_lead_id()
        if lead_id is None:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="External lead workflow",
                    status="SKIP",
                    reason="No external leads in database",
                )
            ]

        stages = {
            "Import": int(
                self._probe.scalar(
                    "SELECT COUNT(*) FROM external_leads WHERE lead_id = :lid",
                    {"lid": str(lead_id)},
                )
                or 0
            )
            > 0,
            "Enrichment": int(
                self._probe.scalar(
                    "SELECT COUNT(*) FROM external_customer_profile WHERE lead_id = :lid",
                    {"lid": str(lead_id)},
                )
                or 0
            )
            > 0,
            "Lead Analytics": int(
                self._probe.scalar(
                    """
                    SELECT COUNT(*) FROM lead_feature_store
                    WHERE lead_id = :lid AND source_module = 'external_lead_analytics'
                    """,
                    {"lid": str(lead_id)},
                )
                or 0
            )
            > 0,
            "Lead Feature Store": int(
                self._probe.scalar(
                    "SELECT COUNT(DISTINCT feature_name) FROM lead_feature_store WHERE lead_id = :lid",
                    {"lid": str(lead_id)},
                )
                or 0
            )
            > 0,
        }

        training_exists = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM training_dataset t
                JOIN external_customer_profile p ON t.profile_id = p.profile_id
                WHERE p.lead_id = :lid AND t.profile_type = 'External'
                """,
                {"lid": str(lead_id)},
            )
            or 0
        )
        stages["Training Dataset"] = training_exists > 0

        conversion_ok = False
        conv = client.post(
            "/api/ml/conversion/predict",
            json={"lead_id": str(lead_id)},
        )
        conversion_ok = conv.status_code == 200
        stages["Lead Conversion"] = conversion_ok

        failed = [name for name, ok in stages.items() if not ok]
        return [
            ValidationCheck(
                category=self.CATEGORY,
                name="External lead end-to-end workflow",
                status="PASS" if not failed else "FAIL",
                reason=f"stages_ok={list(stages.keys())}, failed={failed}",
                details=stages,
            )
        ]
