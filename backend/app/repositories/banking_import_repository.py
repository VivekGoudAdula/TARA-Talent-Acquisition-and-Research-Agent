"""Bulk persistence for banking collections loaded from Excel."""

from __future__ import annotations

import time

from pymongo.errors import BulkWriteError

from app.db.mongo import MongoDatabase, ensure_indexes
from app.internal.banking_excel_importer import BankingImportBundle
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

BANKING_COLLECTIONS = (
    "customers",
    "products",
    "accounts",
    "transactions",
    "customer_products",
    "consent",
    "digital_activity",
)

# MongoDB duplicate key error code
_DUPLICATE_KEY_CODE = 11000


class BankingImportRepository:
    """Writes transformed banking bundles into MongoDB."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def load_bundle(self, bundle: BankingImportBundle, *, replace_existing: bool = True) -> dict[str, int]:
        if replace_existing:
            for name in BANKING_COLLECTIONS:
                self._db._db[name].drop()
            ensure_indexes(collections=set(BANKING_COLLECTIONS))

        specs: list[tuple[str, list[dict]]] = [
            ("products", bundle.products),
            ("customers", bundle.customers),
            ("accounts", bundle.accounts),
            ("consent", bundle.consent),
            ("customer_products", bundle.customer_products),
            ("transactions", bundle.transactions),
            ("digital_activity", bundle.digital_activity),
        ]

        counts: dict[str, int] = {}
        for collection, docs in specs:
            if not docs:
                counts[collection] = 0
                continue
            inserted = self._insert_many(collection, docs)
            counts[collection] = inserted
            logger.info("Loaded %d documents into %s (skipped duplicates)", inserted, collection)

        return counts

    def _insert_many(self, collection: str, docs: list[dict], *, batch_size: int = 500) -> int:
        """Insert docs in batches. Duplicate key errors are skipped (not retried).
        Returns the number of successfully inserted documents."""
        coll = self._db._db[collection]
        total_inserted = 0

        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            for attempt in range(5):
                try:
                    result = coll.insert_many(batch, ordered=False)
                    total_inserted += len(result.inserted_ids)
                    break
                except BulkWriteError as exc:
                    write_errors = exc.details.get("writeErrors", [])
                    # If every error in this batch is a duplicate key error,
                    # treat it as non-fatal — the docs already exist.
                    non_dup_errors = [e for e in write_errors if e.get("code") != _DUPLICATE_KEY_CODE]
                    n_inserted = exc.details.get("nInserted", 0)
                    total_inserted += n_inserted
                    dup_count = len(write_errors) - len(non_dup_errors)
                    if dup_count:
                        logger.debug(
                            "Skipped %d duplicate(s) in %s batch %d",
                            dup_count, collection, i // batch_size,
                        )
                    if non_dup_errors:
                        # Real transient errors — retry
                        if attempt == 4:
                            raise
                        time.sleep(2 ** attempt)
                    else:
                        # Only duplicates — move to next batch
                        break
                except Exception:
                    if attempt == 4:
                        raise
                    time.sleep(2 ** attempt)

        return total_inserted
