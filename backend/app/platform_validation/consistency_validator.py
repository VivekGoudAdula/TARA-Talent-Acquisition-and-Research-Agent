"""Cross-entity database consistency validation."""

from __future__ import annotations

from app.platform_validation.check_result import ValidationCheck
from app.platform_validation.db_probe import DatabaseProbe


class ConsistencyValidator:
    """Validates cross-table consistency across intelligence layers."""

    CATEGORY = "Database Consistency"

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        checks.append(self._customer360_has_feature_store())
        checks.append(self._external_profile_has_lead_features())
        checks.append(self._training_dataset_profile_references())
        checks.append(self._product_recommendation_product_validity())
        return checks

    def _customer360_has_feature_store(self) -> ValidationCheck:
        if not self._probe.table_exists("customer_360_profile"):
            return ValidationCheck(
                category=self.CATEGORY,
                name="Customer360 has Feature Store",
                status="SKIP",
                reason="customer_360_profile missing",
            )

        missing = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM customer_360_profile p
                LEFT JOIN (
                    SELECT DISTINCT customer_id FROM feature_store
                ) f ON p.customer_id = f.customer_id
                WHERE f.customer_id IS NULL
                """
            )
            or 0
        )
        return ValidationCheck(
            category=self.CATEGORY,
            name="Every Customer360 has Feature Store",
            status="PASS" if missing == 0 else "FAIL",
            reason=f"profiles_without_features={missing}",
        )

    def _external_profile_has_lead_features(self) -> ValidationCheck:
        if not self._probe.table_exists("external_customer_profile"):
            return ValidationCheck(
                category=self.CATEGORY,
                name="External profile has Lead Feature Store",
                status="SKIP",
                reason="external_customer_profile missing",
            )

        missing = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM external_customer_profile p
                LEFT JOIN (
                    SELECT DISTINCT lead_id FROM lead_feature_store
                ) f ON p.lead_id = f.lead_id
                WHERE f.lead_id IS NULL
                """
            )
            or 0
        )
        return ValidationCheck(
            category=self.CATEGORY,
            name="Every External Profile has Lead Feature Store",
            status="PASS" if missing == 0 else "FAIL",
            reason=f"profiles_without_lead_features={missing}",
        )

    def _training_dataset_profile_references(self) -> ValidationCheck:
        if not self._probe.table_exists("training_dataset"):
            return ValidationCheck(
                category=self.CATEGORY,
                name="Training dataset profile references",
                status="SKIP",
                reason="training_dataset missing",
            )

        orphan_internal = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM training_dataset t
                LEFT JOIN customer_360_profile p ON t.profile_id = p.profile_id
                WHERE t.profile_type = 'Internal' AND p.profile_id IS NULL
                """
            )
            or 0
        )
        orphan_external = int(
            self._probe.scalar(
                """
                SELECT COUNT(*) FROM training_dataset t
                LEFT JOIN external_customer_profile p ON t.profile_id = p.profile_id
                WHERE t.profile_type = 'External' AND p.profile_id IS NULL
                """
            )
            or 0
        )
        total_orphans = orphan_internal + orphan_external
        return ValidationCheck(
            category=self.CATEGORY,
            name="Training dataset references valid profiles",
            status="PASS" if total_orphans == 0 else "FAIL",
            reason=(
                f"orphan_internal={orphan_internal}, orphan_external={orphan_external}"
            ),
        )

    def _product_recommendation_product_validity(self) -> ValidationCheck:
        from app.ml.product_recommendation.catalog import PRODUCT_CATALOG

        catalog_names = {p.name for p in PRODUCT_CATALOG}
        return ValidationCheck(
            category=self.CATEGORY,
            name="Product catalog references valid products",
            status="PASS" if len(catalog_names) >= 1 else "FAIL",
            reason=f"catalog_products={len(catalog_names)}",
            details={"products": sorted(catalog_names)},
        )
