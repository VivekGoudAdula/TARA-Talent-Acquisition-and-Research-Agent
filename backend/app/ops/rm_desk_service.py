"""RM Operations Desk — simulated CRM workstation (no external bank APIs)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SLA_HOURS = {"high": 4, "normal": 24, "low": 48}


class RmDeskService:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def dashboard(self) -> dict[str, Any]:
        handoffs = list(self._db.rm_handoffs.find({}, {"_id": 0}))
        now = datetime.utcnow()
        pending = [h for h in handoffs if h.get("status") == "pending"]
        in_progress = [h for h in handoffs if h.get("status") == "in_progress"]
        overdue = [
            h for h in pending + in_progress
            if self._is_overdue(h, now)
        ]
        return {
            "total_handoffs": len(handoffs),
            "pending": len(pending),
            "in_progress": len(in_progress),
            "completed": sum(1 for h in handoffs if h.get("status") in ("completed", "converted")),
            "overdue_sla": len(overdue),
            "avg_wait_hours": self._avg_wait_hours(pending, now),
        }

    def list_queue(
        self,
        *,
        status: str | None = None,
        assigned_rm: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        if assigned_rm:
            query["assigned_rm"] = assigned_rm
        rows = list(self._db.rm_handoffs.find(query, {"_id": 0}))
        now = datetime.utcnow()
        for row in rows:
            row["sla_deadline"] = self._sla_deadline(row)
            row["sla_breached"] = self._is_overdue(row, now)
            row["assigned_rm_name"] = row.get("assigned_rm")
            row["status_notes"] = row.get("rm_notes")
        rows.sort(key=lambda r: (r.get("priority") != "high", r.get("created_at") or ""))
        return rows[:limit]

    def assign(self, handoff_id: str, rm_name: str, rm_id: str | None = None) -> dict[str, Any] | None:
        now = datetime.utcnow()
        existing = self._db.rm_handoffs.find_one({"handoff_id": handoff_id})
        if not existing:
            return None
        self._db.rm_handoffs.update_one(
            {"handoff_id": handoff_id},
            {
                "$set": {
                    "assigned_rm": rm_name,
                    "assigned_rm_id": rm_id or str(uuid4())[:8],
                    "status": "in_progress",
                    "assigned_at": now,
                    "updated_at": now,
                }
            },
        )
        self._log_activity(handoff_id, "assigned", f"Assigned to {rm_name}")
        return self._strip_id(self._db.rm_handoffs.find_one({"handoff_id": handoff_id}))

    def update_status(
        self,
        handoff_id: str,
        status: str,
        *,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        now = datetime.utcnow()
        existing = self._db.rm_handoffs.find_one({"handoff_id": handoff_id})
        if not existing:
            return None
        update: dict[str, Any] = {"status": status, "updated_at": now}
        if notes:
            update["rm_notes"] = notes
        if status in ("completed", "converted", "lost", "declined"):
            update["resolved_at"] = now
        self._db.rm_handoffs.update_one({"handoff_id": handoff_id}, {"$set": update})
        result = self._db.rm_handoffs.find_one({"handoff_id": handoff_id})
        if result:
            self._log_activity(handoff_id, status, notes or status)
            if status == "converted":
                self._ingest_conversion_outcome(result)
        return self._strip_id(result)

    def list_rms(self) -> list[dict[str, Any]]:
        return [
            {"rm_id": "RM001", "name": "Priya Sharma", "branch": "Mumbai Central", "active_leads": 0},
            {"rm_id": "RM002", "name": "Arjun Mehta", "branch": "Delhi Connaught Place", "active_leads": 0},
            {"rm_id": "RM003", "name": "Sneha Reddy", "branch": "Bangalore MG Road", "active_leads": 0},
        ]

    def _sla_deadline(self, handoff: dict) -> datetime | None:
        created = handoff.get("created_at")
        if not created:
            return None
        hours = SLA_HOURS.get(handoff.get("priority", "normal"), 24)
        return created + timedelta(hours=hours)

    def _is_overdue(self, handoff: dict, now: datetime) -> bool:
        deadline = self._sla_deadline(handoff)
        if not deadline:
            return False
        return handoff.get("status") in ("pending", "in_progress") and now > deadline

    @staticmethod
    def _avg_wait_hours(pending: list[dict], now: datetime) -> float | None:
        if not pending:
            return None
        total = 0.0
        for h in pending:
            created = h.get("created_at")
            if created:
                total += (now - created).total_seconds() / 3600
        return round(total / len(pending), 1)

    def _log_activity(self, handoff_id: str, action: str, detail: str) -> None:
        self._db.rm_handoff_activity.insert_one(
            {
                "activity_id": str(uuid4()),
                "handoff_id": handoff_id,
                "action": action,
                "detail": detail,
                "created_at": datetime.utcnow(),
            }
        )

    def _ingest_conversion_outcome(self, handoff: dict) -> None:
        try:
            from app.learning.service import LearningService
            from app.schemas.learning import IngestOutcomeRequest

            LearningService(self._db).ingest_outcome(
                IngestOutcomeRequest(
                    entity_id=handoff["entity_id"],
                    entity_type=handoff.get("entity_type", "External"),
                    response_type="interested",
                    journey_status="handoff_pending",
                )
            )
        except Exception as exc:
            logger.debug("RM conversion feedback skipped: %s", exc)

    @staticmethod
    def _strip_id(doc: dict | None) -> dict | None:
        if not doc:
            return None
        doc.pop("_id", None)
        return doc
