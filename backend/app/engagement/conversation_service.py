"""Inbound/outbound conversation handling for WhatsApp, SMS, and Email."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import get_settings
from app.db.mongo import MongoDatabase
from app.engagement.conversation_reply import build_agent_reply
from app.engagement.conversation_repository import ConversationRepository
from app.engagement.export_service import EngagementExportService
from app.events import broadcast_event
from app.onboarding.orchestrator import OnboardingOrchestrator
from app.onboarding.response_parser import classify_response
from app.schemas.onboarding import LeadResponseCaptureRequest
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _serialize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(out.get("created_at"), datetime):
        out["created_at"] = out["created_at"].isoformat()
    return out


class ConversationService:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._repo = ConversationRepository(db)
        self._export = EngagementExportService(db)
        self._onboarding = OnboardingOrchestrator(db)
        self._settings = get_settings()

    def resolve_entity(
        self,
        *,
        phone: str | None = None,
        email: str | None = None,
        entity_id: str | None = None,
        entity_type: str | None = None,
    ) -> tuple[str, str]:
        if entity_id and entity_id != "unknown":
            et = (entity_type or "External").strip().title()
            return str(entity_id), et

        digits = "".join(c for c in (phone or "") if c.isdigit())[-10:]
        if len(digits) >= 10:
            lead = self._db.external_leads.find_one(
                {"phone_number": {"$regex": digits}}
            )
            if lead:
                return str(lead.get("lead_id")), "External"
            cust = self._db.customers.find_one(
                {"phone_number": {"$regex": digits}}
            )
            if cust:
                return str(cust.get("customer_id")), "Internal"
            return f"phone:{digits}", "External"

        email_norm = (email or "").strip().lower()
        if email_norm:
            lead = self._db.external_leads.find_one(
                {"email": {"$regex": f"^{email_norm}$", "$options": "i"}}
            )
            if lead:
                return str(lead.get("lead_id")), "External"
            cust = self._db.customers.find_one(
                {"email": {"$regex": f"^{email_norm}$", "$options": "i"}}
            )
            if cust:
                return str(cust.get("customer_id")), "Internal"

        return entity_id or "unknown", entity_type or "External"

    def record_outbound(
        self,
        *,
        entity_id: str,
        entity_type: str,
        channel: str,
        body: str,
        provider_sid: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        doc = self._repo.append_message(
            entity_id=entity_id,
            entity_type=entity_type,
            channel=channel,
            direction="outbound",
            role="agent",
            body=body,
            provider_sid=provider_sid,
            metadata=metadata,
        )
        payload = _serialize_doc(doc)
        broadcast_event("conversation_message", payload)
        return payload

    def process_inbound(
        self,
        *,
        channel: str,
        body: str,
        phone: str | None = None,
        email: str | None = None,
        entity_id: str | None = None,
        entity_type: str = "External",
        button_payload: str | None = None,
        provider_sid: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        text = (body or button_payload or "").strip()
        if not text:
            return {"status": "ignored", "reason": "empty"}

        eid, etype = self.resolve_entity(
            phone=phone,
            email=email,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        response_type = classify_response(
            raw_text=text,
            button_payload=button_payload,
        )

        inbound_doc = self._repo.append_message(
            entity_id=eid,
            entity_type=etype,
            channel=channel,
            direction="inbound",
            role="customer",
            body=text,
            response_type=response_type,
            provider_sid=provider_sid,
            metadata={"phone": phone, "email": email, "button_payload": button_payload},
        )
        inbound_payload = _serialize_doc(inbound_doc)
        broadcast_event("conversation_message", inbound_payload)

        onboarding_result = None
        if not dry_run:
            onboarding_result = self._onboarding.process_lead_response(
                LeadResponseCaptureRequest(
                    entity_id=eid,
                    entity_type=etype,
                    channel=channel,
                    response_type=response_type,
                    raw_text=text,
                    button_payload=button_payload,
                    phone=phone,
                    email=email,
                )
            )

        record = self._export.build_record_for_entity(eid, etype)
        reply = build_agent_reply(
            customer_text=text,
            response_type=response_type,
            record=record,
            onboarding=onboarding_result,
            settings=self._settings,
        )

        outbound_doc = self._repo.append_message(
            entity_id=eid,
            entity_type=etype,
            channel=channel,
            direction="outbound",
            role="agent",
            body=reply,
            response_type=response_type,
            metadata={"auto_reply": True},
        )
        outbound_payload = _serialize_doc(outbound_doc)
        broadcast_event("conversation_message", outbound_payload)

        return {
            "status": "processed",
            "entity_id": eid,
            "entity_type": etype,
            "channel": channel,
            "response_type": response_type,
            "reply": reply,
            "inbound": inbound_payload,
            "outbound": outbound_payload,
            "next_action": onboarding_result.next_action if onboarding_result else None,
        }

    def sync_turn(
        self,
        *,
        channel: str,
        phone: str | None = None,
        email: str | None = None,
        customer_body: str,
        agent_body: str | None = None,
        entity_id: str | None = None,
        entity_type: str | None = None,
        provider_sid: str | None = None,
    ) -> dict[str, Any]:
        """Record a customer message + optional agent reply (e.g. from bank WhatsApp webhook)."""
        eid, etype = self.resolve_entity(
            phone=phone,
            email=email,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        response_type = classify_response(raw_text=customer_body)
        inbound_doc = self._repo.append_message(
            entity_id=eid,
            entity_type=etype,
            channel=channel,
            direction="inbound",
            role="customer",
            body=customer_body,
            response_type=response_type,
            provider_sid=provider_sid,
        )
        broadcast_event("conversation_message", _serialize_doc(inbound_doc))
        outbound_payload = None
        if agent_body:
            outbound_doc = self._repo.append_message(
                entity_id=eid,
                entity_type=etype,
                channel=channel,
                direction="outbound",
                role="agent",
                body=agent_body,
                metadata={"synced_from_bank": True},
            )
            outbound_payload = _serialize_doc(outbound_doc)
            broadcast_event("conversation_message", outbound_payload)
        return {
            "entity_id": eid,
            "entity_type": etype,
            "inbound": _serialize_doc(inbound_doc),
            "outbound": outbound_payload,
        }

    def get_thread(
        self,
        entity_id: str,
        *,
        channel: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        messages = [
            _serialize_doc(m)
            for m in self._repo.list_messages(entity_id, channel=channel, limit=limit)
        ]
        entity_type = messages[-1]["entity_type"] if messages else "External"
        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "channel": channel,
            "messages": messages,
            "total": len(messages),
        }

    def list_recent_inbox(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._repo.list_recent_threads(limit=limit)
