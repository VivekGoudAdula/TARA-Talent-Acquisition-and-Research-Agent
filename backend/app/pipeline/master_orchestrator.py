"""Master orchestrator — Layers 1→3 (+ explainability) in one run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.pipeline.progress import live_pipeline_progress, subset_step_names
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineStepResult:
    step: str
    status: str
    detail: str | None = None
    duration_ms: int = 0


@dataclass
class PipelineRunResult:
    run_id: str
    pipeline_type: str
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[PipelineStepResult] = field(default_factory=list)
    success: bool = False

    def to_doc(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "pipeline_type": self.pipeline_type,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "success": self.success,
            "steps": [
                {
                    "step": s.step,
                    "status": s.status,
                    "detail": s.detail,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
        }


class MasterPipelineOrchestrator:
    """Runs intelligence → scoring → explainability without external CBS APIs."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self.limit_internal: int | None = None
        self.limit_external: int | None = None
        self.pipeline_target: str = "both"

    def run_external_pipeline(self, *, train_models: bool = True) -> PipelineRunResult:
        run = PipelineRunResult(
            run_id=str(uuid4()),
            pipeline_type="external",
            started_at=datetime.utcnow(),
        )
        try:
            self._step(run, "external_enrich", self._run_external_enrich)
            self._step(run, "external_analytics", self._run_external_analytics)
            self._step(run, "external_intelligence", self._run_external_intelligence)
            self._step(run, "behaviour_summary", self._run_behaviour_summary)
            if train_models:
                self._step(run, "ml_dataset", self._run_ml_dataset)
                self._step(run, "repayment_train", self._run_repayment_train)
                self._step(run, "conversion_train", self._run_conversion_train)
                self._step(run, "scoring_persist", self._run_scoring_persist)
            self._step(run, "explainability", self._run_explainability)
            run.success = all(s.status == "ok" for s in run.steps)
        except Exception as exc:
            logger.exception("External pipeline failed")
            run.steps.append(PipelineStepResult(step="pipeline", status="error", detail=str(exc)))
            run.success = False
        run.completed_at = datetime.utcnow()
        self._db.pipeline_runs.insert_one(run.to_doc())
        return run

    def run_internal_pipeline(self, *, train_models: bool = True) -> PipelineRunResult:
        run = PipelineRunResult(
            run_id=str(uuid4()),
            pipeline_type="internal",
            started_at=datetime.utcnow(),
        )
        try:
            self._step(run, "internal_build_all", self._run_internal_build_all)
            self._step(run, "behaviour_summary", self._run_behaviour_summary)
            if train_models:
                self._step(run, "ml_dataset", self._run_ml_dataset)
                self._step(run, "repayment_train", self._run_repayment_train)
                self._step(run, "conversion_train", self._run_conversion_train)
                self._step(run, "scoring_persist", self._run_scoring_persist)
            self._step(run, "explainability", self._run_explainability)
            run.success = all(s.status == "ok" for s in run.steps)
        except Exception as exc:
            logger.exception("Internal pipeline failed")
            run.steps.append(PipelineStepResult(step="pipeline", status="error", detail=str(exc)))
            run.success = False
        run.completed_at = datetime.utcnow()
        self._db.pipeline_runs.insert_one(run.to_doc())
        return run

    def run_full_demo_pipeline(self) -> PipelineRunResult:
        """External + internal scoring for demo datasets."""
        ext = self.run_external_pipeline()
        internal = self.run_internal_pipeline(train_models=False)
        merged = PipelineRunResult(
            run_id=str(uuid4()),
            pipeline_type="full_demo",
            started_at=ext.started_at,
            completed_at=datetime.utcnow(),
            steps=ext.steps + internal.steps,
            success=ext.success and internal.success,
        )
        self._db.pipeline_runs.insert_one(merged.to_doc())
        return merged

    def run_subset_pipeline(
        self,
        *,
        target: str = "both",
        limit_internal: int = 5,
        limit_external: int = 5,
        train_models: bool = True,
    ) -> PipelineRunResult:
        run = PipelineRunResult(
            run_id=str(uuid4()),
            pipeline_type=f"subset_{target}",
            started_at=datetime.utcnow(),
        )
        self.limit_internal = limit_internal
        self.limit_external = limit_external
        self.pipeline_target = target
        step_names = subset_step_names(target=target, train_models=train_models)
        live_pipeline_progress.begin(run_id=run.run_id, pipeline_type=run.pipeline_type, step_names=step_names)

        try:
            # 1. External intelligence steps
            if target in ("external", "both"):
                self._step(run, "external_enrich", self._run_external_enrich)
                self._step(run, "external_analytics", self._run_external_analytics)
                self._step(run, "external_intelligence", self._run_external_intelligence)
            
            # 2. Internal builder step
            if target in ("internal", "both"):
                self._step(run, "internal_build_all", self._run_internal_build_all)
            
            # 3. Behaviour summary (always runs)
            self._step(run, "behaviour_summary", self._run_behaviour_summary)
            
            # 4. Train models & scoring
            if train_models:
                self._step(run, "ml_dataset", self._run_ml_dataset)
                self._step(run, "repayment_train", self._run_repayment_train)
                if target in ("external", "both"):
                    self._step(run, "conversion_train", self._run_conversion_train)
                self._step(run, "scoring_persist", self._run_scoring_persist)
            
            # 5. Explainability
            self._step(run, "explainability", self._run_explainability)
            run.success = all(s.status == "ok" for s in run.steps)
        except Exception as exc:
            logger.exception("Subset pipeline failed")
            run.steps.append(PipelineStepResult(step="pipeline", status="error", detail=str(exc)))
            run.success = False
        run.completed_at = datetime.utcnow()
        self._db.pipeline_runs.insert_one(run.to_doc())
        live_pipeline_progress.finish(success=run.success)
        return run

    def _step(self, run: PipelineRunResult, name: str, fn) -> None:
        import time

        live_pipeline_progress.start_step(name)
        t0 = time.perf_counter()
        try:
            detail = fn()
            ms = int((time.perf_counter() - t0) * 1000)
            run.steps.append(
                PipelineStepResult(step=name, status="ok", detail=str(detail)[:500], duration_ms=ms)
            )
            live_pipeline_progress.complete_step(name, status="ok", detail=str(detail)[:500], duration_ms=ms)
        except Exception as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            run.steps.append(
                PipelineStepResult(step=name, status="error", detail=str(exc), duration_ms=ms)
            )
            live_pipeline_progress.complete_step(name, status="error", detail=str(exc), duration_ms=ms)
            raise

    def _run_external_enrich(self) -> str:
        from app.external.external_enrichment_service import ExternalEnrichmentService
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.external_profile_repository import ExternalProfileRepository

        svc = ExternalEnrichmentService(
            ExternalLeadRepository(self._db),
            ExternalProfileRepository(self._db),
        )
        r = svc.enrich_all(limit=self.limit_external)
        return f"enriched={r['leads_enriched']}"

    def _run_external_analytics(self) -> str:
        from app.external.external_analytics_service import ExternalAnalyticsService
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository

        svc = ExternalAnalyticsService(
            ExternalLeadRepository(self._db),
            ExternalProfileRepository(self._db),
            LeadFeatureStoreRepository(self._db),
        )
        r = svc.build_all(limit=self.limit_external)
        return f"analytics={r}"

    def _run_external_intelligence(self) -> str:
        from app.external.external_intelligence_service import ExternalIntelligenceService
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository

        svc = ExternalIntelligenceService(
            ExternalLeadRepository(self._db),
            ExternalProfileRepository(self._db),
            LeadFeatureStoreRepository(self._db),
        )
        r = svc.build_all(limit=self.limit_external)
        return f"intelligence={r}"

    def _scoped_limits(self) -> tuple[int | None, int | None]:
        """Only include internal/external rows that match the selected pipeline target."""
        target = (self.pipeline_target or "both").lower()
        internal = self.limit_internal if target in ("internal", "both") else 0
        external = self.limit_external if target in ("external", "both") else 0
        return internal, external

    def _run_behaviour_summary(self) -> str:
        from app.behaviour_summary.behaviour_summary_service import BehaviourSummaryService
        from app.repositories.customer360_repository import Customer360Repository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.feature_store_repository import FeatureStoreRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
        from app.repositories.external_lead_repository import ExternalLeadRepository

        svc = BehaviourSummaryService(
            Customer360Repository(self._db),
            ExternalProfileRepository(self._db),
            FeatureStoreRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            ExternalLeadRepository(self._db),
        )
        r = svc.build_all(
            limit_internal=self._scoped_limits()[0],
            limit_external=self._scoped_limits()[1],
        )
        return f"behaviour={r}"

    def _run_ml_dataset(self) -> str:
        from app.ml.dataset_builder.dataset_service import DatasetService
        from app.repositories.customer360_repository import Customer360Repository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.feature_store_repository import FeatureStoreRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
        from app.repositories.training_dataset_repository import TrainingDatasetRepository

        svc = DatasetService(
            Customer360Repository(self._db),
            ExternalProfileRepository(self._db),
            ExternalLeadRepository(self._db),
            FeatureStoreRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            TrainingDatasetRepository(self._db),
        )
        lim_int, lim_ext = self._scoped_limits()
        r = svc.build_dataset(limit_internal=lim_int, limit_external=lim_ext)
        return f"records={r.records_persisted}"

    def _run_repayment_train(self) -> str:
        from app.ml.repayment.service import RepaymentCapacityService
        from app.repositories.training_dataset_repository import TrainingDatasetRepository
        from app.repositories.ml_scoring_repository import MLScoringRepository
        from app.repositories.customer360_repository import Customer360Repository
        from app.repositories.external_profile_repository import ExternalProfileRepository

        svc = RepaymentCapacityService(
            TrainingDatasetRepository(self._db),
            scoring_repository=MLScoringRepository(self._db),
            customer360_repository=Customer360Repository(self._db),
            external_profile_repository=ExternalProfileRepository(self._db),
        )
        r = svc.train()
        return f"best={r.best_model}"

    def _run_conversion_train(self) -> str:
        from app.ml.conversion.service import ConversionService
        from app.learning.repository import LearningRepository
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
        from app.repositories.ml_scoring_repository import MLScoringRepository

        labels = LearningRepository(self._db).outcome_labels_by_lead_id()
        svc = ConversionService(
            ExternalLeadRepository(self._db),
            ExternalProfileRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            scoring_repository=MLScoringRepository(self._db),
        )
        if len(labels) >= 3:
            r = svc.train(label_source="blended", outcome_labels=labels)
        else:
            r = svc.train(label_source="synthetic")
        return f"best={r.best_model}"

    def _run_scoring_persist(self) -> str:
        from app.repositories.customer360_repository import Customer360Repository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.feature_store_repository import FeatureStoreRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
        from app.repositories.ml_scoring_repository import MLScoringRepository
        from app.repositories.training_dataset_repository import TrainingDatasetRepository
        from app.ml.repayment.service import RepaymentCapacityService
        from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
        from app.ml.conversion.service import ConversionService
        from app.ml.scoring_persistence_service import ScoringPersistenceService

        repayment_svc = RepaymentCapacityService(
            TrainingDatasetRepository(self._db),
            scoring_repository=MLScoringRepository(self._db),
            customer360_repository=Customer360Repository(self._db),
            external_profile_repository=ExternalProfileRepository(self._db),
        )
        product_svc = ProductRecommendationService(
            Customer360Repository(self._db),
            ExternalProfileRepository(self._db),
            ExternalLeadRepository(self._db),
            FeatureStoreRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            repayment_svc,
            scoring_repository=MLScoringRepository(self._db),
        )
        conversion_svc = ConversionService(
            ExternalLeadRepository(self._db),
            ExternalProfileRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            scoring_repository=MLScoringRepository(self._db),
        )
        svc = ScoringPersistenceService(
            Customer360Repository(self._db),
            ExternalProfileRepository(self._db),
            ExternalLeadRepository(self._db),
            repayment_svc,
            product_svc,
            conversion_svc,
            MLScoringRepository(self._db),
        )
        r = svc.build_all(
            limit_internal=self._scoped_limits()[0],
            limit_external=self._scoped_limits()[1],
        )
        return f"scored={r}"

    def _run_explainability(self) -> str:
        from app.explainability.repository import ExplainabilityRepository
        from app.explainability.decision_summary import DecisionSummaryBuilder
        from app.explainability.openai_service import OpenAIService
        from app.explainability.service import ExplainabilityService
        from app.repositories.customer360_repository import Customer360Repository
        from app.repositories.external_profile_repository import ExternalProfileRepository
        from app.repositories.external_lead_repository import ExternalLeadRepository
        from app.repositories.feature_store_repository import FeatureStoreRepository
        from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
        from app.repositories.training_dataset_repository import TrainingDatasetRepository
        from app.repositories.ml_scoring_repository import MLScoringRepository
        from app.ml.repayment.service import RepaymentCapacityService
        from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
        from app.ml.conversion.service import ConversionService

        repayment_svc = RepaymentCapacityService(
            TrainingDatasetRepository(self._db),
            scoring_repository=MLScoringRepository(self._db),
            customer360_repository=Customer360Repository(self._db),
            external_profile_repository=ExternalProfileRepository(self._db),
        )
        product_svc = ProductRecommendationService(
            Customer360Repository(self._db),
            ExternalProfileRepository(self._db),
            ExternalLeadRepository(self._db),
            FeatureStoreRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            repayment_svc,
            scoring_repository=MLScoringRepository(self._db),
        )
        conversion_svc = ConversionService(
            ExternalLeadRepository(self._db),
            ExternalProfileRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            scoring_repository=MLScoringRepository(self._db),
        )
        summary_builder = DecisionSummaryBuilder(
            Customer360Repository(self._db),
            ExternalProfileRepository(self._db),
            ExternalLeadRepository(self._db),
            FeatureStoreRepository(self._db),
            LeadFeatureStoreRepository(self._db),
            repayment_svc,
            product_svc,
            conversion_svc,
        )
        svc = ExplainabilityService(
            ExplainabilityRepository(self._db),
            summary_builder,
            OpenAIService(),
        )
        lim_int, lim_ext = self._scoped_limits()
        r = svc.build_all(limit_internal=lim_int, limit_external=lim_ext)
        return f"reports={r.get('reports_succeeded', 0)}"

    def _run_internal_build_all(self) -> str:
        from app.dependencies import create_internal_pipeline_orchestrator
        from app.repositories.customer_query_repository import CustomerQueryRepository
        from app.repositories.customer360_repository import Customer360Repository
        from app.repositories.feature_store_repository import FeatureStoreRepository
        from app.internal_pipeline.validator import PipelineValidator
        from app.internal_pipeline.progress_tracker import PipelineProgressTracker
        from app.internal_pipeline.pipeline_service import InternalPipelineService

        customer_query_repo = CustomerQueryRepository(self._db)
        customer360_repo = Customer360Repository(self._db)
        feature_repo = FeatureStoreRepository(self._db)
        validator = PipelineValidator(customer_query_repo, customer360_repo, feature_repo)
        progress_tracker = PipelineProgressTracker()

        svc = InternalPipelineService(
            customer_query_repo,
            customer360_repo,
            feature_repo,
            create_internal_pipeline_orchestrator,
            validator,
            progress_tracker,
            self._db,
        )
        customer_ids = customer_query_repo.get_all_customer_ids()
        if self.limit_internal is not None:
            customer_ids = customer_ids[:self.limit_internal]
        r = svc._run_batch(customer_ids)
        return f"completed={r.completed} failed={r.failed}"

