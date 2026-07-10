"""Simulated UPI / YONO digital activation — no external bank APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

YONO_STEPS = [
    {"step": "app_download", "label": "Download IDBI Mobile / YONO app"},
    {"step": "mobile_verify", "label": "Verify mobile number"},
    {"step": "upi_id_create", "label": "Create UPI ID"},
    {"step": "yono_login", "label": "First YONO login"},
    {"step": "product_activate", "label": "Activate lending product"},
]


class ActivationRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def start(self, *, entity_id: str, entity_type: str, phone: str, product: str | None) -> str:
        activation_id = str(uuid4())
        now = datetime.utcnow()
        steps = [
            {**s, "status": "pending", "completed_at": None} for s in YONO_STEPS
        ]
        self._db.activation_journeys.insert_one(
            {
                "activation_id": activation_id,
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "phone": phone,
                "product": product or "Personal Loan",
                "channel": "YONO_UPI",
                "status": "in_progress",
                "steps": steps,
                "deep_link": f"idbi://yono/activate?ref={activation_id}",
                "created_at": now,
                "updated_at": now,
                "completed_at": None,
            }
        )
        return activation_id

    def complete_step(self, activation_id: str, step: str) -> dict[str, Any] | None:
        doc = self._db.activation_journeys.find_one({"activation_id": activation_id})
        if not doc:
            return None
        now = datetime.utcnow()
        steps = doc.get("steps", [])
        for s in steps:
            if s.get("step") == step:
                s["status"] = "completed"
                s["completed_at"] = now
        all_done = all(s.get("status") == "completed" for s in steps)
        status = "completed" if all_done else "in_progress"
        update: dict[str, Any] = {"steps": steps, "status": status, "updated_at": now}
        if all_done:
            update["completed_at"] = now
        self._db.activation_journeys.update_one(
            {"activation_id": activation_id}, {"$set": update}
        )
        return self._db.activation_journeys.find_one(
            {"activation_id": activation_id}, {"_id": 0}
        )

    def get_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        rows = list(self._db.activation_journeys.find({"entity_id": str(entity_id)}, {"_id": 0}))
        rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return rows[0] if rows else None

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = list(self._db.activation_journeys.find({}, {"_id": 0}))
        rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return rows[:limit]
