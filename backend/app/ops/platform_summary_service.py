"""MongoDB platform overview for the admin UI."""

from __future__ import annotations

from typing import Any

from app.api.ui_adapters import adapt_pipeline_status, adapt_platform_counts, adapt_recent_lead_row
from app.db.mongo import MongoDatabase

DEMO_EMAIL = "krishnajai008@gmail.com"
DEMO_PHONE = "+918897371942"
DEMO_PHONE_DISPLAY = "8897371942"
_RECENT_LEAD_LIMIT = 20


class PlatformSummaryService:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def get_summary(self) -> dict[str, Any]:
        counts = adapt_platform_counts(self._db)

        recent_leads = self._list_external_leads(limit=_RECENT_LEAD_LIMIT)
        internal_customers = self._list_internal_customers(limit=_RECENT_LEAD_LIMIT)

        runs = list(self._db.pipeline_runs.find({}, {"_id": 0}).limit(20))
        runs.sort(key=lambda d: d.get("started_at") or "", reverse=True)

        return {
            "database": "mongodb",
            "demo_contact": {
                "email": DEMO_EMAIL,
                "phone": DEMO_PHONE_DISPLAY,
                "phone_e164": DEMO_PHONE,
            },
            "counts": counts,
            "internal_customers": internal_customers,
            "external_leads": recent_leads,
            "recent_leads": recent_leads,
            "recent_pipeline_runs": runs,
            "pipeline_status": adapt_pipeline_status(counts, runs),
            "layers": self._layer_status(counts),
        }

    @staticmethod
    def _format_phone(phone: str | None) -> str:
        if not phone:
            return ""
        digits = "".join(c for c in phone if c.isdigit())
        return digits[-10:] if len(digits) >= 10 else phone

    def _list_internal_customers(self, limit: int = 20) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for cust in self._db.customers.find({}, {"_id": 0}).limit(limit):
            first = cust.get("first_name") or ""
            last = cust.get("last_name") or ""
            cid = str(cust.get("customer_id", ""))
            rows.append(
                {
                    "entity_id": cid,
                    "customer_id": cid,
                    "name": f"{first} {last}".strip(),
                    "phone": self._format_phone(cust.get("phone_number")),
                    "email": cust.get("email"),
                    "city": cust.get("city"),
                    "customer_type": "Internal",
                }
            )
        return rows

    def _list_external_leads(self, limit: int = _RECENT_LEAD_LIMIT) -> list[dict[str, Any]]:
        leads = list(self._db.external_leads.find({}, {"_id": 0}).limit(limit))
        lead_ids = [str(lead.get("lead_id")) for lead in leads if lead.get("lead_id")]
        conv_dict: dict[str, Any] = {}
        if lead_ids:
            conv_predictions = self._db.conversion_predictions.find(
                {"lead_id": {"$in": lead_ids}},
                {"lead_id": 1, "conversion_probability": 1, "_id": 0},
            )
            conv_dict = {
                str(c["lead_id"]): c.get("conversion_probability")
                for c in conv_predictions
                if c.get("lead_id")
            }

        rows: list[dict[str, Any]] = []
        for lead in leads:
            eid = str(lead.get("lead_id", ""))
            rows.append(adapt_recent_lead_row(lead, conv_dict.get(eid)))
        return rows

    @staticmethod
    def _layer_status(counts: dict[str, int]) -> list[dict[str, Any]]:
        return [
            {
                "layer": "L1 — Data",
                "status": "ok" if counts["external_leads"] > 0 else "empty",
                "detail": f"{counts['internal_customers']} internal · {counts['external_leads']} external leads",
            },
            {
                "layer": "L2 — Enrichment",
                "status": "ok" if counts["enriched_profiles"] > 0 else "pending",
                "detail": f"{counts['enriched_profiles']} enriched profiles",
            },
            {
                "layer": "L3 — Scoring",
                "status": "ok" if counts["conversion_scores"] > 0 else "pending",
                "detail": f"{counts['conversion_scores']} conversion scores",
            },
            {
                "layer": "L4 — Engagement",
                "status": "ok" if counts["engagement_events"] > 0 else "pending",
                "detail": f"{counts['engagement_events']} events",
            },
            {
                "layer": "L5 — Onboarding",
                "status": "ok" if counts["onboarding_journeys"] > 0 else "pending",
                "detail": f"{counts['onboarding_journeys']} journeys · {counts['rm_handoffs']} handoffs",
            },
            {
                "layer": "L6 — Learning",
                "status": "ok" if counts["pipeline_runs"] > 0 else "pending",
                "detail": f"{counts['pipeline_runs']} pipeline runs logged",
            },
        ]
