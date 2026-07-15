"""Build full voice-agent context for AI Callback sessions."""

from __future__ import annotations

from typing import Any

from app.db.mongo import MongoDatabase
from app.engagement.banking_copy import eligibility_label, humanize_reasons, professional_insight
from app.engagement.export_service import EngagementExportService
from app.schemas.engagement import EngagementLeadRecord
from app.schemas.voice_session import VoiceAgentContext

_AGENT_RULES = (
    "Use only the provided context. "
    "No repeated questions. "
    "Short replies — one sentence max. "
    "Do not ask for name, phone, product, or eligibility already in context. "
    "Answer product questions briefly from context. "
    "Transfer to Relationship Manager if customer shows interest. "
    "Log call outcome when the call ends."
)


class VoiceContextService:
    """Loads ML + profile data into a voice-agent-ready context blob."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._export = EngagementExportService(db)

    def load_context(
        self,
        *,
        entity_id: str,
        entity_type: str,
        phone: str,
        name: str | None = None,
        campaign: str | None = None,
        source_channel: str | None = None,
    ) -> VoiceAgentContext:
        record = self._export.build_record_for_entity(entity_id, entity_type)
        lead_meta = self._load_entity_meta(entity_id, entity_type)

        if record:
            resolved_name = name or record.name
            resolved_phone = phone or record.phone
            product = record.recommended_product
            reasons = list(record.reason_codes[:3])
            confidence = record.conversion_probability
            eligibility = eligibility_label(confidence)
            lang = lead_meta.get("preferred_language") or "English"
            resolved_campaign = campaign or lead_meta.get("campaign")
            talking_points = record.talking_points or professional_insight(record)
        else:
            resolved_name = name or "Customer"
            resolved_phone = phone
            product = "Personal Loan"
            reasons = []
            confidence = None
            eligibility = eligibility_label(None)
            lang = lead_meta.get("preferred_language") or "English"
            resolved_campaign = campaign or lead_meta.get("campaign")
            talking_points = None

        if not reasons:
            reasons = [humanize_reasons([])]

        callback_note = ""
        if source_channel:
            callback_note = f" They triggered this via {source_channel}."

        instructions = (
            f"{_AGENT_RULES}"
            f"{callback_note} "
            f"Speak in {lang}. "
            f"Recommended product: {product or 'a suitable lending product'}. "
            f"Top reasons: {', '.join(reasons[:3])}."
        )

        return VoiceAgentContext(
            name=resolved_name,
            lang=lang,
            campaign=resolved_campaign,
            intent="callback",
            product=product,
            top3_reasons=reasons[:3],
            confidence=confidence,
            eligibility=eligibility,
            customer_id=entity_id,
            entity_type=entity_type,
            phone=resolved_phone,
            repayment_capacity=record.repayment_capacity if record else None,
            talking_points=talking_points,
            agent_instructions=instructions.strip(),
        )

    def _load_entity_meta(self, entity_id: str, entity_type: str) -> dict[str, Any]:
        if entity_type.lower() == "external":
            if entity_id.startswith("phone:"):
                digits = entity_id.split(":", 1)[-1][-10:]
                doc = self._db.external_leads.find_one({"phone_number": {"$regex": digits}})
            else:
                doc = self._db.external_leads.find_one({"lead_id": str(entity_id)})
            if doc:
                return {
                    "preferred_language": doc.get("preferred_language"),
                    "campaign": doc.get("campaign"),
                }
            return {}

        doc = self._db.customers.find_one({"customer_id": str(entity_id)})
        if doc:
            return {
                "preferred_language": doc.get("preferred_language"),
                "campaign": None,
            }
        return {}
