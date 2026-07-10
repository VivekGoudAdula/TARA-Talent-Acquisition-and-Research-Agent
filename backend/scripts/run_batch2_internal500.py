#!/usr/bin/env python3
"""
Batch-2 Internal Pipeline:
  Step 1 → Build 360 profiles for the remaining ~500 internal customers (those without a profile).
  Step 2 → Re-train ML models using ALL 1000 internal profiles (behaviour + ml_dataset + train + score).
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import MongoDatabase


def main() -> None:
    db = MongoDatabase()

    from app.repositories.customer_query_repository import CustomerQueryRepository
    from app.repositories.customer360_repository import Customer360Repository
    from app.repositories.feature_store_repository import FeatureStoreRepository
    from app.dependencies import create_internal_pipeline_orchestrator
    from app.internal_pipeline.validator import PipelineValidator
    from app.internal_pipeline.progress_tracker import PipelineProgressTracker
    from app.internal_pipeline.pipeline_service import InternalPipelineService

    customer_query_repo = CustomerQueryRepository(db)
    customer360_repo = Customer360Repository(db)
    feature_repo = FeatureStoreRepository(db)

    # ── Step 1: Identify customers still missing a 360 profile ─────────────────
    all_ids: list[UUID] = customer_query_repo.get_all_customer_ids()
    profiled_ids: set[str] = {
        doc["customer_id"]
        for doc in db._db["customer_360_profile"].find({}, {"customer_id": 1})
    }
    missing_ids = [cid for cid in all_ids if str(cid) not in profiled_ids]

    print(f"Total internal customers   : {len(all_ids)}")
    print(f"Already have 360 profile   : {len(profiled_ids)}")
    print(f"Still need profile (batch2): {len(missing_ids)}")

    if missing_ids:
        validator = PipelineValidator(customer_query_repo, customer360_repo, feature_repo)
        progress_tracker = PipelineProgressTracker()
        svc = InternalPipelineService(
            customer_query_repo,
            customer360_repo,
            feature_repo,
            create_internal_pipeline_orchestrator,
            validator,
            progress_tracker,
            db,
        )
        print(f"\n[Step 1] Building 360 profiles for {len(missing_ids)} remaining customers …")
        summary = svc._run_batch(missing_ids)
        print(f"  completed={summary.completed}  failed={summary.failed}  profiles_in_db={summary.profiles}")
    else:
        print("\n[Step 1] All 1000 internal customers already have profiles. Skipping build.")

    # ── Step 2: Re-train ML on ALL 1000 internal profiles ──────────────────────
    # We run the subset pipeline with target="internal" and skip internal_build_all
    # by using a dedicated training-only flow (behaviour → ml_dataset → train → score → explain)
    print("\n[Step 2] Running ML training on ALL 1000 internal profiles …")

    from app.behaviour_summary.behaviour_summary_service import BehaviourSummaryService
    from app.repositories.external_profile_repository import ExternalProfileRepository
    from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
    from app.repositories.external_lead_repository import ExternalLeadRepository
    from app.repositories.training_dataset_repository import TrainingDatasetRepository
    from app.repositories.ml_scoring_repository import MLScoringRepository
    from app.ml.dataset_builder.dataset_service import DatasetService
    from app.ml.repayment.service import RepaymentCapacityService
    from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
    from app.ml.scoring_persistence_service import ScoringPersistenceService

    import time

    def timed(label, fn):
        t0 = time.perf_counter()
        r = fn()
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"  [{label}] done in {ms}ms -> {r}")
        return r

    ext_profile_repo = ExternalProfileRepository(db)
    ext_lead_repo = ExternalLeadRepository(db)
    lead_feature_repo = LeadFeatureStoreRepository(db)
    training_repo = TrainingDatasetRepository(db)
    scoring_repo = MLScoringRepository(db)

    # Behaviour summary — internal only (limit_external=0)
    beh_svc = BehaviourSummaryService(
        customer360_repo, ext_profile_repo, feature_repo,
        lead_feature_repo, ext_lead_repo,
    )
    # timed("behaviour_summary", lambda: beh_svc.build_all(limit_internal=1000, limit_external=0))

    # ML dataset — internal only
    ds_svc = DatasetService(
        customer360_repo, ext_profile_repo, ext_lead_repo,
        feature_repo, lead_feature_repo, training_repo,
    )
    timed("ml_dataset", lambda: ds_svc.build_dataset(limit_internal=1000, limit_external=0))

    # Repayment model training
    repayment_svc = RepaymentCapacityService(
        training_repo,
        scoring_repository=scoring_repo,
        customer360_repository=customer360_repo,
        external_profile_repository=ext_profile_repo,
    )
    timed("repayment_train", lambda: repayment_svc.train())

    # Score and persist — internal only
    product_svc = ProductRecommendationService(
        customer360_repo, ext_profile_repo, ext_lead_repo,
        feature_repo, lead_feature_repo, repayment_svc,
        scoring_repository=scoring_repo,
    )
    score_svc = ScoringPersistenceService(
        customer360_repo, ext_profile_repo, ext_lead_repo,
        repayment_svc, product_svc, None, scoring_repo,
    )
    timed("scoring_persist", lambda: score_svc.build_all(limit_internal=1000, limit_external=0))

    print("\n[OK] Batch-2 internal pipeline complete!")
    print(f"   Profiles in DB: {db._db['customer_360_profile'].count_documents({})}")
    print(f"   ML scores in DB: {db._db['ml_scoring'].count_documents({})}")


if __name__ == "__main__":
    main()
