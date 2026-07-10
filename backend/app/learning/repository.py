"""Mongo persistence for Layer 6 learning artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class LearningRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def upsert_outcome_label(self, record: dict[str, Any]) -> str:
        entity_id = str(record["entity_id"])
        now = datetime.utcnow()
        existing = self._db.outcome_labels.find_one({"entity_id": entity_id})
        label_id = existing.get("label_id") if existing else str(uuid4())
        doc = {
            "label_id": label_id,
            **record,
            "updated_at": now,
        }
        if not existing:
            doc["created_at"] = now
        self._db.outcome_labels.replace_one({"entity_id": entity_id}, doc, upsert=True)
        return label_id

    def bulk_upsert_outcome_labels(self, records: list[dict[str, Any]]) -> int:
        count = 0
        for record in records:
            self.upsert_outcome_label(record)
            count += 1
        return count

    def list_outcome_labels(self, *, limit: int = 500) -> list[dict[str, Any]]:
        docs = list(self._db.outcome_labels.find({}, {"_id": 0}))
        docs.sort(key=lambda d: d.get("updated_at") or datetime.min, reverse=True)
        return docs[:limit]

    def outcome_labels_by_lead_id(self) -> dict[str, float]:
        labels: dict[str, float] = {}
        for doc in self._db.outcome_labels.find({}, {"lead_id": 1, "conversion_label": 1}):
            lead_id = doc.get("lead_id")
            if lead_id is not None:
                labels[str(lead_id)] = float(doc["conversion_label"])
        return labels

    def count_outcome_labels(self) -> int:
        return self._db.outcome_labels.count_documents({})

    def save_performance_snapshot(self, payload: dict[str, Any]) -> str:
        snapshot_id = str(uuid4())
        doc = {
            "snapshot_id": snapshot_id,
            "captured_at": datetime.utcnow(),
            **payload,
        }
        self._db.performance_snapshots.insert_one(doc)
        logger.info("Saved performance snapshot %s", snapshot_id)
        return snapshot_id

    def list_performance_snapshots(self, *, limit: int = 20) -> list[dict[str, Any]]:
        docs = list(self._db.performance_snapshots.find({}, {"_id": 0}))
        docs.sort(key=lambda d: d.get("captured_at") or datetime.min, reverse=True)
        return docs[:limit]

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        return self._db.performance_snapshots.find_one(
            {"snapshot_id": snapshot_id}, {"_id": 0}
        )

    def list_model_runs(self, *, model_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if model_name:
            query["model_name"] = model_name
        docs = list(self._db.ml_model_runs.find(query, {"_id": 0}))
        docs.sort(key=lambda d: d.get("created_at") or datetime.min, reverse=True)
        return docs[:limit]
