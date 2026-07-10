"""API routes for batch ML scoring persistence."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_scoring_persistence_service
from app.ml.scoring_persistence_service import ScoringPersistenceService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ml/scoring", tags=["ML Scoring Persistence"])


@router.post(
    "/build-all",
    status_code=status.HTTP_200_OK,
    summary="Persist repayment, product-fit, and conversion scores for all profiles",
    description=(
        "Runs repayment prediction, product recommendation, and conversion prediction "
        "for every internal/external profile and external lead, saving results to MongoDB."
    ),
)
def build_all_scoring(
    service: ScoringPersistenceService = Depends(get_scoring_persistence_service),
) -> dict:
    result = service.build_all()
    logger.info("ML scoring persistence complete: %s", result)
    return result
