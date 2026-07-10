"""Per-customer orchestration across existing Internal Intelligence engines."""

import traceback
from uuid import UUID

from app.db.mongo import MongoDatabase
from app.repositories.banking_repository import BankingRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.internal_pipeline import CustomerPipelineResult
from app.services.customer360.behaviour_analytics_service import BehaviourAnalyticsService
from app.services.customer360.customer360_service import Customer360Service
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.customer_health_analytics_service import CustomerHealthAnalyticsService
from app.services.customer360.digital_channel_analytics_service import DigitalChannelAnalyticsService
from app.services.customer360.financial_profile_service import FinancialProfileService
from app.services.customer360.relationship_analytics_service import RelationshipAnalyticsService
from app.services.customer360.transaction_analytics_service import TransactionAnalyticsService
from app.utils.exceptions import CustomerNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

STAGE_CUSTOMER360 = "Customer360"
STAGE_FINANCIAL = "Financial Analytics"
STAGE_TRANSACTION = "Transaction Analytics"
STAGE_BEHAVIOUR = "Behaviour Analytics"
STAGE_RELATIONSHIP = "Relationship Analytics"
STAGE_CHANNEL = "Digital & Channel Analytics"
STAGE_HEALTH = "Customer Health Analytics"
STAGE_FEATURE_STORE = "Feature Store"
STAGE_COMPLETED = "Pipeline Completed"


class InternalPipelineOrchestrator:
    """
    Executes the full Internal Intelligence pipeline for a single customer.

    Does not implement analytics logic — only invokes existing services in order.
    """

    def __init__(
        self,
        banking_repository: BankingRepository,
        aggregation_service: CustomerAggregationService,
        customer360_service: Customer360Service,
        financial_service: FinancialProfileService,
        transaction_service: TransactionAnalyticsService,
        behaviour_service: BehaviourAnalyticsService,
        relationship_service: RelationshipAnalyticsService,
        channel_service: DigitalChannelAnalyticsService,
        health_service: CustomerHealthAnalyticsService,
        feature_store_repository: FeatureStoreRepository,
        db: MongoDatabase | None = None,
    ) -> None:
        self._banking_repo = banking_repository
        self._aggregation = aggregation_service
        self._customer360 = customer360_service
        self._financial = financial_service
        self._transaction = transaction_service
        self._behaviour = behaviour_service
        self._relationship = relationship_service
        self._channel = channel_service
        self._health = health_service
        self._feature_repo = feature_store_repository
        self._db = db

    def _next_stage(self, stages_completed: list[str]) -> str:
        stage_order = [
            STAGE_CUSTOMER360,
            STAGE_FINANCIAL,
            STAGE_TRANSACTION,
            STAGE_BEHAVIOUR,
            STAGE_RELATIONSHIP,
            STAGE_CHANNEL,
            STAGE_HEALTH,
            STAGE_FEATURE_STORE,
        ]
        return stage_order[len(stages_completed)] if len(stages_completed) < len(stage_order) else STAGE_COMPLETED

    def _rollback_session(self) -> None:
        if self._db is not None:
            self._db.rollback()

    def run_for_customer(self, customer_id: UUID) -> CustomerPipelineResult:
        stages_completed: list[str] = []

        try:
            if not self._banking_repo.get_customer(customer_id):
                raise CustomerNotFoundError(customer_id)

            logger.info("Pipeline started for customer_id=%s", customer_id)

            aggregate = self._aggregation.aggregate(customer_id)
            self._customer360.build_profile(aggregate)
            stages_completed.append(STAGE_CUSTOMER360)
            logger.info(
                "customer_id=%s | %s Created",
                customer_id,
                STAGE_CUSTOMER360,
            )

            self._financial.compute_and_persist(aggregate)
            stages_completed.append(STAGE_FINANCIAL)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_FINANCIAL,
            )

            self._transaction.compute_and_persist(aggregate)
            stages_completed.append(STAGE_TRANSACTION)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_TRANSACTION,
            )

            self._behaviour.compute_and_persist(aggregate)
            stages_completed.append(STAGE_BEHAVIOUR)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_BEHAVIOUR,
            )

            self._relationship.compute_and_persist(aggregate)
            stages_completed.append(STAGE_RELATIONSHIP)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_RELATIONSHIP,
            )

            self._channel.compute_and_persist(aggregate)
            stages_completed.append(STAGE_CHANNEL)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_CHANNEL,
            )

            self._health.compute_and_persist(aggregate)
            stages_completed.append(STAGE_HEALTH)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_HEALTH,
            )

            self._feature_repo.mark_pipeline_completed(customer_id)
            stages_completed.append(STAGE_FEATURE_STORE)
            logger.info(
                "customer_id=%s | %s Completed",
                customer_id,
                STAGE_FEATURE_STORE,
            )

            stages_completed.append(STAGE_COMPLETED)
            logger.info(
                "customer_id=%s | %s",
                customer_id,
                STAGE_COMPLETED,
            )

            return CustomerPipelineResult(
                customer_id=customer_id,
                success=True,
                stages_completed=stages_completed,
            )

        except Exception as exc:
            failed_stage = self._next_stage(stages_completed)
            self._rollback_session()
            logger.exception(
                "Pipeline failed for customer_id=%s at stage %s: %s",
                customer_id,
                failed_stage,
                exc,
            )
            return CustomerPipelineResult(
                customer_id=customer_id,
                success=False,
                stages_completed=stages_completed,
                failed_stage=failed_stage,
                error=f"{exc}\n{traceback.format_exc()}",
            )
