"""Mongo persistence for Layer 5 onboarding."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class OnboardingRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def save_lead_response(
        self,
        *,
        entity_id: str,
        entity_type: str,
        channel: str,
        response_type: str,
        raw_text: str | None = None,
        button_payload: str | None = None,
        call_sid: str | None = None,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        response_id = str(uuid4())
        doc = {
            "response_id": response_id,
            "entity_id": str(entity_id),
            "entity_type": entity_type,
            "channel": channel,
            "response_type": response_type,
            "raw_text": raw_text,
            "button_payload": button_payload,
            "call_sid": call_sid,
            "intent": intent,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        self._db.lead_responses.insert_one(doc)
        return response_id

    def upsert_journey(
        self,
        *,
        entity_id: str,
        entity_type: str,
        status: str,
        kyc_readiness: str,
        kyc_missing_items: list[str],
        last_response_type: str,
        last_channel: str,
        product: str | None = None,
        handoff_id: str | None = None,
        increment_nudge: bool = False,
    ) -> str:
        now = datetime.utcnow()
        existing = self._db.onboarding_journeys.find_one({"entity_id": str(entity_id)})
        if existing:
            update: dict[str, Any] = {
                "status": status,
                "kyc_readiness": kyc_readiness,
                "kyc_missing_items": kyc_missing_items,
                "last_response_type": last_response_type,
                "last_channel": last_channel,
                "updated_at": now,
            }
            if product:
                update["product"] = product
            if handoff_id:
                update["handoff_id"] = handoff_id
            if increment_nudge:
                update["nudge_count"] = int(existing.get("nudge_count") or 0) + 1
            self._db.onboarding_journeys.update_one(
                {"entity_id": str(entity_id)},
                {"$set": update},
            )
            return str(existing["journey_id"])

        journey_id = str(uuid4())
        self._db.onboarding_journeys.insert_one(
            {
                "journey_id": journey_id,
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "status": status,
                "kyc_readiness": kyc_readiness,
                "kyc_missing_items": kyc_missing_items,
                "last_response_type": last_response_type,
                "last_channel": last_channel,
                "product": product,
                "handoff_id": handoff_id,
                "nudge_count": 1 if increment_nudge else 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        return journey_id

    def create_handoff(
        self,
        *,
        entity_id: str,
        entity_type: str,
        customer_name: str,
        phone: str,
        product: str | None,
        priority: str,
        reason: str,
        source_channel: str,
        talking_points: str | None = None,
        call_sid: str | None = None,
    ) -> str:
        handoff_id = str(uuid4())
        self._db.rm_handoffs.insert_one(
            {
                "handoff_id": handoff_id,
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "customer_name": customer_name,
                "phone": phone,
                "product": product,
                "priority": priority,
                "status": "pending",
                "reason": reason,
                "source_channel": source_channel,
                "talking_points": talking_points,
                "call_sid": call_sid,
                "created_at": datetime.utcnow(),
                "resolved_at": None,
            }
        )
        logger.info("RM handoff created handoff_id=%s entity_id=%s", handoff_id, entity_id)
        return handoff_id

    def get_journey(self, entity_id: str) -> dict[str, Any] | None:
        return self._db.onboarding_journeys.find_one({"entity_id": str(entity_id)})

    def list_responses(self, entity_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = list(
            self._db.lead_responses.find({"entity_id": str(entity_id)}).limit(limit * 3)
        )
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[:limit]

    def list_handoffs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        rows = list(self._db.rm_handoffs.find(query).limit(limit * 3))
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[:limit]

    def list_journeys(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = list(self._db.onboarding_journeys.find().limit(limit * 3))
        rows.sort(key=lambda r: r.get("updated_at") or r.get("created_at") or "", reverse=True)
        return rows[:limit]
