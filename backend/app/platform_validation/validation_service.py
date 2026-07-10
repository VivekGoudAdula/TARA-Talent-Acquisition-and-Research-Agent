"""Orchestrates the full enterprise platform validation suite."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.db.mongo import MongoDatabase
from app.platform_validation.business_validator import BusinessValidator
from app.platform_validation.check_result import (
    CategorySummary,
    ValidationCheck,
    overall_percentage,
    summarize_category,
)
from app.platform_validation.consistency_validator import ConsistencyValidator
from app.platform_validation.data_quality_validator import DataQualityValidator
from app.platform_validation.database_validator import DatabaseValidator
from app.platform_validation.db_probe import DatabaseProbe
from app.platform_validation.e2e_validator import EndToEndValidator
from app.platform_validation.external_validator import ExternalIntelligenceValidator
from app.platform_validation.internal_validator import InternalIntelligenceValidator
from app.platform_validation.ml_validator import MLValidator
from app.platform_validation.report_generator import ReportGenerator
from app.schemas.platform_validation import (
    CategorySummaryResponse,
    SystemHealthResponse,
    ValidationCheckResponse,
    ValidationReportResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class PlatformValidationService:
    """Runs all validators and produces enterprise audit reports."""

    def __init__(self, db: MongoDatabase, report_dir: Path | None = None) -> None:
        self._db = db
        self._probe = DatabaseProbe(db)
        self._report_dir = report_dir or Path.cwd()
        self._last_report: ValidationReportResponse | None = None

    def run_full_validation(self, write_reports: bool = True) -> ValidationReportResponse:
        logger.info("Starting enterprise platform validation suite")

        all_checks: list[ValidationCheck] = []

        db_validators = [
            DatabaseValidator(self._probe),
            DataQualityValidator(self._probe),
            InternalIntelligenceValidator(self._probe),
            ExternalIntelligenceValidator(self._probe),
            MLValidator(self._probe),
            ConsistencyValidator(self._probe),
        ]
        for validator in db_validators:
            checks = validator.run()
            all_checks.extend(checks)
            logger.info(
                "Validator %s completed: %d checks",
                validator.CATEGORY,
                len(checks),
            )

        from app.platform_validation.api_validator import APIValidator, _get_test_client

        with _get_test_client() as client:
            for validator in (
                APIValidator(self._probe, client),
                BusinessValidator(self._probe, client),
                EndToEndValidator(self._probe, client),
            ):
                checks = validator.run()
                all_checks.extend(checks)
                logger.info(
                    "Validator %s completed: %d checks",
                    validator.CATEGORY,
                    len(checks),
                )

        categories = self._group_categories(all_checks)
        overall = overall_percentage(all_checks)
        generated_at = datetime.now(timezone.utc).isoformat()
        system_health = self._build_system_health(categories, all_checks)

        report_paths: dict[str, str] = {}
        if write_reports:
            generator = ReportGenerator(self._report_dir)
            report_paths = generator.write_all(
                generated_at,
                overall,
                system_health.model_dump(),
                categories,
                all_checks,
            )
            logger.info("Validation reports written to %s", self._report_dir)

        response = ValidationReportResponse(
            generated_at=generated_at,
            overall_health=overall,
            system_health=system_health,
            categories=[self._to_category_response(c) for c in categories],
            report_paths=report_paths,
        )
        self._last_report = response
        return response

    def get_health_summary(self, run_if_missing: bool = True) -> SystemHealthResponse:
        if self._last_report is None and run_if_missing:
            self.run_full_validation(write_reports=False)
        if self._last_report is None:
            return SystemHealthResponse(
                database="SKIP",
                internal="SKIP",
                external="SKIP",
                customer360="SKIP",
                feature_store="SKIP",
                behaviour_analytics="SKIP",
                ml="SKIP",
                repayment_model="SKIP",
                product_recommendation="SKIP",
                lead_conversion="SKIP",
                api="SKIP",
                data_integrity="SKIP",
                end_to_end_workflow="SKIP",
                overall_health="0%",
            )
        return self._last_report.system_health

    def _group_categories(self, checks: list[ValidationCheck]) -> list[CategorySummary]:
        by_category: dict[str, list[ValidationCheck]] = {}
        for check in checks:
            by_category.setdefault(check.category, []).append(check)
        return [summarize_category(cat, items) for cat, items in sorted(by_category.items())]

    def _build_system_health(
        self,
        categories: list[CategorySummary],
        all_checks: list[ValidationCheck],
    ) -> SystemHealthResponse:
        cat_map = {c.category: c.status for c in categories}

        def check_status(prefix: str, category: str | None = None) -> str:
            if category and category in cat_map:
                return cat_map[category]
            matched = [c for c in all_checks if c.name.startswith(prefix)]
            if not matched:
                return "SKIP"
            if any(c.status == "FAIL" for c in matched):
                return "FAIL"
            if all(c.status in ("PASS", "SKIP") for c in matched):
                return "PASS"
            return "WARN"

        repayment_checks = [
            c for c in all_checks if "Repayment" in c.name and c.category == "Machine Learning"
        ]
        conversion_checks = [
            c for c in all_checks if "Conversion" in c.name and c.category == "Machine Learning"
        ]
        product_checks = [
            c for c in all_checks if "Product Recommendation" in c.name
        ]

        def ml_substatus(subset: list[ValidationCheck]) -> str:
            if not subset:
                return "SKIP"
            if any(c.status == "FAIL" for c in subset):
                return "FAIL"
            return "PASS"

        customer360_checks = [c for c in all_checks if "Customer360" in c.name]
        feature_checks = [
            c for c in all_checks
            if "Feature Store" in c.name or "feature_store" in c.name.lower()
        ]
        behaviour_checks = [c for c in all_checks if "Behaviour" in c.name]

        return SystemHealthResponse(
            database=cat_map.get("Database", "SKIP"),
            internal=cat_map.get("Internal Intelligence", "SKIP"),
            external=cat_map.get("External Intelligence", "SKIP"),
            customer360=(
                "FAIL" if any(c.status == "FAIL" for c in customer360_checks)
                else "PASS" if customer360_checks else "SKIP"
            ),
            feature_store=(
                "FAIL" if any(c.status == "FAIL" for c in feature_checks)
                else "PASS" if feature_checks else "SKIP"
            ),
            behaviour_analytics=(
                "FAIL" if any(c.status == "FAIL" for c in behaviour_checks)
                else "PASS" if behaviour_checks else "SKIP"
            ),
            ml=cat_map.get("Machine Learning", "SKIP"),
            repayment_model=ml_substatus(repayment_checks),
            product_recommendation=ml_substatus(product_checks),
            lead_conversion=ml_substatus(conversion_checks),
            api=cat_map.get("API", "SKIP"),
            data_integrity=cat_map.get("Data Integrity", "SKIP"),
            end_to_end_workflow=cat_map.get("End to End Workflow", "SKIP"),
            overall_health=overall_percentage(all_checks),
        )

    @staticmethod
    def _to_category_response(cat: CategorySummary) -> CategorySummaryResponse:
        return CategorySummaryResponse(
            category=cat.category,
            status=cat.status,
            passed=cat.passed,
            failed=cat.failed,
            warned=cat.warned,
            skipped=cat.skipped,
            checks=[
                ValidationCheckResponse(
                    category=c.category,
                    name=c.name,
                    status=c.status,
                    reason=c.reason,
                    details=c.details,
                )
                for c in cat.checks
            ],
        )
