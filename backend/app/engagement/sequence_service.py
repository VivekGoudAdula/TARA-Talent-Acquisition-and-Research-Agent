"""Multi-touch engagement sequencing with channel fail-over."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase
from app.engagement.orchestrator import EngagementOrchestrator
from app.engagement.export_service import EngagementExportService
from app.schemas.engagement import EngagementLeadRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_TOUCH_PLAN = [
    {"day": 0, "channel": "WhatsApp", "purpose": "initial_offer"},
    {"day": 2, "channel": "SMS", "purpose": "reminder"},
    {"day": 5, "channel": "Email", "purpose": "detailed_offer"},
    {"day": 7, "channel": "Voice", "purpose": "callback"},
]

FAILOVER_MAP = {
    "WhatsApp": "SMS",
    "SMS": "Email",
    "Email": "SMS",
}


class EngagementSequenceService:
    """Plans and executes multi-touch outreach cadences per lead."""

    def __init__(self, db: MongoDatabase, orchestrator: EngagementOrchestrator | None = None) -> None:
        self._db = db
        export = EngagementExportService(db)
        from app.engagement.repository import EngagementRepository

        self._orchestrator = orchestrator or EngagementOrchestrator(
            export, EngagementRepository(db)
        )

    def create_sequence(
        self,
        entity_id: str,
        *,
        entity_type: str = "External",
        touch_plan: list[dict[str, Any]] | None = None,
    ) -> str:
        plan = touch_plan or DEFAULT_TOUCH_PLAN
        sequence_id = str(uuid4())
        now = datetime.utcnow()
        touches = []
        for step in plan:
            due = now + timedelta(days=int(step.get("day", 0)))
            touches.append(
                {
                    "touch_id": str(uuid4()),
                    "day_offset": step.get("day", 0),
                    "channel": step["channel"],
                    "purpose": step.get("purpose", "outreach"),
                    "status": "scheduled",
                    "due_at": due,
                    "sent_at": None,
                    "result": None,
                }
            )
        self._db.engagement_sequences.insert_one(
            {
                "sequence_id": sequence_id,
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "status": "active",
                "touches": touches,
                "created_at": now,
                "updated_at": now,
            }
        )
        return sequence_id

    def process_due_touches(self, *, dry_run: bool = False, limit: int = 50) -> dict[str, int]:
        now = datetime.utcnow()
        processed = succeeded = failed = 0
        sequences = list(self._db.engagement_sequences.find({"status": "active"}))
        for seq in sequences:
            if processed >= limit:
                break
            entity_id = seq["entity_id"]
            record = self._load_record(entity_id, seq.get("entity_type", "External"))
            if not record:
                continue
            updated = False
            for touch in seq.get("touches", []):
                if touch.get("status") != "scheduled":
                    continue
                due = touch.get("due_at")
                if due and due > now:
                    continue
                processed += 1
                channel = touch["channel"]
                result = self._orchestrator.send_one(
                    record,
                    channel=channel,
                    dry_run=dry_run,
                )
                if not result.success and channel in FAILOVER_MAP:
                    fallback = FAILOVER_MAP[channel]
                    result = self._orchestrator.send_one(record, channel=fallback, dry_run=dry_run)
                    touch["failover_channel"] = fallback
                touch["status"] = "sent" if result.success else "failed"
                touch["sent_at"] = now
                touch["result"] = {
                    "success": result.success,
                    "channel": result.channel,
                    "status": result.status,
                    "error": result.error,
                }
                if result.success:
                    succeeded += 1
                else:
                    failed += 1
                updated = True
                if processed >= limit:
                    break
            if updated:
                all_done = all(t.get("status") != "scheduled" for t in seq.get("touches", []))
                self._db.engagement_sequences.update_one(
                    {"sequence_id": seq["sequence_id"]},
                    {
                        "$set": {
                            "touches": seq["touches"],
                            "status": "completed" if all_done else "active",
                            "updated_at": now,
                        }
                    },
                )
        return {"processed": processed, "succeeded": succeeded, "failed": failed}

    def list_sequences(self, entity_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if entity_id:
            query["entity_id"] = entity_id
        rows = list(self._db.engagement_sequences.find(query, {"_id": 0}))
        rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return rows[:limit]

    def _load_record(self, entity_id: str, entity_type: str) -> EngagementLeadRecord | None:
        export = EngagementExportService(self._db)
        record = export.build_record_for_entity(entity_id, entity_type)
        if record:
            return record
        return EngagementLeadRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            phone="",
            name="Customer",
            recommended_product="Personal Loan",
            consent=True,
        )
