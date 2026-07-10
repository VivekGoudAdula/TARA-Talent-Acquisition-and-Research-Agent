"""API endpoint validation (read-only where possible)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe


def _get_test_client() -> TestClient:
    from app.main import app

    return TestClient(app)


class APIValidator:
    """Validates API availability and response contracts."""

    CATEGORY = "API"

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
        customer_id = self._probe.sample_customer_id()
        profile_id = self._probe.sample_profile_id()
        lead_id = self._probe.sample_lead_id()
        external_profile_id = self._probe.sample_external_profile_id()
        internal_training_id = self._probe.sample_training_profile_id("Internal")
        external_training_id = self._probe.sample_training_profile_id("External")

        checks.append(self._get(client, "/health", "Health"))
        checks.append(self._get(client, "/api/internal/status", "Internal pipeline status"))

        if customer_id:
            checks.extend(
                [
                    self._get(client, f"/api/customer360/{customer_id}", "Customer360 GET"),
                    self._get(
                        client,
                        f"/api/customer360/transaction/{customer_id}",
                        "Transaction Analytics GET",
                    ),
                    self._get(
                        client,
                        f"/api/customer360/behaviour/{customer_id}",
                        "Behaviour Analytics GET",
                    ),
                    self._get(
                        client,
                        f"/api/customer360/relationship/{customer_id}",
                        "Relationship Analytics GET",
                    ),
                    self._get(
                        client,
                        f"/api/customer360/channel/{customer_id}",
                        "Digital Channel Analytics GET",
                    ),
                    self._get(
                        client,
                        f"/api/customer360/customer-health/{customer_id}",
                        "Customer Health GET",
                    ),
                ]
            )

        if profile_id:
            checks.append(
                self._get(client, f"/api/behaviour/{profile_id}", "Behaviour Summary GET")
            )

        checks.extend(
            [
                self._get(client, "/api/external/leads", "External leads list"),
                self._get(client, "/api/ml/dataset", "ML dataset GET"),
                self._get(client, "/api/ml/dataset/stats", "ML dataset stats"),
                self._get(client, "/api/ml/repayment/model", "Repayment model info"),
                self._get(client, "/api/ml/conversion/model", "Conversion model info"),
                self._get(client, "/api/ml/products/catalog", "Product catalog"),
            ]
        )

        if lead_id:
            checks.extend(
                [
                    self._get(client, f"/api/external/profile/{lead_id}", "External profile GET"),
                    self._get(
                        client,
                        f"/api/external/analytics/{lead_id}",
                        "External analytics GET",
                    ),
                    self._get(
                        client,
                        f"/api/external/intelligence/{lead_id}",
                        "External intelligence GET",
                    ),
                ]
            )

        if internal_training_id:
            checks.append(
                self._post_json(
                    client,
                    "/api/ml/repayment/predict",
                    {
                        "profile_type": "Internal",
                        "profile_id": str(internal_training_id),
                    },
                    "Repayment predict (Internal)",
                )
            )

        if external_training_id:
            checks.append(
                self._post_json(
                    client,
                    "/api/ml/repayment/predict",
                    {
                        "profile_type": "External",
                        "profile_id": str(external_training_id),
                    },
                    "Repayment predict (External)",
                )
            )

        if profile_id:
            checks.append(
                self._post_json(
                    client,
                    "/api/ml/products/recommend",
                    {"profile_id": str(profile_id), "top_n": 3},
                    "Product recommend (Internal)",
                )
            )

        if external_profile_id:
            checks.append(
                self._post_json(
                    client,
                    "/api/ml/products/recommend",
                    {"profile_id": str(external_profile_id), "top_n": 3},
                    "Product recommend (External)",
                )
            )

        if lead_id:
            checks.append(
                self._post_json(
                    client,
                    "/api/ml/conversion/predict",
                    {"lead_id": str(lead_id)},
                    "Conversion predict",
                )
            )

        if customer_id:
            checks.append(
                self._get(
                    client,
                    f"/api/explain/{customer_id}",
                    "Explainability GET",
                    allow_404=True,
                )
            )

        checks.extend(self._validate_mutating_routes_registered(client))
        return checks

    def _get(
        self,
        client: TestClient,
        path: str,
        name: str,
        allow_404: bool = False,
    ) -> ValidationCheck:
        response = client.get(path)
        if response.status_code == 200:
            return ValidationCheck(
                category=self.CATEGORY,
                name=name,
                status="PASS",
                reason=f"HTTP {response.status_code}",
            )
        if allow_404 and response.status_code == 404:
            return ValidationCheck(
                category=self.CATEGORY,
                name=name,
                status="WARN",
                reason="HTTP 404 — resource not yet generated",
            )
        return ValidationCheck(
            category=self.CATEGORY,
            name=name,
            status="FAIL",
            reason=f"HTTP {response.status_code}: {response.text[:200]}",
        )

    def _post_json(
        self,
        client: TestClient,
        path: str,
        payload: dict[str, Any],
        name: str,
    ) -> ValidationCheck:
        response = client.post(path, json=payload)
        if response.status_code == 200:
            return ValidationCheck(
                category=self.CATEGORY,
                name=name,
                status="PASS",
                reason=f"HTTP {response.status_code}",
            )
        return ValidationCheck(
            category=self.CATEGORY,
            name=name,
            status="FAIL",
            reason=f"HTTP {response.status_code}: {response.text[:200]}",
        )

    def _validate_mutating_routes_registered(self, client: TestClient) -> list[ValidationCheck]:
        """Confirm write endpoints exist without invoking them (no synthetic data)."""
        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})
        expected_posts = [
            ("/api/customer360/build/{customer_id}", "Customer360 build"),
            ("/api/customer360/financial/{customer_id}", "Financial analytics"),
            ("/api/external/import", "External import"),
            ("/api/external/enrich", "External enrichment"),
            ("/api/ml/dataset/build", "ML dataset build"),
            ("/api/ml/repayment/train", "Repayment train"),
            ("/api/ml/conversion/train", "Conversion train"),
            ("/api/internal/build-all", "Internal pipeline build-all"),
            ("/api/explain/generate", "Explainability generate"),
        ]
        checks: list[ValidationCheck] = []
        for path, name in expected_posts:
            registered = path in paths and "post" in paths[path]
            checks.append(
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Route registered: {name}",
                    status="PASS" if registered else "FAIL",
                    reason="POST endpoint present in OpenAPI" if registered else "Missing from OpenAPI",
                )
            )
        return checks
