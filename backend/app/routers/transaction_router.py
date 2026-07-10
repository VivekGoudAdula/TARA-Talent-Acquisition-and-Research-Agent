"""Transaction analytics API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import (
    get_aggregation_service,
    get_customer_query_repository,
    get_transaction_analytics_service,
    get_banking_repository,
)
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.repositories.banking_repository import BankingRepository
from app.schemas.banking import TransactionSchema
from app.schemas.transaction_analytics import (
    TransactionAnalyticsProfile,
    TransactionAnalyticsResponse,
    TransactionBuildAllResponse,
)
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.transaction_analytics_service import TransactionAnalyticsService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/customer360/transaction", tags=["Transaction Analytics"])
frontend_router = APIRouter(prefix="/api/transactions", tags=["Transactions Frontend"])


@router.post(
    "/build-all",
    response_model=TransactionBuildAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute transaction analytics for all customers",
)
def build_all_transaction_analytics(
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    transaction_service: TransactionAnalyticsService = Depends(get_transaction_analytics_service),
    customer_query: CustomerQueryRepository = Depends(get_customer_query_repository),
) -> TransactionBuildAllResponse:
    customer_ids = customer_query.get_all_customer_ids()
    succeeded = 0
    failed = 0

    for customer_id in customer_ids:
        try:
            aggregate = aggregation_service.aggregate(customer_id)
            transaction_service.compute_and_persist(aggregate)
            succeeded += 1
        except Exception as exc:
            failed += 1
            logger.warning("Transaction analytics failed for customer_id=%s: %s", customer_id, exc)

    logger.info(
        "Batch transaction analytics complete: processed=%d succeeded=%d failed=%d",
        len(customer_ids),
        succeeded,
        failed,
    )
    return TransactionBuildAllResponse(
        message="Batch transaction analytics completed",
        customers_processed=len(customer_ids),
        customers_succeeded=succeeded,
        customers_failed=failed,
    )


@router.post(
    "/{customer_id}",
    response_model=TransactionAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute transaction analytics for one customer",
)
def compute_transaction_analytics(
    customer_id: UUID,
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    transaction_service: TransactionAnalyticsService = Depends(get_transaction_analytics_service),
) -> TransactionAnalyticsResponse:
    aggregate = aggregation_service.aggregate(customer_id)
    analytics = transaction_service.compute_and_persist(aggregate)
    return TransactionAnalyticsResponse(
        message="Transaction analytics computed and persisted successfully",
        analytics=analytics,
    )


@router.get(
    "/{customer_id}",
    response_model=TransactionAnalyticsProfile,
    summary="Get stored transaction analytics",
)
def get_transaction_analytics(
    customer_id: UUID,
    transaction_service: TransactionAnalyticsService = Depends(get_transaction_analytics_service),
) -> TransactionAnalyticsProfile:
    return transaction_service.get_analytics(customer_id)


@frontend_router.get(
    "/{customer_id}",
    response_model=list[TransactionSchema],
    summary="Get raw transaction list for a customer",
)
def get_customer_transactions(
    customer_id: UUID,
    limit: int = 50,
    banking_repo: BankingRepository = Depends(get_banking_repository),
) -> list[TransactionSchema]:
    accounts = banking_repo.get_accounts_by_customer(customer_id)
    account_ids = [acc.account_id for acc in accounts]
    transactions = banking_repo.get_transactions_by_account_ids(account_ids)
    
    # Sort transactions by date descending and apply limit
    transactions.sort(key=lambda t: t.date.isoformat() if hasattr(t.date, "isoformat") else str(t.date or ""), reverse=True)
    if limit:
        transactions = transactions[:limit]
        
    return [TransactionSchema.model_validate(t) for t in transactions]

