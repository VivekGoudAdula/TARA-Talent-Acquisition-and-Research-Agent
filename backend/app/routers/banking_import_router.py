"""API routes for internal banking Excel import."""

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_banking_import_service, get_pipeline_orchestrator
from app.internal.banking_import_service import BankingImportService
from app.schemas.banking_import import BankingImportResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/internal", tags=["Internal Banking Import"])


@router.post(
    "/import",
    response_model=BankingImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import internal banking data from Excel workbooks",
    description=(
        "Loads customer_master, transaction_history, loan_history, and digital_activity "
        "Excel files into MongoDB banking collections (customers, accounts, transactions, etc.)."
    ),
)
def import_internal_banking_data(
    run_pipeline: bool = Query(default=False, description="Run internal intelligence+scoring after import"),
    service: BankingImportService = Depends(get_banking_import_service),
    pipeline=Depends(get_pipeline_orchestrator),
) -> BankingImportResponse:
    from app.config import get_settings

    result = service.import_from_excel()
    logger.info("Internal banking import via API: %s", result)
    settings = get_settings()
    if run_pipeline or settings.pipeline_auto_run_on_import:
        try:
            pipeline.run_internal_pipeline()
        except Exception as exc:
            logger.warning("Post-import internal pipeline failed: %s", exc)
    return BankingImportResponse(**result)
