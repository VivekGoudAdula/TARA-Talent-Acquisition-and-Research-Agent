"""Post-run validation for Internal Intelligence pipeline coverage."""

from app.repositories.customer360_repository import Customer360Repository
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.schemas.internal_pipeline import PipelineValidationDetail
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class PipelineValidator:
    """Verifies customer, profile, and feature store counts are aligned."""

    def __init__(
        self,
        customer_query_repository: CustomerQueryRepository,
        customer360_repository: Customer360Repository,
        feature_store_repository: FeatureStoreRepository,
    ) -> None:
        self._customer_repo = customer_query_repository
        self._profile_repo = customer360_repository
        self._feature_repo = feature_store_repository

    def validate(self) -> PipelineValidationDetail:
        customers = self._customer_repo.count_customers()
        profiles = self._profile_repo.count_profiles()
        feature_store_customers = self._feature_repo.count_distinct_customers()
        feature_store_rows = self._feature_repo.count_rows()
        pipeline_completed = self._feature_repo.count_pipeline_completed_customers()

        mismatches: list[str] = []

        if customers != profiles:
            mismatches.append(
                f"customers ({customers}) != customer_360_profile ({profiles})"
            )
        if customers != feature_store_customers:
            mismatches.append(
                f"customers ({customers}) != distinct feature_store customers "
                f"({feature_store_customers})"
            )
        if customers != pipeline_completed:
            mismatches.append(
                f"customers ({customers}) != pipeline_completed markers ({pipeline_completed})"
            )

        is_valid = len(mismatches) == 0

        if is_valid:
            logger.info(
                "Pipeline validation passed: customers=%s profiles=%s feature_store=%s",
                customers,
                profiles,
                feature_store_customers,
            )
        else:
            logger.warning(
                "Pipeline validation failed: %s",
                "; ".join(mismatches),
            )

        return PipelineValidationDetail(
            customers=customers,
            profiles=profiles,
            feature_store_customers=feature_store_customers,
            feature_store_rows=feature_store_rows,
            pipeline_completed=pipeline_completed,
            is_valid=is_valid,
            mismatches=mismatches,
        )
