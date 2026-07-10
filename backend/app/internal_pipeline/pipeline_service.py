"""High-level service for batch and single-customer pipeline execution."""

from collections.abc import Callable
from uuid import UUID

from app.db.mongo import MongoDatabase

from app.internal_pipeline.orchestrator import InternalPipelineOrchestrator
from app.internal_pipeline.progress_tracker import PipelineProgressTracker
from app.internal_pipeline.validator import PipelineValidator
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.internal_pipeline import (
    CustomerPipelineResult,
    PipelineBuildSummary,
    PipelineStatusResponse,
)
from app.utils.database import new_session
from app.utils.exceptions import CustomerNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _format_success_rate(completed: int, total: int) -> str:
    if total == 0:
        return "0%"
    rate = round((completed / total) * 100, 2)
    if rate == int(rate):
        return f"{int(rate)}%"
    return f"{rate}%"


class InternalPipelineService:
    """Coordinates build-all, build-one, status, and validation."""

    def __init__(
        self,
        customer_query_repository: CustomerQueryRepository,
        customer360_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
        orchestrator_factory: Callable[[MongoDatabase], InternalPipelineOrchestrator],
        validator: PipelineValidator,
        progress_tracker: PipelineProgressTracker,
        db: MongoDatabase,
    ) -> None:
        self._customer_query = customer_query_repository
        self._profile_repo = customer360_repository
        self._feature_repo = feature_store_repository
        self._orchestrator_factory = orchestrator_factory
        self._validator = validator
        self._tracker = progress_tracker
        self._db = db

    def build_all(self) -> PipelineBuildSummary:
        customer_ids = self._customer_query.get_all_customer_ids()
        logger.info("Starting internal pipeline for %d customers", len(customer_ids))
        return self._run_batch(customer_ids)

    def build_one(self, customer_id: UUID) -> PipelineBuildSummary:
        if not self._customer_query.customer_exists(customer_id):
            raise CustomerNotFoundError(customer_id)
        logger.info("Starting internal pipeline for customer_id=%s", customer_id)
        return self._run_batch([customer_id])

    def get_status(self) -> PipelineStatusResponse:
        total = self._customer_query.count_customers()
        profiles = self._profile_repo.count_profiles()
        feature_store = self._feature_repo.count_distinct_customers()
        pipeline_completed = self._feature_repo.count_pipeline_completed_customers()
        failed_ids = self._tracker.get_failed_customer_ids()

        all_ids = set(self._customer_query.get_all_customer_ids())
        profile_ids = {
            profile.customer_id for profile in self._profile_repo.get_all_profiles()
        }
        completed_ids = {
            cid
            for cid in all_ids
            if cid in profile_ids and self._feature_repo.customer_has_pipeline_completed(cid)
        }
        pending_ids = sorted(all_ids - completed_ids, key=str)

        successful = len(completed_ids)
        return PipelineStatusResponse(
            total_customers=total,
            profiles_built=profiles,
            feature_store_built=feature_store,
            pipeline_completed=pipeline_completed,
            pending_customers=len(pending_ids),
            failed_customers=len(failed_ids),
            success_percentage=_format_success_rate(successful, total),
            pending_customer_ids=[str(cid) for cid in pending_ids],
            failed_customer_ids=[str(cid) for cid in failed_ids],
            is_running=self._tracker.is_running(),
        )

    def _run_batch(self, customer_ids: list[UUID]) -> PipelineBuildSummary:
        self._tracker.start_run(len(customer_ids))
        results: list[CustomerPipelineResult] = []
        succeeded = 0

        for customer_id in customer_ids:
            result = self._run_customer_isolated(customer_id)
            results.append(result)
            if result.success:
                succeeded += 1
                self._tracker.record_success(customer_id)
            else:
                self._tracker.record_failure(customer_id)
                logger.error(
                    "Pipeline failed customer_id=%s stage=%s error=%s",
                    customer_id,
                    result.failed_stage,
                    (result.error or "")[:500],
                )

        self._db.expire_all()
        run_state = self._tracker.finish_run()
        validation = self._validator.validate()

        summary = PipelineBuildSummary(
            customers=validation.customers,
            profiles=validation.profiles,
            feature_store=validation.feature_store_customers,
            completed=succeeded,
            failed=len(run_state.failed_customer_ids),
            success_rate=_format_success_rate(succeeded, len(customer_ids)),
            failed_customer_ids=[str(cid) for cid in run_state.failed_customer_ids],
            validation=validation,
            results=results if len(customer_ids) <= 10 else [],
        )

        logger.info(
            "Internal pipeline finished: completed=%d failed=%d success_rate=%s valid=%s",
            summary.completed,
            summary.failed,
            summary.success_rate,
            validation.is_valid,
        )
        return summary

    def _run_customer_isolated(self, customer_id: UUID) -> CustomerPipelineResult:
        """Run pipeline in a dedicated DB session so one failure cannot poison the batch."""
        session = new_session()
        try:
            orchestrator = self._orchestrator_factory(session)
            return orchestrator.run_for_customer(customer_id)
        except Exception as exc:
            session.rollback()
            logger.exception("Unexpected pipeline error for customer_id=%s", customer_id)
            return CustomerPipelineResult(
                customer_id=customer_id,
                success=False,
                failed_stage="start",
                error=str(exc),
            )
        finally:
            session.close()
