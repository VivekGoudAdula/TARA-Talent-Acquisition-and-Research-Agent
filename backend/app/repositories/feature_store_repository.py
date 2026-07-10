"""Feature Store repository — upsert and retrieve analytics features."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.models.feature_store import FeatureStoreEntry
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_MODULE = "transaction_analytics"
BEHAVIOUR_SUMMARY_SOURCE = "behaviour_summary"
PIPELINE_SOURCE_MODULE = "internal_pipeline"
PIPELINE_COMPLETED_FEATURE = "pipeline_completed"


class FeatureStoreRepository:
    """Data access layer for the enterprise feature store."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._features_cache = {}

    def upsert_features(
        self,
        customer_id: UUID,
        features: dict[str, Decimal | int | str | None],
        source_module: str = SOURCE_MODULE,
        commit: bool = True,
    ) -> int:
        now = datetime.utcnow()
        count = 0
        cid = str(customer_id)
        self._features_cache.pop(cid, None)
        operations = []

        for name, value in features.items():
            if value is None:
                continue

            numeric_val: str | None = None
            text_val: str | None = None

            if isinstance(value, str):
                text_val = value
            else:
                numeric_val = str(value)

            doc = {
                "feature_id": str(uuid4()),
                "customer_id": cid,
                "feature_name": name,
                "feature_value_numeric": numeric_val,
                "feature_value_text": text_val,
                "source_module": source_module,
                "last_updated": now,
            }
            from pymongo import ReplaceOne
            operations.append(
                ReplaceOne(
                    {"customer_id": cid, "feature_name": name},
                    doc,
                    upsert=True,
                )
            )
            count += 1

        if operations:
            self._db.feature_store.bulk_write(operations)

        logger.debug("Upserted %d features for customer_id=%s", count, customer_id)
        return count

    def get_features_by_customer(
        self,
        customer_id: UUID,
        source_module: str = SOURCE_MODULE,
    ) -> list[FeatureStoreEntry]:
        docs = self._db.feature_store.find(
            {"customer_id": str(customer_id), "source_module": source_module}
        )
        return [FeatureStoreEntry.from_doc(d) for d in docs if d]

    def get_all_features_by_customer(self, customer_id: UUID) -> list[FeatureStoreEntry]:
        key = str(customer_id)
        if key in self._features_cache:
            return self._features_cache[key]
        docs = self._db.feature_store.find({"customer_id": key})
        res = [FeatureStoreEntry.from_doc(d) for d in docs if d]
        self._features_cache[key] = res
        return res

    def features_to_dict(self, entries: list[FeatureStoreEntry]) -> dict[str, Decimal | str]:
        result: dict[str, Decimal | str] = {}
        for entry in entries:
            if entry.feature_value_text is not None:
                result[entry.feature_name] = entry.feature_value_text
            elif entry.feature_value_numeric is not None:
                result[entry.feature_name] = Decimal(str(entry.feature_value_numeric))
        return result

    def count_distinct_customers(self) -> int:
        return len(self._db.feature_store.distinct("customer_id"))

    def count_rows(self) -> int:
        return self._db.feature_store.count_documents({})

    def count_pipeline_completed_customers(self) -> int:
        return self._db.feature_store.count_documents(
            {
                "source_module": PIPELINE_SOURCE_MODULE,
                "feature_name": PIPELINE_COMPLETED_FEATURE,
            }
        )

    def mark_pipeline_completed(self, customer_id: UUID) -> None:
        self.upsert_features(
            customer_id,
            {PIPELINE_COMPLETED_FEATURE: 1},
            source_module=PIPELINE_SOURCE_MODULE,
        )

    def customer_has_pipeline_completed(self, customer_id: UUID) -> bool:
        return (
            self._db.feature_store.count_documents(
                {
                    "customer_id": str(customer_id),
                    "source_module": PIPELINE_SOURCE_MODULE,
                    "feature_name": PIPELINE_COMPLETED_FEATURE,
                },
                limit=1,
            )
            > 0
        )
