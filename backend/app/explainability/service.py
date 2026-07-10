"""Orchestration service for the Explainable AI layer."""

from __future__ import annotations

from uuid import UUID

from app.explainability.decision_summary import DecisionSummaryBuilder
from app.explainability.openai_service import OpenAIService
from app.explainability.repository import ExplainabilityRepository
from app.schemas.explainability import (
    ExplainabilityGenerateRequest,
    ExplainabilityReportResponse,
    ExplanationResponse,
)
from app.api.ui_adapters import adapt_explainability_report
from app.utils.exceptions import ExplainabilityReportNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _field(obj, name: str, default=None):
    """Safe read for DocumentEntity reports — optional MongoDB fields."""
    if obj is None:
        return default
    return getattr(obj, name, default)


class ExplainabilityService:
    """
    Enterprise Explainable AI service.

    Converts structured ML outputs into regulator-friendly explanations.
    Does not make lending decisions or alter predictions.
    """

    def __init__(
        self,
        repository: ExplainabilityRepository,
        decision_summary_builder: DecisionSummaryBuilder,
        openai_service: OpenAIService | None = None,
    ) -> None:
        self._repo = repository
        self._summary_builder = decision_summary_builder
        self._openai = openai_service or OpenAIService()

    def generate(self, request: ExplainabilityGenerateRequest) -> dict:
        if request.profile_id is not None:
            summary = self._summary_builder.build_by_profile_id(request.profile_id)
        elif request.customer_id is not None:
            summary = self._summary_builder.build_by_customer_id(request.customer_id)
        else:
            raise ValueError("Either profile_id or customer_id must be provided")

        summary_dict = summary.to_dict()
        explanation = self._openai.generate_explanation(summary_dict)

        report = self._repo.save(
            customer_id=summary.customer_id,
            profile_type=summary.profile_type,
            repayment_prediction=summary.repayment_capacity,
            recommended_product=summary.recommended_product,
            conversion_probability=summary.conversion_probability,
            reason_codes=explanation.get("reason_codes", summary.top_reason_codes),
            llm_summary=explanation.get("summary"),
            llm_response=explanation,
            profile_id=summary.profile_id,
        )

        logger.info(
            "Explainability report generated customer_id=%s profile_type=%s",
            summary.customer_id,
            summary.profile_type,
        )

        return adapt_explainability_report(
            self._to_response(report, summary, explanation).model_dump(mode="json")
        )

    def build_all(
        self, limit_internal: int | None = None, limit_external: int | None = None
    ) -> dict[str, int]:
        """Generate and persist explainability reports for all internal and external profiles."""
        internal_repo = self._summary_builder._internal_repo
        external_repo = self._summary_builder._external_repo

        succeeded = 0
        failed = 0

        internal_profiles = internal_repo.get_all_profiles()
        if limit_internal is not None:
            internal_profiles = internal_profiles[:limit_internal]

        for profile in internal_profiles:
            try:
                self.generate(ExplainabilityGenerateRequest(profile_id=profile.profile_id))
                succeeded += 1
            except Exception as exc:
                failed += 1
                logger.warning(
                    "Explainability failed internal profile_id=%s: %s",
                    profile.profile_id,
                    exc,
                )

        external_profiles = external_repo.get_all_profiles()
        if limit_external is not None:
            external_profiles = external_profiles[:limit_external]

        for profile in external_profiles:
            try:
                self.generate(ExplainabilityGenerateRequest(profile_id=profile.profile_id))
                succeeded += 1
            except Exception as exc:
                failed += 1
                logger.warning(
                    "Explainability failed external profile_id=%s: %s",
                    profile.profile_id,
                    exc,
                )

        return {
            "profiles_processed": succeeded + failed,
            "reports_succeeded": succeeded,
            "reports_failed": failed,
            "reports_in_db": self._repo.count_all(),
        }

    def get_latest(self, customer_id: UUID) -> dict:
        report = self._repo.get_latest_by_customer_id(customer_id)
        if report is None:
            raise ExplainabilityReportNotFoundError(customer_id)

        explanation = _field(report, "llm_response") or {}
        llm_summary = _field(report, "llm_summary")
        response = ExplainabilityReportResponse(
            report_id=_field(report, "report_id"),
            customer_id=_field(report, "customer_id"),
            profile_type=_field(report, "profile_type"),
            repayment_prediction=_field(report, "repayment_prediction"),
            recommended_product=_field(report, "recommended_product"),
            conversion_probability=(
                float(conv)
                if (conv := _field(report, "conversion_probability")) is not None
                else None
            ),
            reason_codes=_field(report, "reason_codes")
            if isinstance(_field(report, "reason_codes"), list)
            else [],
            created_at=_field(report, "created_at"),
            explanation=ExplanationResponse(
                summary=explanation.get("summary", llm_summary or ""),
                repayment_explanation=explanation.get("repayment_explanation", ""),
                product_explanation=explanation.get("product_explanation", ""),
                conversion_explanation=explanation.get("conversion_explanation", ""),
                confidence_summary=explanation.get("confidence_summary", ""),
                reason_codes=explanation.get("reason_codes", []),
            ),
            decision_summary=None,
        )
        return adapt_explainability_report(response.model_dump(mode="json"))

    def _to_response(self, report, summary, explanation: dict) -> ExplainabilityReportResponse:
        conv = _field(report, "conversion_probability")
        return ExplainabilityReportResponse(
            report_id=_field(report, "report_id"),
            customer_id=_field(report, "customer_id"),
            profile_type=_field(report, "profile_type"),
            repayment_prediction=_field(report, "repayment_prediction"),
            recommended_product=_field(report, "recommended_product"),
            conversion_probability=float(conv) if conv is not None else None,
            reason_codes=explanation.get("reason_codes", []),
            created_at=_field(report, "created_at"),
            explanation=ExplanationResponse(**explanation),
            decision_summary=summary.to_dict(),
        )
