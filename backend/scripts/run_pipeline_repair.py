"""Execute internal pipeline build-all and platform validation; write repair report."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db_env import load_db_env

load_db_env()

from fastapi.testclient import TestClient

from app.main import app
from app.utils.database import new_session


def table_counts() -> dict[str, int]:
    db = new_session()
    try:
        return {
            "customers": db.customers.count_documents({}),
            "customer_360_profile": db.customer_360_profile.count_documents({}),
            "feature_store_distinct": len(db.feature_store.distinct("customer_id")),
            "pipeline_completed": db.feature_store.count_documents(
                {
                    "source_module": "internal_pipeline",
                    "feature_name": "pipeline_completed",
                }
            ),
        }
    finally:
        db.close()


def main() -> None:
    before_counts = table_counts()
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_cause": (
            "Batch pipeline used a single shared database session across all customers. "
            "When any customer failed mid-pipeline, subsequent customers could be blocked. "
            "Additionally, build-all had not been fully executed for all customers."
        ),
        "files_fixed": [
            "app/internal_pipeline/pipeline_service.py",
            "app/internal_pipeline/orchestrator.py",
            "app/dependencies.py",
            "app/repositories/customer360_repository.py",
            "app/schemas/internal_pipeline.py",
            "tests/test_internal_pipeline.py",
        ],
        "methods_changed": [
            "InternalPipelineService._run_customer_isolated",
            "InternalPipelineService._run_batch",
            "InternalPipelineOrchestrator._rollback_session",
            "create_internal_pipeline_orchestrator",
            "Customer360Repository.update_profile",
        ],
        "validation_before": None,
        "validation_after": None,
        "counts_before": before_counts,
        "counts_after": None,
        "build_all": None,
    }

    with TestClient(app) as client:
        health_before = client.get("/api/system/health")
        if health_before.status_code == 200:
            report["validation_before"] = health_before.json()

        print("Running POST /api/internal/build-all ...")
        build_resp = client.post("/api/internal/build-all", timeout=3600)
        report["build_all"] = {
            "status_code": build_resp.status_code,
            "body": build_resp.json() if build_resp.status_code == 200 else build_resp.text[:2000],
        }
        print("Build-all status:", build_resp.status_code)

        print("Running POST /api/system/validate ...")
        validate_resp = client.post("/api/system/validate", timeout=600)
        if validate_resp.status_code == 200:
            body = validate_resp.json()
            report["validation_after"] = body.get("system_health")
            report["overall_health"] = body.get("overall_health")
        else:
            report["validation_after"] = {"error": validate_resp.text[:1000]}

    after_counts = table_counts()
    report["counts_after"] = after_counts
    report["customers_processed"] = report["build_all"]["body"].get("completed") if report["build_all"] else None
    report["customers_failed"] = report["build_all"]["body"].get("failed") if report["build_all"] else None
    report["failed_customer_ids"] = (
        report["build_all"]["body"].get("failed_customer_ids") if report["build_all"] else []
    )

    out = PROJECT_ROOT / "pipeline_repair_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Counts before:", before_counts)
    print("Counts after:", after_counts)
    print("Overall health:", report.get("overall_health"))
    print("Report written to", out)


if __name__ == "__main__":
    main()
