"""Customer ID queries for batch analytics jobs."""

from uuid import UUID

from app.db.mongo import MongoDatabase


class CustomerQueryRepository:
    """Read-only queries against the customers collection."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def get_all_customer_ids(self) -> list[UUID]:
        docs = self._db.customers.find({}, {"customer_id": 1})
        return [UUID(doc["customer_id"]) for doc in docs]

    def count_customers(self) -> int:
        return self._db.customers.count_documents({})

    def customer_exists(self, customer_id: UUID) -> bool:
        return (
            self._db.customers.count_documents({"customer_id": str(customer_id)}, limit=1)
            > 0
        )
