"""Layer 5 onboarding service facade."""

from __future__ import annotations

from app.db.mongo import MongoDatabase
from app.onboarding.orchestrator import OnboardingOrchestrator
from app.onboarding.repository import OnboardingRepository
from app.onboarding.response_parser import classify_response
from app.schemas.engagement import VoiceCallOutcomeRequest
from app.schemas.onboarding import (
    LeadResponseCaptureRequest,
    OnboardingJourneyResponse,
    OnboardingProcessResponse,
    OnboardingStatusResponse,
    RmHandoffResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _sanitize_mongo_doc(doc: dict) -> dict:
    """Make MongoDB documents JSON-safe for API responses."""
    from datetime import datetime

    out: dict = {}
    for key, value in doc.items():
        if key == "_id":
            continue
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


class OnboardingService:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._repo = OnboardingRepository(db)
        self._orchestrator = OnboardingOrchestrator(db)

    def process_lead_response(
        self, request: LeadResponseCaptureRequest
    ) -> OnboardingProcessResponse:
        result = self._orchestrator.process_lead_response(request)
        self._ingest_learning_feedback(request, result)
        return result

    def _ingest_learning_feedback(
        self,
        request: LeadResponseCaptureRequest,
        result: OnboardingProcessResponse,
    ) -> None:
        try:
            from app.learning.service import LearningService
            from app.schemas.learning import IngestOutcomeRequest

            LearningService(self._db).ingest_outcome(
                IngestOutcomeRequest(
                    entity_id=request.entity_id,
                    entity_type=request.entity_type,
                    response_type=result.response_type,
                    channel=request.channel,
                    journey_status=result.journey_status,
                )
            )
        except Exception as exc:
            logger.debug("Layer 6 feedback ingest skipped: %s", exc)

    def process_voice_outcome(
        self, outcome: VoiceCallOutcomeRequest
    ) -> OnboardingProcessResponse | None:
        try:
            result = self._orchestrator.process_voice_outcome(outcome)
            if result:
                from app.schemas.onboarding import LeadResponseCaptureRequest
                from app.schemas.learning import IngestOutcomeRequest

                self._ingest_learning_feedback(
                    LeadResponseCaptureRequest(
                        entity_id=outcome.entity_id or "",
                        entity_type=outcome.entity_type or "External",
                        channel="Voice",
                        response_type=result.response_type,
                        phone=outcome.recipient,
                    ),
                    result,
                )
            return result
        except Exception as exc:
            logger.warning("Onboarding voice processing failed: %s", exc)
            return None

    def process_whatsapp_inbound(self, form: dict[str, str]) -> OnboardingProcessResponse | None:
        """Parse Twilio WhatsApp inbound — delegates to conversation layer."""
        from app.engagement.conversation_service import ConversationService

        body = (form.get("Body") or "").strip()
        button = (form.get("ButtonPayload") or form.get("ButtonText") or "").strip()
        if not body and not button:
            return None

        result = ConversationService(self._db).process_inbound(
            channel="WhatsApp",
            body=body or button,
            phone=form.get("From") or form.get("WaId") or "",
            button_payload=button or None,
            provider_sid=form.get("MessageSid"),
        )
        if result.get("status") != "processed":
            return None

        from app.schemas.onboarding import OnboardingProcessResponse

        return OnboardingProcessResponse(
            message=result.get("reply") or "Processed",
            response_id=result.get("inbound", {}).get("message_id", ""),
            journey_id="",
            response_type=result.get("response_type", "unknown"),
            kyc_readiness="",
            journey_status="engaged",
            next_action=result.get("next_action") or "recorded",
        )

    def get_status(self, entity_id: str) -> OnboardingStatusResponse:
        journey_doc = self._repo.get_journey(entity_id)
        journey = self._journey_to_schema(journey_doc) if journey_doc else None
        responses = [_sanitize_mongo_doc(r) for r in self._repo.list_responses(entity_id)]
        handoff_docs = [
            h for h in self._repo.list_handoffs(limit=100)
            if h.get("entity_id") == str(entity_id)
        ]
        handoffs = [self._handoff_to_schema(h) for h in handoff_docs]
        return OnboardingStatusResponse(
            entity_id=str(entity_id),
            journey=journey,
            responses=responses,
            handoffs=handoffs,
        )

    def list_handoffs(self, status: str | None = None) -> list[RmHandoffResponse]:
        return [self._handoff_to_schema(h) for h in self._repo.list_handoffs(status=status)]

    def list_journeys(self, limit: int = 50) -> list[OnboardingJourneyResponse]:
        return [self._journey_to_schema(j) for j in self._repo.list_journeys(limit=limit)]

    def upload_kyc_document(
        self,
        *,
        entity_id: str,
        document_type: str,
        file_name: str,
        file_size_kb: int | None = None,
        checksum: str | None = None,
    ) -> dict:
        from app.onboarding.kyc_documents import KycDocumentService

        return KycDocumentService(self._db).upload(
            entity_id=entity_id,
            document_type=document_type,
            file_name=file_name,
            file_size_kb=file_size_kb,
            checksum=checksum,
        )

    def kyc_document_status(self, entity_id: str) -> dict:
        from app.onboarding.kyc_documents import KycDocumentService

        svc = KycDocumentService(self._db)
        return {
            "readiness": svc.readiness(entity_id),
            "documents": svc.list_documents(entity_id),
        }

    def _resolve_entity_by_phone(self, phone: str) -> str | None:
        digits = "".join(c for c in phone if c.isdigit())[-10:]
        if len(digits) < 10:
            return None
        lead = self._db.external_leads.find_one(
            {"phone_number": {"$regex": digits[-10:]}}
        )
        if lead:
            return str(lead.get("lead_id"))
        return None

    @staticmethod
    def _journey_to_schema(doc: dict) -> OnboardingJourneyResponse:
        return OnboardingJourneyResponse(
            journey_id=str(doc.get("journey_id", "")),
            entity_id=str(doc.get("entity_id", "")),
            entity_type=str(doc.get("entity_type", "External")),
            status=str(doc.get("status", "open")),
            kyc_readiness=str(doc.get("kyc_readiness", "Not Ready")),
            kyc_missing_items=list(doc.get("kyc_missing_items") or []),
            last_response_type=doc.get("last_response_type"),
            last_channel=doc.get("last_channel"),
            handoff_id=doc.get("handoff_id"),
            nudge_count=int(doc.get("nudge_count") or 0),
            product=doc.get("product"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    @staticmethod
    def _handoff_to_schema(doc: dict) -> RmHandoffResponse:
        return RmHandoffResponse(
            handoff_id=str(doc.get("handoff_id", "")),
            entity_id=str(doc.get("entity_id", "")),
            entity_type=str(doc.get("entity_type", "External")),
            customer_name=str(doc.get("customer_name", "")),
            phone=str(doc.get("phone", "")),
            product=doc.get("product"),
            priority=str(doc.get("priority", "normal")),
            status=str(doc.get("status", "pending")),
            reason=str(doc.get("reason", "")),
            source_channel=str(doc.get("source_channel", "")),
            talking_points=doc.get("talking_points"),
            created_at=doc.get("created_at"),
        )
