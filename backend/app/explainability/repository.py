"""Repository for explainability_reports collection."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.models.explainability_report import ExplainabilityReport
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ExplainabilityRepository:
    """Data access layer for explainability_reports."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def save(
        self,
        *,
        customer_id: UUID,
        profile_type: str,
        repayment_prediction: str | None,
        recommended_product: str | None,
        conversion_probability: float | None,
        reason_codes: list[str],
        llm_summary: str | None,
        llm_response: dict | None,
        profile_id: UUID | None = None,
        commit: bool = True,
    ) -> ExplainabilityReport:
        existing = self._db.explainability_reports.find_one({"customer_id": str(customer_id)})
        report_id = UUID(existing["report_id"]) if existing and existing.get("report_id") else uuid4()
        created_at = existing.get("created_at", datetime.utcnow()) if existing else datetime.utcnow()

        report = ExplainabilityReport(
            report_id=report_id,
            customer_id=customer_id,
            profile_type=profile_type,
            repayment_prediction=repayment_prediction,
            recommended_product=recommended_product,
            conversion_probability=conversion_probability,
            reason_codes=reason_codes,
            llm_summary=llm_summary,
            llm_response=llm_response,
            created_at=created_at,
        )
        doc = report.to_doc()
        if profile_id is not None:
            doc["profile_id"] = str(profile_id)
        doc["updated_at"] = datetime.utcnow()
        self._db.explainability_reports.replace_one(
            {"customer_id": str(customer_id)}, doc, upsert=True
        )
        logger.info(
            "Saved explainability report report_id=%s customer_id=%s",
            report.report_id,
            customer_id,
        )
        return report

    def get_latest_by_customer_id(self, customer_id: UUID) -> ExplainabilityReport | None:
        doc = self._db.explainability_reports.find_one({"customer_id": str(customer_id)})
        return ExplainabilityReport.from_doc(doc)

    def count_all(self) -> int:
        return self._db.explainability_reports.count_documents({})
