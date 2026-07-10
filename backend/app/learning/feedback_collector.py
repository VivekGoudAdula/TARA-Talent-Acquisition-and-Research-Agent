"""Aggregate Layer 5 outcomes into feedback signals for Layer 6."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.db.mongo import MongoDatabase
from app.learning.outcome_labels import build_label_record
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FeedbackCollector:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def collect_entity_outcomes(self, *, limit: int = 5000) -> list[dict[str, Any]]:
        """Build one outcome record per entity from responses, journeys, and handoffs."""
        responses = list(self._db.lead_responses.find({}, {"_id": 0}))
        journeys = {
            doc["entity_id"]: doc
            for doc in self._db.onboarding_journeys.find({}, {"_id": 0})
        }
        handoffs_by_entity: dict[str, dict[str, Any]] = {}
        for doc in self._db.rm_handoffs.find({}, {"_id": 0}):
            eid = doc.get("entity_id")
            if not eid:
                continue
            existing = handoffs_by_entity.get(eid)
            if existing is None or (doc.get("created_at") or "") > (existing.get("created_at") or ""):
                handoffs_by_entity[eid] = doc

        latest_response: dict[str, dict[str, Any]] = {}
        for resp in responses:
            eid = resp.get("entity_id")
            if not eid:
                continue
            prev = latest_response.get(eid)
            if prev is None or (resp.get("created_at") or "") >= (prev.get("created_at") or ""):
                latest_response[eid] = resp

        records: list[dict[str, Any]] = []
        for entity_id, resp in list(latest_response.items())[:limit]:
            journey = journeys.get(entity_id, {})
            handoff = handoffs_by_entity.get(entity_id, {})
            lead_id = self._resolve_lead_id(entity_id)
            record = build_label_record(
                entity_id=entity_id,
                entity_type=resp.get("entity_type") or journey.get("entity_type") or "External",
                lead_id=lead_id,
                response_type=resp.get("response_type"),
                journey_status=journey.get("status"),
                handoff_status=handoff.get("status"),
                channel=resp.get("channel") or journey.get("last_channel"),
            )
            if record:
                records.append(record)

        logger.info("Collected %d entity outcome records", len(records))
        return records

    def outcome_labels_by_lead_id(self, *, limit: int = 5000) -> dict[str, float]:
        """Map lead_id → conversion_label for model training."""
        labels: dict[str, float] = {}
        for record in self.collect_entity_outcomes(limit=limit):
            lead_id = record.get("lead_id")
            if lead_id:
                labels[str(lead_id)] = float(record["conversion_label"])
        return labels

    def channel_stats(self) -> list[dict[str, Any]]:
        """Per-channel outreach and response metrics."""
        outreach: dict[str, int] = defaultdict(int)
        for event in self._db.engagement_events.find({}, {"channel": 1, "status": 1}):
            channel = (event.get("channel") or "Unknown").strip()
            outreach[channel] += 1

        responses_by_channel: dict[str, list[str]] = defaultdict(list)
        for resp in self._db.lead_responses.find({}, {"channel": 1, "response_type": 1}):
            channel = (resp.get("channel") or "Unknown").strip()
            responses_by_channel[channel].append(resp.get("response_type") or "neutral")

        channels = sorted(set(outreach) | set(responses_by_channel))
        stats: list[dict[str, Any]] = []
        for channel in channels:
            types = responses_by_channel.get(channel, [])
            interested = sum(1 for t in types if t in ("interested", "apply", "callback_requested"))
            declined = sum(1 for t in types if t == "declined")
            response_count = len(types)
            outreach_count = outreach.get(channel, 0)
            stats.append(
                {
                    "channel": channel,
                    "outreach_count": outreach_count,
                    "response_count": response_count,
                    "interested_count": interested,
                    "declined_count": declined,
                    "conversion_rate": round(interested / response_count, 4) if response_count else None,
                    "response_rate": round(response_count / outreach_count, 4) if outreach_count else None,
                }
            )
        return stats

    def funnel_stats(self) -> dict[str, Any]:
        responses = list(self._db.lead_responses.find({}, {"response_type": 1}))
        journeys = list(self._db.onboarding_journeys.find({}, {"status": 1}))
        handoffs = list(self._db.rm_handoffs.find({}, {"status": 1}))

        counts: dict[str, int] = defaultdict(int)
        for resp in responses:
            counts[resp.get("response_type") or "neutral"] += 1

        kyc_nudges = sum(1 for j in journeys if j.get("status") == "kyc_nudge_sent")
        handoffs_created = len(handoffs)
        total = len(responses)
        interested = counts.get("interested", 0) + counts.get("apply", 0) + counts.get("callback_requested", 0)

        return {
            "total_responses": total,
            "interested": counts.get("interested", 0),
            "declined": counts.get("declined", 0),
            "callback_requested": counts.get("callback_requested", 0),
            "no_answer": counts.get("no_answer", 0),
            "handoffs_created": handoffs_created,
            "kyc_nudges_sent": kyc_nudges,
            "interest_rate": round(interested / total, 4) if total else None,
            "handoff_rate": round(handoffs_created / total, 4) if total else None,
        }

    def _resolve_lead_id(self, entity_id: str) -> str | None:
        if entity_id.startswith("phone:"):
            digits = entity_id.split(":", 1)[-1][-10:]
            lead = self._db.external_leads.find_one(
                {"phone_number": {"$regex": digits}},
                {"lead_id": 1},
            )
            return str(lead["lead_id"]) if lead and lead.get("lead_id") else None
        lead = self._db.external_leads.find_one({"lead_id": str(entity_id)}, {"lead_id": 1})
        if lead and lead.get("lead_id"):
            return str(lead["lead_id"])
        return str(entity_id) if len(entity_id) == 36 else None
