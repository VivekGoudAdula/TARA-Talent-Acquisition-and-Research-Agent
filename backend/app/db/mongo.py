"""MongoDB connection, database wrapper, and index management."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.mongodb_uri:
            raise RuntimeError(
                "MONGODB_URI is not set. Add your Azure Cosmos DB connection string to .env"
            )
        _client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=120000,
        )
        logger.info("MongoDB client initialized for database=%s", settings.mongodb_db_name)
    return _client


def get_database() -> Database:
    settings = get_settings()
    return get_mongo_client()[settings.mongodb_db_name]


class MongoDatabase:
    """Thin wrapper exposing Tara collections and session helpers."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db or get_database()

    # --- collections ---
    @property
    def customers(self) -> Collection:
        return self._db["customers"]

    @property
    def accounts(self) -> Collection:
        return self._db["accounts"]

    @property
    def transactions(self) -> Collection:
        return self._db["transactions"]

    @property
    def products(self) -> Collection:
        return self._db["products"]

    @property
    def customer_products(self) -> Collection:
        return self._db["customer_products"]

    @property
    def consent(self) -> Collection:
        return self._db["consent"]

    @property
    def customer_360_profile(self) -> Collection:
        return self._db["customer_360_profile"]

    @property
    def feature_store(self) -> Collection:
        return self._db["feature_store"]

    @property
    def external_leads(self) -> Collection:
        return self._db["external_leads"]

    @property
    def external_customer_profile(self) -> Collection:
        return self._db["external_customer_profile"]

    @property
    def lead_feature_store(self) -> Collection:
        return self._db["lead_feature_store"]

    @property
    def training_dataset(self) -> Collection:
        return self._db["training_dataset"]

    @property
    def explainability_reports(self) -> Collection:
        return self._db["explainability_reports"]

    @property
    def repayment_predictions(self) -> Collection:
        return self._db["repayment_predictions"]

    @property
    def product_recommendations(self) -> Collection:
        return self._db["product_recommendations"]

    @property
    def conversion_predictions(self) -> Collection:
        return self._db["conversion_predictions"]

    @property
    def ml_model_runs(self) -> Collection:
        return self._db["ml_model_runs"]

    @property
    def engagement_events(self) -> Collection:
        return self._db["engagement_events"]

    @property
    def lead_responses(self) -> Collection:
        return self._db["lead_responses"]

    @property
    def onboarding_journeys(self) -> Collection:
        return self._db["onboarding_journeys"]

    @property
    def rm_handoffs(self) -> Collection:
        return self._db["rm_handoffs"]

    @property
    def outcome_labels(self) -> Collection:
        return self._db["outcome_labels"]

    @property
    def performance_snapshots(self) -> Collection:
        return self._db["performance_snapshots"]

    @property
    def pipeline_runs(self) -> Collection:
        return self._db["pipeline_runs"]

    @property
    def engagement_sequences(self) -> Collection:
        return self._db["engagement_sequences"]

    @property
    def activation_journeys(self) -> Collection:
        return self._db["activation_journeys"]

    @property
    def kyc_documents(self) -> Collection:
        return self._db["kyc_documents"]

    @property
    def rm_handoff_activity(self) -> Collection:
        return self._db["rm_handoff_activity"]

    @property
    def email_cta_clicks(self) -> Collection:
        return self._db["email_cta_clicks"]

    @property
    def callback_cta_tokens(self) -> Collection:
        return self._db["callback_cta_tokens"]

    @property
    def voice_callback_sessions(self) -> Collection:
        return self._db["voice_callback_sessions"]

    @property
    def voice_callback_dedup(self) -> Collection:
        return self._db["voice_callback_dedup"]

    @property
    def channel_messages(self) -> Collection:
        return self._db["channel_messages"]

    @property
    def digital_activity(self) -> Collection:
        return self._db["digital_activity"]

    def commit(self) -> None:
        """No-op — MongoDB writes are immediate. Kept for repository compatibility."""

    def rollback(self) -> None:
        """No-op — per-request isolation uses separate MongoDatabase instances."""

    def expire_all(self) -> None:
        """No-op — compatibility with legacy session refresh."""

    def close(self) -> None:
        """No-op — client lifecycle managed globally."""


INDEX_SPECS: list[tuple[str, list[tuple[str, int]], bool, dict[str, Any] | None]] = [
    ("customers", [("customer_id", ASCENDING)], True, None),
    ("accounts", [("account_id", ASCENDING)], True, None),
    ("accounts", [("customer_id", ASCENDING)], False, None),
    ("transactions", [("transaction_id", ASCENDING)], True, None),
    ("transactions", [("account_id", ASCENDING)], False, None),
    ("products", [("product_id", ASCENDING)], True, None),
    ("customer_products", [("customer_product_id", ASCENDING)], True, None),
    ("customer_products", [("customer_id", ASCENDING)], False, None),
    ("consent", [("consent_id", ASCENDING)], True, None),
    ("consent", [("customer_id", ASCENDING)], False, None),
    ("digital_activity", [("customer_id", ASCENDING)], True, None),
    ("customer_360_profile", [("profile_id", ASCENDING)], True, None),
    ("customer_360_profile", [("customer_id", ASCENDING)], True, None),
    (
        "feature_store",
        [("customer_id", ASCENDING), ("feature_name", ASCENDING)],
        True,
        None,
    ),
    ("feature_store", [("customer_id", ASCENDING)], False, None),
    ("external_leads", [("lead_id", ASCENDING)], True, None),
    ("external_leads", [("external_reference", ASCENDING)], True, None),
    ("external_customer_profile", [("profile_id", ASCENDING)], True, None),
    ("external_customer_profile", [("lead_id", ASCENDING)], True, None),
    (
        "lead_feature_store",
        [("lead_id", ASCENDING), ("feature_name", ASCENDING)],
        True,
        None,
    ),
    ("training_dataset", [("record_id", ASCENDING)], True, None),
    ("training_dataset", [("profile_id", ASCENDING)], False, None),
    ("explainability_reports", [("report_id", ASCENDING)], True, None),
    ("explainability_reports", [("customer_id", ASCENDING)], True, None),
    ("repayment_predictions", [("profile_id", ASCENDING)], True, None),
    ("product_recommendations", [("profile_id", ASCENDING)], True, None),
    ("conversion_predictions", [("lead_id", ASCENDING)], True, None),
    ("ml_model_runs", [("run_id", ASCENDING)], True, None),
    ("ml_model_runs", [("model_name", ASCENDING)], False, None),
    ("engagement_events", [("event_id", ASCENDING)], True, None),
    ("engagement_events", [("entity_id", ASCENDING)], False, None),
    ("engagement_events", [("channel", ASCENDING)], False, None),
    ("lead_responses", [("response_id", ASCENDING)], True, None),
    ("lead_responses", [("entity_id", ASCENDING)], False, None),
    ("onboarding_journeys", [("journey_id", ASCENDING)], True, None),
    ("onboarding_journeys", [("entity_id", ASCENDING)], True, None),
    ("rm_handoffs", [("handoff_id", ASCENDING)], True, None),
    ("rm_handoffs", [("entity_id", ASCENDING)], False, None),
    ("rm_handoffs", [("status", ASCENDING)], False, None),
    ("outcome_labels", [("label_id", ASCENDING)], True, None),
    ("outcome_labels", [("entity_id", ASCENDING)], True, None),
    ("outcome_labels", [("lead_id", ASCENDING)], False, None),
    ("performance_snapshots", [("snapshot_id", ASCENDING)], True, None),
    ("pipeline_runs", [("run_id", ASCENDING)], True, None),
    ("engagement_sequences", [("sequence_id", ASCENDING)], True, None),
    ("engagement_sequences", [("entity_id", ASCENDING)], False, None),
    ("activation_journeys", [("activation_id", ASCENDING)], True, None),
    ("activation_journeys", [("entity_id", ASCENDING)], False, None),
    ("kyc_documents", [("document_id", ASCENDING)], True, None),
    ("kyc_documents", [("entity_id", ASCENDING)], False, None),
    ("rm_handoff_activity", [("activity_id", ASCENDING)], True, None),
    ("email_cta_clicks", [("click_id", ASCENDING)], True, None),
    ("voice_callback_sessions", [("session_id", ASCENDING)], True, None),
    ("voice_callback_sessions", [("entity_id", ASCENDING)], False, None),
    ("voice_callback_dedup", [("dedup_key", ASCENDING), ("created_at", ASCENDING)], False, None),
    ("callback_cta_tokens", [("token", ASCENDING)], True, None),
    ("callback_cta_tokens", [("expires_at", ASCENDING)], False, None),
    ("channel_messages", [("message_id", ASCENDING)], True, None),
    ("channel_messages", [("entity_id", ASCENDING), ("created_at", ASCENDING)], False, None),
    ("channel_messages", [("thread_id", ASCENDING), ("created_at", ASCENDING)], False, None),
]


def _index_key_tuple(keys: list[tuple[str, int]]) -> tuple[tuple[str, int], ...]:
    return tuple(keys)


def _collection_has_index(coll: Collection, keys: list[tuple[str, int]], *, unique: bool) -> bool:
    target = _index_key_tuple(keys)
    for info in coll.index_information().values():
        if tuple(info.get("key", ())) == target and bool(info.get("unique")) == unique:
            return True
    return False


def ensure_indexes(collections: set[str] | None = None) -> None:
    """Create MongoDB collection indexes.

    When ``collections`` is set, only indexes for those collection names are applied.
    Unique indexes are skipped on non-empty collections (Azure Cosmos DB limitation).
    """
    db = get_database()
    for coll_name, keys, unique, extra in INDEX_SPECS:
        if collections is not None and coll_name not in collections:
            continue
        coll = db[coll_name]
        if _collection_has_index(coll, keys, unique=unique):
            continue
        if unique and coll.count_documents({}, limit=1) > 0:
            logger.warning(
                "Skipping unique index %s on %s — collection is not empty (Cosmos DB)",
                keys,
                coll_name,
            )
            continue
        kwargs: dict[str, Any] = {"unique": unique}
        if extra:
            kwargs.update(extra)
        coll.create_index(keys, **kwargs)
    logger.info("MongoDB indexes ensured for Tara database")


def get_db() -> Generator[MongoDatabase, None, None]:
    """FastAPI dependency yielding a MongoDB database wrapper."""
    db = MongoDatabase()
    try:
        yield db
    finally:
        db.close()


def new_session() -> MongoDatabase:
    """Create an isolated database wrapper for batch pipeline processing."""
    return MongoDatabase()
