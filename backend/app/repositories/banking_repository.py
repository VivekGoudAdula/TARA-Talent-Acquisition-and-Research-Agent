"""Read-only repository for core banking collections."""

from uuid import UUID

from app.db.mongo import MongoDatabase
from app.models.banking import Account, Consent, Customer, CustomerProduct, Product, Transaction
from app.utils.exceptions import CustomerNotFoundError


class BankingRepository:
    """Data access layer for banking collections."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def get_customer(self, customer_id: UUID) -> Customer | None:
        doc = self._db.customers.find_one({"customer_id": str(customer_id)})
        return Customer.from_doc(doc)

    def get_customer_or_raise(self, customer_id: UUID) -> Customer:
        customer = self.get_customer(customer_id)
        if customer is None:
            raise CustomerNotFoundError(customer_id)
        return customer

    def get_accounts_by_customer(self, customer_id: UUID) -> list[Account]:
        docs = self._db.accounts.find({"customer_id": str(customer_id)})
        return [Account.from_doc(d) for d in docs if d]

    def get_transactions_by_account_ids(self, account_ids: list[UUID]) -> list[Transaction]:
        if not account_ids:
            return []
        ids = [str(aid) for aid in account_ids]
        docs = self._db.transactions.find({"account_id": {"$in": ids}})
        return [Transaction.from_doc(d) for d in docs if d]

    def get_customer_products(self, customer_id: UUID) -> list[CustomerProduct]:
        docs = self._db.customer_products.find({"customer_id": str(customer_id)})
        return [CustomerProduct.from_doc(d) for d in docs if d]

    def get_products_by_ids(self, product_ids: list[UUID]) -> dict[UUID, Product]:
        if not product_ids:
            return {}
        ids = [str(pid) for pid in product_ids]
        docs = self._db.products.find({"product_id": {"$in": ids}})
        result: dict[UUID, Product] = {}
        for doc in docs:
            product = Product.from_doc(doc)
            if product:
                result[product.product_id] = product
        return result

    def get_consent_by_customer(self, customer_id: UUID) -> Consent | None:
        doc = self._db.consent.find_one({"customer_id": str(customer_id)})
        return Consent.from_doc(doc)
