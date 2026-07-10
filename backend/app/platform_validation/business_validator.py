"""Business rule validation for ML outputs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe


def _get_test_client() -> TestClient:
    from app.main import app

    return TestClient(app)

VALID_REPAYMENT = {"Very High", "High", "Medium", "Low"}


class BusinessValidator:
    """Validates business contracts on prediction and recommendation outputs."""

    CATEGORY = "Business Validation"

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
        internal_id = self._probe.sample_training_profile_id("Internal")
        external_id = self._probe.sample_training_profile_id("External")
        profile_id = self._probe.sample_profile_id()
        external_profile_id = self._probe.sample_external_profile_id()
        lead_id = self._probe.sample_lead_id()

        checks.extend(self._validate_repayment(client, internal_id, "Internal"))
        checks.extend(self._validate_repayment(client, external_id, "External"))
        checks.extend(self._validate_recommendation(client, profile_id, "Internal"))
        checks.extend(self._validate_recommendation(client, external_profile_id, "External"))
        checks.extend(self._validate_conversion(client, lead_id))

        return [c for c in checks if c is not None]

    def _validate_repayment(
        self,
        client: TestClient,
        profile_id,
        label: str,
    ) -> list[ValidationCheck | None]:
        if profile_id is None:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Repayment prediction ({label})",
                    status="SKIP",
                    reason="No training dataset profile available",
                )
            ]

        response = client.post(
            "/api/ml/repayment/predict",
            json={"profile_type": label, "profile_id": str(profile_id)},
        )
        if response.status_code != 200:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Repayment prediction ({label})",
                    status="FAIL",
                    reason=f"HTTP {response.status_code}",
                )
            ]

        body = response.json()
        capacity = body.get("repayment_capacity")
        confidence = body.get("confidence")
        ok = (
            capacity in VALID_REPAYMENT
            and confidence is not None
            and 0 <= float(confidence) <= 1
        )
        return [
            ValidationCheck(
                category=self.CATEGORY,
                name=f"Repayment prediction ({label})",
                status="PASS" if ok else "FAIL",
                reason=f"capacity={capacity}, confidence={confidence}",
            )
        ]

    def _validate_recommendation(
        self,
        client: TestClient,
        profile_id,
        label: str,
    ) -> list[ValidationCheck | None]:
        if profile_id is None:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Product recommendation ({label})",
                    status="SKIP",
                    reason="No profile available",
                )
            ]

        response = client.post(
            "/api/ml/products/recommend",
            json={"profile_id": str(profile_id), "top_n": 3},
        )
        if response.status_code != 200:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Product recommendation ({label})",
                    status="FAIL",
                    reason=f"HTTP {response.status_code}",
                )
            ]

        body = response.json()
        recommendations = body.get("recommendations", [])
        if not recommendations:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name=f"Product recommendation ({label})",
                    status="FAIL",
                    reason="No recommendations returned",
                )
            ]

        first = recommendations[0]
        ok = (
            first.get("product_name")
            and first.get("probability") is not None
            and first.get("eligible") is not None
            and body.get("repayment_capacity") in VALID_REPAYMENT
        )
        return [
            ValidationCheck(
                category=self.CATEGORY,
                name=f"Product recommendation ({label})",
                status="PASS" if ok else "FAIL",
                reason=(
                    f"product={first.get('product_name')}, "
                    f"probability={first.get('probability')}, "
                    f"eligible={first.get('eligible')}"
                ),
            )
        ]

    def _validate_conversion(self, client: TestClient, lead_id) -> list[ValidationCheck | None]:
        if lead_id is None:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Conversion prediction",
                    status="SKIP",
                    reason="No lead available",
                )
            ]

        response = client.post(
            "/api/ml/conversion/predict",
            json={"lead_id": str(lead_id)},
        )
        if response.status_code != 200:
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Conversion prediction",
                    status="FAIL",
                    reason=f"HTTP {response.status_code}",
                )
            ]

        body = response.json()
        probability = body.get("conversion_probability")
        ok = probability is not None and 0 <= float(probability) <= 100
        return [
            ValidationCheck(
                category=self.CATEGORY,
                name="Conversion prediction",
                status="PASS" if ok else "FAIL",
                reason=f"conversion_probability={probability}",
            )
        ]
