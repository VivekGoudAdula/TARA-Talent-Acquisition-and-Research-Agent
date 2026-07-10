#!/usr/bin/env python3
"""
Batch-2 External Pipeline + Full Combined Retrain:
  Step 1 -> Enrich / process analytics for remaining 500 external leads (total: 1000).
  Step 2 -> Re-train conversion model on ALL 1000 external profiles.
  Step 3 -> Score all customers (internal + external) with updated models.
"""

from __future__ import annotations

import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import MongoDatabase


def timed(label, fn):
    t0 = time.perf_counter()
    r = fn()
    ms = int((time.perf_counter() - t0) * 1000)
    print(f"  [{label}] done in {ms}ms -> {r}")
    return r


def main() -> None:
    db = MongoDatabase()

    ext_leads_total = db._db["external_leads"].count_documents({})
    ext_profiles_before = db._db["external_customer_profile"].count_documents({})
    print(f"External leads in DB      : {ext_leads_total}")
    print(f"External profiles before  : {ext_profiles_before}")
    print(f"Still need processing     : {ext_leads_total - ext_profiles_before}")

    from app.repositories.external_lead_repository import ExternalLeadRepository
    from app.repositories.external_profile_repository import ExternalProfileRepository
    from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
    from app.repositories.customer360_repository import Customer360Repository
    from app.repositories.feature_store_repository import FeatureStoreRepository
    from app.repositories.training_dataset_repository import TrainingDatasetRepository
    from app.repositories.ml_scoring_repository import MLScoringRepository
    from app.external.external_enrichment_service import ExternalEnrichmentService
    from app.external.external_analytics_service import ExternalAnalyticsService
    from app.external.external_intelligence_service import ExternalIntelligenceService
    from app.behaviour_summary.behaviour_summary_service import BehaviourSummaryService
    from app.ml.dataset_builder.dataset_service import DatasetService
    from app.ml.repayment.service import RepaymentCapacityService
    from app.ml.conversion.service import ConversionService
    from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
    from app.ml.scoring_persistence_service import ScoringPersistenceService
    from app.learning.repository import LearningRepository

    ext_lead_repo = ExternalLeadRepository(db)
    ext_profile_repo = ExternalProfileRepository(db)
    lead_feature_repo = LeadFeatureStoreRepository(db)
    customer360_repo = Customer360Repository(db)
    feature_repo = FeatureStoreRepository(db)
    training_repo = TrainingDatasetRepository(db)
    scoring_repo = MLScoringRepository(db)

    # -- Step 1: Enrich all 1000 external leads (idempotent upsert) -------------
    print("\n[Step 1] Enriching ALL 1000 external leads ...")
    enrich_svc = ExternalEnrichmentService(ext_lead_repo, ext_profile_repo)
    timed("external_enrich", lambda: enrich_svc.enrich_all(limit=1000))

    print("\n[Step 1b] Running analytics for ALL 1000 external leads ...")
    analytics_svc = ExternalAnalyticsService(ext_lead_repo, ext_profile_repo, lead_feature_repo)
    timed("external_analytics", lambda: analytics_svc.build_all(limit=1000))

    print("\n[Step 1c] Running intelligence for ALL 1000 external leads ...")
    intel_svc = ExternalIntelligenceService(ext_lead_repo, ext_profile_repo, lead_feature_repo)
    timed("external_intelligence", lambda: intel_svc.build_all(limit=1000))

    ext_profiles_after = db._db["external_customer_profile"].count_documents({})
    print(f"\n  External profiles after enrichment: {ext_profiles_after}")

    # -- Step 2: Behaviour summary (external only) -------------------------------
    print("\n[Step 2] Building behaviour summaries for ALL 1000 external leads ...")
    beh_svc = BehaviourSummaryService(
        customer360_repo, ext_profile_repo, feature_repo,
        lead_feature_repo, ext_lead_repo,
    )
    timed("behaviour_summary", lambda: beh_svc.build_all(limit_internal=0, limit_external=1000))

    # -- Step 3: ML dataset + train all models on combined 1000+1000 -------------
    print("\n[Step 3] Building ML dataset (all internal + all external) ...")
    ds_svc = DatasetService(
        customer360_repo, ext_profile_repo, ext_lead_repo,
        feature_repo, lead_feature_repo, training_repo,
    )
    timed("ml_dataset", lambda: ds_svc.build_dataset(limit_internal=1000, limit_external=1000))

    print("\n[Step 3b] Training repayment model on full dataset ...")
    repayment_svc = RepaymentCapacityService(
        training_repo,
        scoring_repository=scoring_repo,
        customer360_repository=customer360_repo,
        external_profile_repository=ext_profile_repo,
    )
    timed("repayment_train", lambda: repayment_svc.train())

    print("\n[Step 3c] Training conversion model on full external dataset ...")
    labels = LearningRepository(db).outcome_labels_by_lead_id()
    conversion_svc = ConversionService(
        ext_lead_repo, ext_profile_repo, lead_feature_repo,
        scoring_repository=scoring_repo,
    )
    if len(labels) >= 3:
        timed("conversion_train", lambda: conversion_svc.train(label_source="blended", outcome_labels=labels))
    else:
        timed("conversion_train", lambda: conversion_svc.train(label_source="synthetic"))

    # -- Step 4: Score ALL internal + external customers ------------------------
    print("\n[Step 4] Persisting scores for ALL customers ...")
    product_svc = ProductRecommendationService(
        customer360_repo, ext_profile_repo, ext_lead_repo,
        feature_repo, lead_feature_repo, repayment_svc,
        scoring_repository=scoring_repo,
    )
    score_svc = ScoringPersistenceService(
        customer360_repo, ext_profile_repo, ext_lead_repo,
        repayment_svc, product_svc, conversion_svc, scoring_repo,
    )
    timed("scoring_persist", lambda: score_svc.build_all(limit_internal=1000, limit_external=1000))

    print("\n[OK] Batch-2 external pipeline + full combined retrain complete!")
    print(f"   External profiles  : {db._db['external_customer_profile'].count_documents({})}")
    print(f"   Internal profiles  : {db._db['customer_360_profile'].count_documents({})}")
    print(f"   ML scores in DB    : {db._db['ml_scoring'].count_documents({})}")


if __name__ == "__main__":
    main()
