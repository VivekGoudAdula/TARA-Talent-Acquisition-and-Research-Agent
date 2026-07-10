"""Lead Feature Store repository."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.models.lead_feature_store import LeadFeatureStoreEntry
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_MODULE = "external_lead_analytics"
BEHAVIOUR_SUMMARY_SOURCE = "behaviour_summary"

LEAD_FEATURE_KEYS = (
    "lead_score",
    "financial_capacity_score",
    "campaign_engagement_score",
    "digital_readiness_score",
    "lead_quality_score",
    "credit_quality",
    "preferred_channel",
    "preferred_contact_time",
)


class LeadFeatureStoreRepository:
    """Data access layer for the external lead feature store."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._features_cache = {}

    def get_all_features_by_lead(self, lead_id: UUID) -> list[LeadFeatureStoreEntry]:
        key = str(lead_id)
        if key in self._features_cache:
            return self._features_cache[key]
        docs = self._db.lead_feature_store.find({"lead_id": key})
        res = [LeadFeatureStoreEntry.from_doc(d) for d in docs if d]
        self._features_cache[key] = res
        return res

    def upsert_features(
        self,
        lead_id: UUID,
        features: dict[str, Decimal | int | str | None],
        source_module: str = SOURCE_MODULE,
        commit: bool = True,
    ) -> int:
        now = datetime.utcnow()
        count = 0
        lid = str(lead_id)
        self._features_cache.pop(lid, None)
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
                "lead_id": lid,
                "feature_name": name,
                "feature_value_numeric": numeric_val,
                "feature_value_text": text_val,
                "source_module": source_module,
                "last_updated": now,
            }
            from pymongo import ReplaceOne
            operations.append(
                ReplaceOne(
                    {"lead_id": lid, "feature_name": name},
                    doc,
                    upsert=True,
                )
            )
            count += 1

        if operations:
            self._db.lead_feature_store.bulk_write(operations)

        logger.debug("Upserted %d lead features for lead_id=%s", count, lead_id)
        return count

    def get_features_by_lead(
        self,
        lead_id: UUID,
        source_module: str = SOURCE_MODULE,
    ) -> list[LeadFeatureStoreEntry]:
        docs = self._db.lead_feature_store.find(
            {"lead_id": str(lead_id), "source_module": source_module}
        )
        return [LeadFeatureStoreEntry.from_doc(d) for d in docs if d]

    def features_to_dict(self, entries: list[LeadFeatureStoreEntry]) -> dict[str, Decimal | str]:
        result: dict[str, Decimal | str] = {}
        for entry in entries:
            if entry.feature_value_text is not None:
                result[entry.feature_name] = entry.feature_value_text
            elif entry.feature_value_numeric is not None:
                result[entry.feature_name] = Decimal(str(entry.feature_value_numeric))
        return result
