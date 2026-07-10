"""Engagement event persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.db.mongo import MongoDatabase
from app.engagement.channels.base import ChannelDeliveryResult
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class EngagementRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def save_event(
        self,
        *,
        entity_id: str,
        entity_type: str,
        channel: str,
        result: ChannelDeliveryResult,
        campaign_id: str | None = None,
        message_preview: str | None = None,
    ) -> str:
        event_id = str(uuid4())
        doc = {
            "event_id": event_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "channel": channel,
            "recipient": result.recipient,
            "status": result.status,
            "success": result.success,
            "provider_sid": result.provider_sid,
            "error": result.error,
            "campaign_id": campaign_id,
            "message_preview": message_preview,
            "metadata": result.metadata,
            "created_at": datetime.utcnow(),
        }
        self._db.engagement_events.insert_one(doc)
        logger.debug("Saved engagement event event_id=%s channel=%s", event_id, channel)
        return event_id

    def save_voice_call_outcome(
        self,
        *,
        call_sid: str,
        entity_id: str,
        entity_type: str,
        recipient: str,
        call_status: str,
        duration_seconds: int,
        agent_id: str,
        direction: str = "outbound",
        intent: str | None = None,
        transcript_preview: str | None = None,
        campaign_lead_id: int | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Record a completed voice call from bank/bank back into engagement_events."""
        terminal_ok = (call_status or "").lower() in (
            "completed",
            "answered",
            "in-progress",
        )
        event_id = str(uuid4())
        doc = {
            "event_id": event_id,
            "entity_id": str(entity_id),
            "entity_type": entity_type,
            "channel": "Voice",
            "recipient": recipient,
            "status": call_status,
            "success": terminal_ok,
            "provider_sid": call_sid,
            "error": None if terminal_ok else call_status,
            "campaign_id": None,
            "message_preview": (transcript_preview or "")[:200] or None,
            "metadata": {
                "source": "bank_voice_runtime",
                "agent_id": agent_id,
                "direction": direction,
                "duration_seconds": duration_seconds,
                "intent": intent,
                "campaign_lead_id": campaign_lead_id,
                **(metadata or {}),
            },
            "created_at": datetime.utcnow(),
        }
        self._db.engagement_events.insert_one(doc)
        logger.info(
            "Voice call outcome saved event_id=%s entity_id=%s status=%s",
            event_id,
            entity_id,
            call_status,
        )
        return event_id

    def count_by_channel(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for doc in self._db.engagement_events.find({}, {"channel": 1}):
            ch = doc.get("channel", "unknown")
            counts[ch] = counts.get(ch, 0) + 1
        return counts

    def count_all(self) -> int:
        return self._db.engagement_events.count_documents({})

    def get_by_entity(self, entity_id: UUID | str) -> list[dict]:
        return list(
            self._db.engagement_events.find({"entity_id": str(entity_id)}).limit(50)
        )
