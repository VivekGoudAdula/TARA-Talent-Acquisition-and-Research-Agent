"""Mongo persistence for WhatsApp / SMS / Email conversation threads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ConversationRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def append_message(
        self,
        *,
        entity_id: str,
        entity_type: str,
        channel: str,
        direction: str,
        role: str,
        body: str,
        response_type: str | None = None,
        provider_sid: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid4())
        thread_id = f"{entity_id}:{channel}"
        now = datetime.utcnow()
        doc = {
            "message_id": message_id,
            "thread_id": thread_id,
            "entity_id": str(entity_id),
            "entity_type": entity_type,
            "channel": channel,
            "direction": direction,
            "role": role,
            "body": body,
            "response_type": response_type,
            "provider_sid": provider_sid,
            "metadata": metadata or {},
            "created_at": now,
        }
        self._db.channel_messages.insert_one(doc)
        logger.debug(
            "Conversation %s %s entity=%s channel=%s",
            direction,
            role,
            entity_id,
            channel,
        )
        return doc

    def list_messages(
        self,
        entity_id: str,
        *,
        channel: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"entity_id": str(entity_id)}
        if channel:
            query["channel"] = channel
        rows = list(self._db.channel_messages.find(query, {"_id": 0}).limit(limit * 3))
        rows.sort(key=lambda r: r.get("created_at") or datetime.min)
        return rows[-limit:]

    def list_recent_threads(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Latest message per entity for ops inbox."""
        pipeline = [
            {"$sort": {"created_at": -1}},
            {
                "$group": {
                    "_id": "$thread_id",
                    "entity_id": {"$first": "$entity_id"},
                    "entity_type": {"$first": "$entity_type"},
                    "channel": {"$first": "$channel"},
                    "last_body": {"$first": "$body"},
                    "last_direction": {"$first": "$direction"},
                    "last_at": {"$first": "$created_at"},
                }
            },
            {"$limit": limit},
        ]
        return list(self._db.channel_messages.aggregate(pipeline))
