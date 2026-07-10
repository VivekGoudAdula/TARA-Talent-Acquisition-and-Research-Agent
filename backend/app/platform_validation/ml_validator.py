"""Machine Learning layer validation."""

from __future__ import annotations

import json
from pathlib import Path

from app.ml.conversion.training import (
    FEATURE_IMPORTANCE_PATH as CONVERSION_FI_PATH,
    METRICS_PATH as CONVERSION_METRICS_PATH,
    MODEL_PATH as CONVERSION_MODEL_PATH,
)
from app.ml.repayment.registry import (
    FEATURE_IMPORTANCE_PATH as REPAYMENT_FI_PATH,
    METRICS_PATH as REPAYMENT_METRICS_PATH,
    MODEL_PATH as REPAYMENT_MODEL_PATH,
)
from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe

VALID_TARGETS = {"Very High", "High", "Medium", "Low"}
CATALOG_PATH = (
    Path(__file__).resolve().parent.parent / "ml" / "product_recommendation" / "catalog.py"
)


class MLValidator:
    """Validates training dataset and ML model artifacts."""

    CATEGORY = "Machine Learning"

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        checks.extend(self._validate_training_dataset())
        checks.extend(self._validate_repayment_model())
        checks.extend(self._validate_conversion_model())
        checks.extend(self._validate_product_recommendation())
        return checks

    def _validate_training_dataset(self) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        if not self._probe.table_exists("training_dataset"):
            return [
                ValidationCheck(
                    category=self.CATEGORY,
                    name="Training dataset exists",
                    status="FAIL",
                    reason="training_dataset table missing",
                )
            ]

        total = self._probe.count_rows("training_dataset")
        internal = int(
            self._probe.scalar(
                "SELECT COUNT(*) FROM training_dataset WHERE profile_type = 'Internal'"
            )
            or 0
        )
        external = int(
            self._probe.scalar(
                "SELECT COUNT(*) FROM training_dataset WHERE profile_type = 'External'"
            )
            or 0
        )
        invalid_targets = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM training_dataset
                WHERE target_repayment_capacity NOT IN ('Very High', 'High', 'Medium', 'Low')
                """
            )
            or 0
        )
        dupes = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM (
                    SELECT profile_id, profile_type, COUNT(*) cnt
                    FROM training_dataset GROUP BY profile_id, profile_type
                    HAVING COUNT(*) > 1
                ) d
                """
            )
            or 0
        )
        null_features = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM training_dataset
                WHERE financial_health_score IS NULL
                  AND lead_quality_score IS NULL
                  AND cash_flow_score IS NULL
                """
            )
            or 0
        )

        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Training dataset populated",
                status="PASS" if total > 0 else "FAIL",
                reason=f"records={total} (internal={internal}, external={external})",
            )
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Training dataset has internal and external records",
                status="PASS" if internal > 0 and external > 0 else "FAIL",
                reason=f"internal={internal}, external={external}",
            )
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Training dataset target variable valid",
                status="PASS" if invalid_targets == 0 else "FAIL",
                reason=f"invalid_targets={invalid_targets}",
            )
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Training dataset no duplicate rows",
                status="PASS" if dupes == 0 else "FAIL",
                reason=f"duplicate_profile_groups={dupes}",
            )
        )
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name="Training dataset feature completeness",
                status="PASS" if null_features == 0 else "WARN",
                reason=f"rows_missing_all_core_scores={null_features}",
            )
        )
        return checks

    def _validate_repayment_model(self) -> list[ValidationCheck]:
        return self._validate_model_artifacts(
            model_name="Repayment Capacity Model",
            model_path=REPAYMENT_MODEL_PATH,
            metrics_path=REPAYMENT_METRICS_PATH,
            fi_path=REPAYMENT_FI_PATH,
        )

    def _validate_conversion_model(self) -> list[ValidationCheck]:
        return self._validate_model_artifacts(
            model_name="Lead Conversion Model",
            model_path=CONVERSION_MODEL_PATH,
            metrics_path=CONVERSION_METRICS_PATH,
            fi_path=CONVERSION_FI_PATH,
        )

    def _validate_model_artifacts(
        self,
        model_name: str,
        model_path: Path,
        metrics_path: Path,
        fi_path: Path,
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        model_ok = model_path.exists()
        checks.append(
            ValidationCheck(
                category=self.CATEGORY,
                name=f"{model_name} file exists",
                status="PASS" if model_ok else "FAIL",
                reason=str(model_path),
            )
        )

        for label, path in [("Metrics", metrics_path), ("Feature importance", fi_path)]:
            if not path.exists():
                checks.append(
                    ValidationCheck(
                        category=self.CATEGORY,
                        name=f"{model_name} {label.lower()} file",
                        status="FAIL",
                        reason=f"Missing: {path}",
                    )
                )
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                checks.append(
                    ValidationCheck(
                        category=self.CATEGORY,
                        name=f"{model_name} {label.lower()} valid JSON",
                        status="PASS" if isinstance(data, dict) and data else "FAIL",
                        reason=f"keys={len(data)}",
                    )
                )
            except json.JSONDecodeError as exc:
                checks.append(
                    ValidationCheck(
                        category=self.CATEGORY,
                        name=f"{model_name} {label.lower()} valid JSON",
                        status="FAIL",
                        reason=str(exc),
                    )
                )
        return checks

    def _validate_product_recommendation(self) -> list[ValidationCheck]:
        catalog_ok = CATALOG_PATH.exists()
        return [
            ValidationCheck(
                category=self.CATEGORY,
                name="Product Recommendation catalog module",
                status="PASS" if catalog_ok else "FAIL",
                reason=str(CATALOG_PATH),
            ),
            ValidationCheck(
                category=self.CATEGORY,
                name="Product Recommendation engine type",
                status="PASS",
                reason="Rule-based hybrid engine (no pickle artifact required)",
            ),
        ]
