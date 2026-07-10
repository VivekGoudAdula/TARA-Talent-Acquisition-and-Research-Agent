"""Customer Aggregation Service — collects data from core banking tables."""

from uuid import UUID

from app.repositories.banking_repository import BankingRepository
from app.schemas.banking import (
    AccountSchema,
    ConsentSchema,
    CustomerProductSchema,
    CustomerSchema,
    ProductSchema,
    TransactionSchema,
)
from app.schemas.customer360 import CustomerAggregate
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CustomerAggregationService:
    """
    Aggregation layer that merges customer data from multiple banking tables
    into a single trusted CustomerAggregate object.

    No scoring, segmentation, or analytics are performed here.
    """

    def __init__(self, banking_repository: BankingRepository) -> None:
        self._banking_repo = banking_repository

    def aggregate(self, customer_id: UUID) -> CustomerAggregate:
        """
        Collect and merge all banking data for a customer.

        Raises:
            CustomerNotFoundError: If the customer_id does not exist.
        """
        logger.info("Aggregating banking data for customer_id=%s", customer_id)

        customer = self._banking_repo.get_customer_or_raise(customer_id)
        accounts = self._banking_repo.get_accounts_by_customer(customer_id)
        account_ids = [account.account_id for account in accounts]
        transactions = self._banking_repo.get_transactions_by_account_ids(account_ids)

        customer_products = self._banking_repo.get_customer_products(customer_id)
        product_ids = [cp.product_id for cp in customer_products]
        product_map = self._banking_repo.get_products_by_ids(product_ids)

        consent = self._banking_repo.get_consent_by_customer(customer_id)

        product_schemas = [
            CustomerProductSchema(
                customer_product_id=cp.customer_product_id,
                customer_id=cp.customer_id,
                product_id=cp.product_id,
                opened_date=cp.opened_date,
                status=cp.status,
                product=ProductSchema.model_validate(product_map[cp.product_id])
                if cp.product_id in product_map
                else None,
            )
            for cp in customer_products
        ]

        aggregate = CustomerAggregate(
            customer=CustomerSchema.model_validate(customer),
            accounts=[AccountSchema.model_validate(a) for a in accounts],
            transactions=[TransactionSchema.model_validate(t) for t in transactions],
            products=product_schemas,
            consent=ConsentSchema.model_validate(consent) if consent else None,
        )

        logger.info(
            "Aggregation complete for customer_id=%s: accounts=%d transactions=%d products=%d consent=%s",
            customer_id,
            len(aggregate.accounts),
            len(aggregate.transactions),
            len(aggregate.products),
            aggregate.consent is not None,
        )
        return aggregate
