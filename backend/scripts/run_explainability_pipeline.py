#!/usr/bin/env python3
"""Generate Explainable AI reports for all profiles using OpenAI or Azure OpenAI."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.config import get_settings
from app.db.mongo import get_database
from app.dependencies import (
    get_conversion_service,
    get_customer360_repository,
    get_decision_summary_builder,
    get_explainability_repository,
    get_external_lead_repository,
    get_external_profile_repository,
    get_feature_store_repository,
    get_lead_feature_store_repository,
    get_ml_scoring_repository,
    get_product_recommendation_service,
    get_repayment_capacity_service,
    get_training_dataset_repository,
)
from app.explainability.openai_service import OpenAIService
from app.explainability.service import ExplainabilityService
from app.utils.database import new_session


def main() -> None:
    settings = get_settings()
    llm = OpenAIService(settings)
    started = time.time()
    db_before = get_database().explainability_reports.count_documents({})

    print("LLM enabled:", settings.explainability_use_llm)
    print("LLM provider:", llm.provider or "fallback (not configured)")
    if llm.provider == "openai":
        print("Model:", settings.openai_model)
    elif llm.provider == "azure":
        print("Deployment:", settings.azure_gpt_deployment)
    print(f"Reports before: {db_before}")

    db = new_session()
    try:
        c360 = get_customer360_repository(db)
        profiles = get_external_profile_repository(db)
        leads = get_external_lead_repository(db)
        fs = get_feature_store_repository(db)
        lead_fs = get_lead_feature_store_repository(db)
        training = get_training_dataset_repository(db)
        scoring = get_ml_scoring_repository(db)
        repayment = get_repayment_capacity_service(training, scoring, c360, profiles)
        product = get_product_recommendation_service(
            c360, profiles, leads, fs, lead_fs, repayment, scoring
        )
        conversion = get_conversion_service(leads, profiles, lead_fs, scoring)
        summary_builder = get_decision_summary_builder(
            c360, profiles, leads, fs, lead_fs, repayment, product, conversion
        )
        service = ExplainabilityService(
            get_explainability_repository(db),
            summary_builder,
            OpenAIService(),
        )
        result = service.build_all()
    finally:
        db.close()

    elapsed = round(time.time() - started, 1)
    db_after = get_database().explainability_reports.count_documents({})
    report = {"result": result, "elapsed_seconds": elapsed, "reports_after": db_after}
    out = PROJECT_ROOT / "explainability_pipeline_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\nDONE in {elapsed}s")
    print(result)
    print("Reports after:", db_after)
    print("Report file:", out)


if __name__ == "__main__":
    main()
