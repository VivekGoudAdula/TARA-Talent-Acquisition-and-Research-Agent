"""CRM customer 360 view for frontend ops desk (no external CRM API)."""

from __future__ import annotations

from typing import Any

from app.api.ui_adapters import adapt_crm_internal_row
from app.db.mongo import MongoDatabase
from app.engagement.export_service import EngagementExportService


class CrmCustomerService:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._export = EngagementExportService(db)

    def search_customers(
        self,
        *,
        query: str = "",
        limit: int = 500,
        customer_type: str = "all",
    ) -> list[dict[str, Any]]:
        """List customers. type=all returns every internal + external record."""
        results: list[dict[str, Any]] = []
        q = query.strip().lower()
        kind = (customer_type or "all").strip().lower()

        if kind in ("all", "internal"):
            profiles_by_customer = {
                str(doc.get("customer_id")): doc
                for doc in self._db.customer_360_profile.find({}, {"_id": 0})
                if doc.get("customer_id")
            }
            # Pre-fetch ML outputs keyed by profile_id for O(1) lookup per customer
            repayment_by_profile = {
                str(doc.get("profile_id")): doc
                for doc in self._db.repayment_predictions.find({}, {"_id": 0})
                if doc.get("profile_id")
            }
            product_by_profile = {
                str(doc.get("profile_id")): doc
                for doc in self._db.product_recommendations.find({}, {"_id": 0})
                if doc.get("profile_id")
            }
            for cust in self._db.customers.find({}, {"_id": 0}):
                cid = str(cust.get("customer_id", ""))
                profile = profiles_by_customer.get(cid)
                pid = str(profile.get("profile_id", "")) if profile else ""
                row = self._internal_summary(
                    cust,
                    profile,
                    repayment_by_profile.get(pid),
                    product_by_profile.get(pid),
                )
                if self._matches_query(q, row):
                    results.append(row)
            if kind == "internal":
                return results[:limit]

        if kind in ("all", "external"):
            leads = list(self._db.external_leads.find({}, {"_id": 0}))
            lead_ids = [str(l["lead_id"]) for l in leads if l.get("lead_id")]

            conversions = {
                str(c["lead_id"]): c
                for c in self._db.conversion_predictions.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "conversion_probability": 1, "_id": 0})
            }
            journeys = {
                str(j["entity_id"]): j
                for j in self._db.onboarding_journeys.find({"entity_id": {"$in": lead_ids}}, {"entity_id": 1, "status": 1, "_id": 0})
            }

            for lead in leads:
                eid = str(lead.get("lead_id", ""))
                row = self._lead_summary(lead, conversions.get(eid), journeys.get(eid))
                row["customer_type"] = "External"
                if self._matches_query(q, row):
                    results.append(row)
            if kind == "external":
                return results[:limit]

        return results[:limit]

    def get_customer_360(self, entity_id: str) -> dict[str, Any]:
        external = self._get_external_360(entity_id)
        if external.get("found"):
            return external
        internal = self._get_internal_360(entity_id)
        if internal.get("found"):
            return internal
        return {"entity_id": entity_id, "found": False}

    def _get_external_360(self, entity_id: str) -> dict[str, Any]:
        lead = self._db.external_leads.find_one({"lead_id": str(entity_id)}, {"_id": 0})
        if not lead and entity_id.startswith("phone:"):
            digits = entity_id.split(":", 1)[-1][-10:]
            lead = self._db.external_leads.find_one(
                {"phone_number": {"$regex": digits}}, {"_id": 0}
            )
        if not lead:
            return {"found": False}

        eid = str(lead.get("lead_id"))
        profile = self._db.external_customer_profile.find_one({"lead_id": eid}, {"_id": 0})
        conv = self._db.conversion_predictions.find_one({"lead_id": eid}, {"_id": 0})
        product = self._db.product_recommendations.find_one(
            {"entity_id": eid}, {"_id": 0}
        ) or self._db.product_recommendations.find_one(
            {"profile_id": profile.get("profile_id") if profile else None}, {"_id": 0}
        )
        journey = self._db.onboarding_journeys.find_one({"entity_id": eid}, {"_id": 0})
        if not journey:
            journey = self._db.onboarding_journeys.find_one(
                {
                    "entity_id": f"phone:{''.join(c for c in (lead.get('phone_number') or '') if c.isdigit())[-10:]}"
                },
                {"_id": 0},
            )
        responses = list(self._db.lead_responses.find({"entity_id": eid}, {"_id": 0}).limit(20))
        handoffs = list(self._db.rm_handoffs.find({"entity_id": eid}, {"_id": 0}))
        activation = self._db.activation_journeys.find_one({"entity_id": eid}, {"_id": 0})
        kyc_docs = list(self._db.kyc_documents.find({"entity_id": eid}, {"_id": 0}))
        events = list(self._db.engagement_events.find({"entity_id": eid}, {"_id": 0}).limit(20))
        sequences = list(self._db.engagement_sequences.find({"entity_id": eid}, {"_id": 0}))
        expl = self._db.explainability_reports.find_one({"customer_id": eid}, {"_id": 0})
        record = self._export.build_record_for_entity(eid, "External")
        from app.engagement.conversation_service import ConversationService

        conversations = ConversationService(self._db).get_thread(eid, limit=100)

        return {
            "found": True,
            "customer_type": "External",
            "entity_id": eid,
            "customer_id": eid,
            "lead_id": eid,
            "full_name": lead.get("full_name"),
            "lead": lead,
            "profile": profile,
            "engagement_record": record.model_dump() if record else None,
            "scoring": {"conversion": conv, "product": product},
            "explainability": expl,
            "onboarding": {
                "journey": journey,
                "responses": responses,
                "handoffs": handoffs,
                "activation": activation,
                "kyc_documents": kyc_docs,
            },
            "engagement": {"events": events, "sequences": sequences},
            "conversations": conversations,
        }

    def _get_internal_360(self, entity_id: str) -> dict[str, Any]:
        cust = self._db.customers.find_one({"customer_id": str(entity_id)}, {"_id": 0})
        if not cust:
            return {"found": False}

        cid = str(cust.get("customer_id"))
        profile = self._db.customer_360_profile.find_one({"customer_id": cid}, {"_id": 0})
        profile_id = str(profile.get("profile_id")) if profile else ""
        product = (
            self._db.product_recommendations.find_one({"profile_id": profile_id}, {"_id": 0})
            if profile_id
            else None
        )
        repayment = (
            self._db.repayment_predictions.find_one({"profile_id": profile_id}, {"_id": 0})
            if profile_id
            else None
        )
        expl = self._db.explainability_reports.find_one({"customer_id": cid}, {"_id": 0})
        events = list(self._db.engagement_events.find({"entity_id": cid}, {"_id": 0}).limit(20))
        record = self._export.build_record_for_entity(cid, "Internal")
        from app.engagement.conversation_service import ConversationService

        conversations = ConversationService(self._db).get_thread(cid, limit=100)
        first = (cust.get("first_name") or "").strip()
        last = (cust.get("last_name") or "").strip()
        full_name = f"{first} {last}".strip()

        return {
            "found": True,
            "customer_type": "Internal",
            "entity_id": cid,
            "customer_id": cid,
            "full_name": full_name,
            "customer": cust,
            "lead": {
                "full_name": f"{first} {last}".strip(),
                "phone_number": cust.get("phone_number"),
                "email": cust.get("email"),
                "city": cust.get("city"),
                "occupation": cust.get("occupation"),
            },
            "profile": profile,
            "engagement_record": record.model_dump() if record else None,
            "scoring": {"conversion": None, "product": product, "repayment": repayment},
            "explainability": expl,
            "onboarding": {"journey": None, "responses": [], "handoffs": [], "activation": None, "kyc_documents": []},
            "engagement": {"events": events, "sequences": []},
            "conversations": conversations,
        }

    def _internal_summary(
        self,
        cust: dict,
        profile: dict | None = None,
        repayment: dict | None = None,
        product: dict | None = None,
    ) -> dict[str, Any]:
        row = adapt_crm_internal_row(cust, profile)
        row["phone"] = self._format_phone(cust.get("phone_number"))

        # Fill gaps from ML prediction collections if the profile didn't provide them
        if repayment:
            if not row.get("repayment_label"):
                row["repayment_label"] = repayment.get("repayment_capacity")
            if not row.get("repayment_capacity"):
                row["repayment_capacity"] = row.get("repayment_label")
            # Derive credit_score from confidence if profile missed it
            if row.get("credit_score") is None:
                conf = repayment.get("confidence")
                if conf is not None:
                    try:
                        row["credit_score"] = int(round(float(conf) * 900))
                    except (TypeError, ValueError):
                        pass

        if product:
            row["recommended_product"] = (
                product.get("top_recommendation")
                or product.get("recommended_product")
                or product.get("top_product")
                or product.get("top_recommended_product")
            )

        if not row.get("recommended_product") and profile:
            row["recommended_product"] = profile.get("top_recommended_product")

        if not row.get("recommended_product"):
            from app.api.ui_adapters import _static_recommended_product

            row["recommended_product"] = _static_recommended_product(row, profile)

        return row

    def _lead_summary(self, lead: dict, conv: dict | None = None, journey: dict | None = None) -> dict[str, Any]:
        eid = str(lead.get("lead_id", ""))
        if conv is None:
            conv = self._db.conversion_predictions.find_one({"lead_id": eid}, {"conversion_probability": 1})
        if journey is None:
            journey = self._db.onboarding_journeys.find_one({"entity_id": eid}, {"status": 1})
        return {
            "entity_id": eid,
            "customer_id": eid,
            "lead_id": eid,
            "id": eid,
            "name": lead.get("full_name"),
            "full_name": lead.get("full_name"),
            "phone": self._format_phone(lead.get("phone_number")),
            "email": lead.get("email"),
            "city": lead.get("city"),
            "product": lead.get("product") or lead.get("campaign"),
            "conversion_probability": conv.get("conversion_probability") if conv else None,
            "journey_status": journey.get("status") if journey else None,
            "customer_type": "External",
        }

    @staticmethod
    def _format_phone(phone: str | None) -> str:
        if not phone:
            return ""
        digits = "".join(c for c in str(phone) if c.isdigit())
        return digits[-10:] if len(digits) >= 10 else str(phone)

    @staticmethod
    def _matches_query(q: str, row: dict[str, Any]) -> bool:
        if not q:
            return True
        haystack = " ".join(
            str(row.get(k) or "")
            for k in ("name", "phone", "email", "entity_id", "city", "product")
        ).lower()
        return q in haystack
