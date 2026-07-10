"""Train ML models (if dataset exists) and seed explainability reports for internal customers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.mongo import get_database
from app.explainability.decision_summary import DecisionSummaryBuilder
from app.explainability.openai_service import OpenAIService
from app.explainability.repository import ExplainabilityRepository
from app.explainability.service import ExplainabilityService
from app.ml.conversion.service import ConversionService
from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
from app.ml.repayment.service import RepaymentCapacityService
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.repositories.ml_scoring_repository import MLScoringRepository
from app.repositories.training_dataset_repository import TrainingDatasetRepository


def main() -> None:
    db = get_database()
    scoring = MLScoringRepository(db)
    training_repo = TrainingDatasetRepository(db)

    records = training_repo.get_all()
    print(f"training_dataset records: {len(records)}")

    if len(records) >= 10:
        repayment_svc = RepaymentCapacityService(
            training_repo,
            scoring_repository=scoring,
            customer360_repository=Customer360Repository(db),
            external_profile_repository=ExternalProfileRepository(db),
        )
        try:
            r = repayment_svc.train()
            print(f"repayment trained: {r.best_model} records={r.records_used}")
        except Exception as exc:
            print(f"repayment train skipped: {exc}")
    else:
        print("repayment train skipped: need >= 10 training records (run pipeline ml_dataset first)")

    conversion_svc = ConversionService(
        ExternalLeadRepository(db),
        ExternalProfileRepository(db),
        LeadFeatureStoreRepository(db),
        scoring_repository=scoring,
    )
    try:
        c = conversion_svc.train(label_source="synthetic")
        print(f"conversion trained: {c.best_model} records={c.records_used}")
    except Exception as exc:
        print(f"conversion train skipped: {exc}")

    repayment_svc = RepaymentCapacityService(
        training_repo,
        scoring_repository=scoring,
        customer360_repository=Customer360Repository(db),
        external_profile_repository=ExternalProfileRepository(db),
    )
    product_svc = ProductRecommendationService(
        Customer360Repository(db),
        ExternalProfileRepository(db),
        ExternalLeadRepository(db),
        FeatureStoreRepository(db),
        LeadFeatureStoreRepository(db),
        repayment_svc,
        scoring_repository=scoring,
    )
    summary_builder = DecisionSummaryBuilder(
        Customer360Repository(db),
        ExternalProfileRepository(db),
        ExternalLeadRepository(db),
        FeatureStoreRepository(db),
        LeadFeatureStoreRepository(db),
        repayment_svc,
        product_svc,
        conversion_svc,
    )
    explain_svc = ExplainabilityService(
        ExplainabilityRepository(db),
        summary_builder,
        OpenAIService(),
    )
    result = explain_svc.build_all(limit_internal=50, limit_external=0)
    print(f"explainability: {result}")


if __name__ == "__main__":
    main()
