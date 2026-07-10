#!/usr/bin/env python3
"""Run full pre-Explainable-AI pipeline: load → intelligence → ML → validate."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import get_database
from app.dependencies import (
    create_internal_pipeline_orchestrator,
    get_behaviour_summary_service,
    get_customer_query_repository,
    get_dataset_service,
    get_external_analytics_service,
    get_external_enrichment_service,
    get_external_intelligence_service,
    get_external_lead_repository,
    get_external_profile_repository,
    get_feature_store_repository,
    get_financial_capacity_analytics,
    get_fraud_screening_engine,
    get_income_confidence_engine,
    get_kyc_readiness_engine,
    get_lead_authenticity_engine,
    get_lead_behaviour_analytics,
    get_lead_enrichment_engine,
    get_lead_feature_store_repository,
    get_lead_quality_analytics,
    get_pipeline_progress_tracker,
    get_pipeline_validator,
    get_product_recommendation_service,
    get_repayment_capacity_service,
    get_training_dataset_repository,
)
from app.external.external_import_service import ExternalImportService
from app.internal.banking_import_service import BankingImportService
from app.internal_pipeline.pipeline_service import InternalPipelineService
from app.platform_validation.validation_service import PlatformValidationService
from app.repositories.banking_import_repository import BankingImportRepository
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.product_recommendation import ProductRecommendRequest
from app.utils.database import new_session


def _counts() -> dict[str, int]:
    db = get_database()
    names = [
        "customers",
        "transactions",
        "digital_activity",
        "external_leads",
        "external_customer_profile",
        "customer_360_profile",
        "feature_store",
        "lead_feature_store",
        "training_dataset",
    ]
    out: dict[str, int] = {}
    for name in names:
        out[name] = db[name].count_documents({}) if name in db.list_collection_names() else 0
    if "feature_store" in db.list_collection_names():
        out["pipeline_completed"] = db.feature_store.count_documents(
            {
                "source_module": "internal_pipeline",
                "feature_name": "pipeline_completed",
            }
        )
    return out


def _step(label: str) -> None:
    print(f"\n{'=' * 60}\nSTEP: {label}\n{'=' * 60}", flush=True)


def main() -> None:
    started = time.time()
    report: dict = {"steps": [], "counts_before": _counts()}

    skip_load = os.getenv("SKIP_EXCEL_LOAD", "").lower() in ("1", "true", "yes")
    from app.config import get_settings

    settings = get_settings()
    if skip_load:
        db_check = get_database()
        actual_customers = db_check.customers.count_documents({})
        expected = settings.expected_customer_count
        if actual_customers != expected:
            print(
                f"WARNING: SKIP_EXCEL_LOAD is set but customers={actual_customers} "
                f"!= EXPECTED_CUSTOMER_COUNT={expected}. "
                "Unset SKIP_EXCEL_LOAD and reload Excel to avoid Customer not found errors.",
                flush=True,
            )

    if skip_load:
        print("Skipping Excel load (SKIP_EXCEL_LOAD is set)", flush=True)
        report["steps"].append({"load_banking": "skipped", "load_external": "skipped"})
    else:
        _step("Load Excel -> MongoDB")
        session = new_session()
        try:
            banking = BankingImportService(BankingImportRepository(session))
            load_result = banking.import_from_excel()
            ext = ExternalImportService(ExternalLeadRepository(session)).import_from_excel()
            report["steps"].append({"load_banking": load_result, "load_external": ext})
            print("Counts after load:", _counts(), flush=True)
        finally:
            session.close()

    db = new_session()
    try:
        cqr = get_customer_query_repository(db)
        c360 = Customer360Repository(db)
        fs = FeatureStoreRepository(db)
        leads = get_external_lead_repository(db)
        profiles = get_external_profile_repository(db)
        lead_fs = get_lead_feature_store_repository(db)
        training = get_training_dataset_repository(db)

        _step("Internal build-all (Profile Analysis)")
        pipeline = InternalPipelineService(
            cqr,
            c360,
            fs,
            create_internal_pipeline_orchestrator,
            get_pipeline_validator(cqr, c360, fs),
            get_pipeline_progress_tracker(),
            db,
        )
        internal_summary = pipeline.build_all()
        report["steps"].append(
            {
                "internal_build_all": {
                    "completed": internal_summary.completed,
                    "failed": internal_summary.failed,
                    "success_rate": internal_summary.success_rate,
                }
            }
        )
        print(
            f"Internal: completed={internal_summary.completed} failed={internal_summary.failed} "
            f"rate={internal_summary.success_rate}",
            flush=True,
        )
        print("Counts after internal:", _counts(), flush=True)

        _step("External enrich")
        enrich_result = get_external_enrichment_service(
            leads, profiles, get_lead_enrichment_engine()
        ).enrich_all()
        report["steps"].append({"external_enrich": enrich_result})
        print(enrich_result, flush=True)

        _step("External analytics build-all")
        analytics_result = get_external_analytics_service(
            leads,
            profiles,
            lead_fs,
            get_lead_behaviour_analytics(),
            get_financial_capacity_analytics(),
            get_lead_quality_analytics(),
        ).build_all()
        report["steps"].append({"external_analytics": analytics_result})
        print(analytics_result, flush=True)

        _step("External intelligence build-all")
        intel_result = get_external_intelligence_service(
            leads,
            profiles,
            lead_fs,
            get_lead_authenticity_engine(),
            get_income_confidence_engine(),
            get_fraud_screening_engine(),
            get_kyc_readiness_engine(),
        ).build_all()
        report["steps"].append({"external_intelligence": intel_result})
        print(intel_result, flush=True)

        _step("Behaviour summary build-all")
        behaviour_result = get_behaviour_summary_service(c360, profiles, fs, lead_fs, leads).build_all()
        report["steps"].append({"behaviour_summary": behaviour_result})
        print(behaviour_result, flush=True)

        _step("ML dataset build")
        dataset_result = get_dataset_service(c360, profiles, leads, fs, lead_fs, training).build_dataset()
        report["steps"].append({"ml_dataset": dataset_result.model_dump()})
        print(
            f"dataset records={dataset_result.records_persisted} "
            f"internal={dataset_result.internal_records} external={dataset_result.external_records}",
            flush=True,
        )

        _step("Repayment model train")
        repayment = get_repayment_capacity_service(training)
        train_result = repayment.train()
        report["steps"].append({"repayment_train": train_result.model_dump()})
        print(f"repayment best_model={train_result.best_model} records={train_result.records_used}", flush=True)

        _step("Product recommendation smoke test")
        customer_id = cqr.get_all_customer_ids()[0]
        profile = c360.get_profile_by_customer_id(customer_id)
        if profile is None:
            raise RuntimeError(f"No Customer360 profile for customer {customer_id}")
        rec = get_product_recommendation_service(c360, profiles, leads, fs, lead_fs, repayment).recommend(
            ProductRecommendRequest(profile_id=profile.profile_id, top_n=3)
        )
        top = rec.recommendations[0] if rec.recommendations else None
        report["steps"].append(
            {
                "product_recommend_smoke": {
                    "profile_id": str(profile.profile_id),
                    "top_product": top.product_name if top else None,
                    "confidence_score": top.confidence_score if top else None,
                }
            }
        )
        print(
            f"top_product={top.product_name if top else None} "
            f"confidence={top.confidence_score if top else None}",
            flush=True,
        )

    finally:
        db.close()

    _step("Platform validation")
    val_db = new_session()
    try:
        val_report = PlatformValidationService(val_db, report_dir=PROJECT_ROOT).run_full_validation(
            write_reports=True
        )
        report["overall_health"] = val_report.overall_health
        report["categories"] = [c.model_dump() for c in val_report.categories]
        for cat in val_report.categories:
            print(f"  [{cat.status}] {cat.category}: pass={cat.passed} fail={cat.failed}", flush=True)
    finally:
        val_db.close()

    report["counts_after"] = _counts()
    report["elapsed_seconds"] = round(time.time() - started, 1)
    out = PROJECT_ROOT / "pre_xai_pipeline_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nDONE in {report['elapsed_seconds']}s | health={report.get('overall_health')}")
    print("Report:", out)
    print("Final counts:", report["counts_after"])


if __name__ == "__main__":
    main()
