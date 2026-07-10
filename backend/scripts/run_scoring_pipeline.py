#!/usr/bin/env python3
"""Run Scoring & Decisioning layer: intelligence → behaviour → ML → product-fit."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import get_database
from app.dependencies import (
    get_behaviour_summary_service,
    get_conversion_service,
    get_customer_query_repository,
    get_dataset_service,
    get_external_intelligence_service,
    get_external_lead_repository,
    get_external_profile_repository,
    get_feature_store_repository,
    get_fraud_screening_engine,
    get_income_confidence_engine,
    get_kyc_readiness_engine,
    get_lead_authenticity_engine,
    get_lead_feature_store_repository,
    get_ml_scoring_repository,
    get_product_recommendation_service,
    get_repayment_capacity_service,
    get_scoring_persistence_service,
    get_training_dataset_repository,
)
from app.repositories.customer360_repository import Customer360Repository
from app.utils.database import new_session


def _counts() -> dict[str, int]:
    db = get_database()
    return {
        "behaviour_summary_fs": db.feature_store.count_documents(
            {"source_module": "behaviour_summary"}
        ),
        "internal_health_scores": db.customer_360_profile.count_documents(
            {"financial_health_score": {"$exists": True, "$ne": None}}
        ),
        "external_health_scores": db.external_customer_profile.count_documents(
            {"financial_health_score": {"$exists": True, "$ne": None}}
        ),
        "training_dataset": db.training_dataset.count_documents({}),
        "intelligence_features": db.lead_feature_store.count_documents(
            {"source_module": "external_lead_intelligence"}
        ),
        "repayment_predictions": db.repayment_predictions.count_documents({}),
        "product_recommendations": db.product_recommendations.count_documents({}),
        "conversion_predictions": db.conversion_predictions.count_documents({}),
        "ml_model_runs": db.ml_model_runs.count_documents({}),
    }


def main() -> None:
    started = time.time()
    report: dict = {"steps": [], "counts_before": _counts()}
    print("BEFORE", report["counts_before"], flush=True)

    db = new_session()
    try:
        cqr = get_customer_query_repository(db)
        c360 = Customer360Repository(db)
        fs = get_feature_store_repository(db)
        leads = get_external_lead_repository(db)
        profiles = get_external_profile_repository(db)
        lead_fs = get_lead_feature_store_repository(db)
        training = get_training_dataset_repository(db)
        scoring_repo = get_ml_scoring_repository(db)

        print("\n=== External intelligence ===", flush=True)
        if _counts()["intelligence_features"] >= profiles.count_all():
            intel = {"skipped": True, "reason": "already validated"}
            print("skipped (already done)", flush=True)
        else:
            intel = get_external_intelligence_service(
                leads,
                profiles,
                lead_fs,
                get_lead_authenticity_engine(),
                get_income_confidence_engine(),
                get_fraud_screening_engine(),
                get_kyc_readiness_engine(),
            ).build_all()
            print(intel, flush=True)
        report["steps"].append({"external_intelligence": intel})

        print("\n=== Behaviour summary ===", flush=True)
        if _counts()["internal_health_scores"] >= c360.count_profiles():
            behaviour = {"skipped": True, "reason": "already built"}
            print("skipped (already done)", flush=True)
        else:
            behaviour = get_behaviour_summary_service(c360, profiles, fs, lead_fs, leads).build_all()
            print(behaviour, flush=True)
        report["steps"].append({"behaviour_summary": behaviour})

        print("\n=== ML dataset build ===", flush=True)
        if _counts()["training_dataset"] > 0:
            dataset = {"skipped": True, "records": _counts()["training_dataset"]}
            print(f"skipped ({dataset['records']} records already)", flush=True)
        else:
            dataset = get_dataset_service(c360, profiles, leads, fs, lead_fs, training).build_dataset()
            report["steps"].append({"ml_dataset": dataset.model_dump()})
            print(
                f"records={dataset.records_persisted} internal={dataset.internal_records} "
                f"external={dataset.external_records}",
                flush=True,
            )
            dataset = dataset.model_dump()
        if isinstance(dataset, dict) and dataset.get("skipped"):
            report["steps"].append({"ml_dataset": dataset})

        print("\n=== Repayment model train ===", flush=True)
        repayment = get_repayment_capacity_service(
            training, scoring_repo, c360, profiles
        )
        train_result = repayment.train()
        report["steps"].append({"repayment_train": train_result.model_dump()})
        print(
            f"best_model={train_result.best_model} records={train_result.records_used} "
            f"cv_f1={train_result.cv_scores.get(train_result.best_model)}",
            flush=True,
        )

        print("\n=== Persist all ML scoring outputs ===", flush=True)
        product_svc = get_product_recommendation_service(
            c360, profiles, leads, fs, lead_fs, repayment, scoring_repo
        )
        conversion = get_conversion_service(leads, profiles, lead_fs, scoring_repo)

        print("\n=== Conversion model train ===", flush=True)
        try:
            conv_train = conversion.train()
            report["steps"].append({"conversion_train": conv_train.model_dump()})
            print(f"best_model={conv_train.best_model} records={conv_train.records_used}", flush=True)
        except Exception as exc:
            print(f"conversion train skipped/failed: {exc}", flush=True)
            report["steps"].append({"conversion_train": {"error": str(exc)}})

        persistence = get_scoring_persistence_service(
            c360, profiles, leads, repayment, product_svc, conversion, scoring_repo
        ).build_all(top_n=5)
        report["steps"].append({"scoring_persistence": persistence})
        print(persistence, flush=True)

    finally:
        db.close()

    report["counts_after"] = _counts()
    report["elapsed_seconds"] = round(time.time() - started, 1)
    out = PROJECT_ROOT / "scoring_pipeline_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nDONE in {report['elapsed_seconds']}s")
    print("AFTER", report["counts_after"])
    print("Report:", out)


if __name__ == "__main__":
    main()
