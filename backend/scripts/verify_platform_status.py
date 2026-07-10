#!/usr/bin/env python3
"""Quick end-to-end platform status verification."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.config import get_settings
from app.db.mongo import get_database
from app.dependencies import get_platform_validation_service
from app.utils.database import new_session


def main() -> None:
    settings = get_settings()
    db = get_database()

    print("=" * 60)
    print("IDBI Innovate 2026 — Platform Status (through Explainable AI)")
    print("=" * 60)
    print(f"Database: {settings.mongodb_db_name}")
    print(f"Subset: {settings.expected_customer_count} internal + {settings.expected_lead_count} external")
    print()

    layers = {
        "Layer 1 — Data Sources": [
            ("customers", settings.expected_customer_count),
            ("transactions", None),
            ("external_leads", settings.expected_lead_count),
        ],
        "Layer 2 — Intelligence": [
            ("customer_360_profile", settings.expected_customer_count),
            ("feature_store", None),
            ("external_customer_profile", settings.expected_lead_count),
            ("lead_feature_store", None),
        ],
        "Layer 3 — Scoring & Decisioning": [
            ("training_dataset", 100),
            ("repayment_predictions", 100),
            ("product_recommendations", 100),
            ("conversion_predictions", settings.expected_lead_count),
            ("ml_model_runs", 1),
        ],
        "Layer 4 — Explainable AI": [
            ("explainability_reports", 100),
        ],
    }

    all_ok = True
    for layer, items in layers.items():
        print(layer)
        for coll, expected in items:
            count = db[coll].count_documents({})
            if expected is not None:
                ok = count >= expected
                status = "OK" if ok else "LOW"
                if not ok:
                    all_ok = False
                print(f"  {coll}: {count} (expected {expected}) [{status}]")
            else:
                print(f"  {coll}: {count}")
        print()

    expl = db["explainability_reports"]
    with_llm = expl.count_documents({"llm_summary": {"$exists": True, "$nin": [None, ""]}})
    with_reasons = expl.count_documents({"reason_codes.0": {"$exists": True}})
    print("Explainable AI quality:")
    print(f"  Reports with LLM summary: {with_llm}/100")
    print(f"  Reports with reason codes: {with_reasons}/100")
    print()

    artifacts = [
        PROJECT_ROOT / "app/ml/models/best_repayment_model.pkl",
        PROJECT_ROOT / "app/ml/models/best_conversion_model.pkl",
    ]
    print("Model artifacts:")
    for path in artifacts:
        print(f"  {path.name}: {'present' if path.exists() else 'MISSING'}")
    print()

    session = new_session()
    try:
        svc = get_platform_validation_service(session)
        report = svc.run_full_validation()
    finally:
        session.close()

    passed = sum(1 for c in report.checks if c.passed)
    print(f"Platform validation: {passed}/{len(report.checks)} checks passed — {report.overall_status}")
    failed = [c.name for c in report.checks if not c.passed]
    if failed:
        print("Failed checks:")
        for name in failed:
            print(f"  - {name}")

    print()
    print("OVERALL:", "COMPLETE" if all_ok and with_llm == 100 else "REVIEW NEEDED")


if __name__ == "__main__":
    main()
