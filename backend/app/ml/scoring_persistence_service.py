"""Batch persistence for all ML scoring outputs across internal and external profiles."""

from __future__ import annotations

from uuid import UUID

from app.ml.conversion.service import ConversionService
from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
from app.ml.repayment.service import RepaymentCapacityService
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.ml_scoring_repository import MLScoringRepository
from app.schemas.product_recommendation import ProductRecommendRequest
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ScoringPersistenceService:
    """Runs repayment, product-fit, and conversion scoring for all profiles and persists to MongoDB."""

    def __init__(
        self,
        customer360_repository: Customer360Repository,
        external_profile_repository: ExternalProfileRepository,
        external_lead_repository: ExternalLeadRepository,
        repayment_service: RepaymentCapacityService,
        product_service: ProductRecommendationService,
        conversion_service: ConversionService,
        scoring_repository: MLScoringRepository,
    ) -> None:
        self._internal_repo = customer360_repository
        self._external_repo = external_profile_repository
        self._lead_repo = external_lead_repository
        self._repayment = repayment_service
        self._product = product_service
        self._conversion = conversion_service
        self._scoring_repo = scoring_repository

    def build_all(
        self,
        top_n: int = 5,
        limit_internal: int | None = None,
        limit_external: int | None = None,
    ) -> dict[str, int | str]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        repayment_ok = 0
        product_ok = 0
        conversion_ok = 0
        failed = 0

        def score_profile(profile, profile_type: str) -> bool:
            try:
                self._repayment.predict(
                    profile_id=profile.profile_id,
                    profile_type=profile_type,
                )
                self._product.recommend(
                    ProductRecommendRequest(profile_id=profile.profile_id, top_n=top_n)
                )
                return True
            except Exception as exc:
                logger.warning(
                    "Scoring persistence failed %s profile_id=%s: %s",
                    profile_type.lower(),
                    profile.profile_id,
                    exc,
                )
                return False

        internal_profiles = self._internal_repo.get_all_profiles()
        if limit_internal is not None:
            internal_profiles = internal_profiles[:limit_internal]

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(score_profile, p, "Internal"): p for p in internal_profiles}
            for fut in as_completed(futures):
                if fut.result():
                    repayment_ok += 1
                    product_ok += 1
                else:
                    failed += 1

        external_profiles = self._external_repo.get_all_profiles()
        if limit_external is not None:
            external_profiles = external_profiles[:limit_external]

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(score_profile, p, "External"): p for p in external_profiles}
            for fut in as_completed(futures):
                if fut.result():
                    repayment_ok += 1
                    product_ok += 1
                else:
                    failed += 1

        if self._conversion is not None:
            leads = self._lead_repo.get_all(limit=10000)
            if limit_external is not None:
                leads = leads[:limit_external]

            def score_lead(lead) -> bool:
                try:
                    self._conversion.predict(lead_id=lead.lead_id)
                    return True
                except Exception as exc:
                    logger.warning(
                        "Conversion persistence failed lead_id=%s: %s", lead.lead_id, exc
                    )
                    return False

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(score_lead, l): l for l in leads}
                for fut in as_completed(futures):
                    if fut.result():
                        conversion_ok += 1
                    else:
                        failed += 1

        return {
            "repayment_persisted": repayment_ok,
            "product_recommendations_persisted": product_ok,
            "conversion_persisted": conversion_ok,
            "failed": failed,
        }
