"""Layer 5 — Conversion & Onboarding API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_onboarding_service
from app.onboarding.service import OnboardingService
from app.schemas.onboarding import (
    LeadResponseCaptureRequest,
    OnboardingJourneyResponse,
    OnboardingProcessResponse,
    OnboardingStatusResponse,
    RmHandoffResponse,
)
from app.schemas.ops import KycDocumentUploadRequest

router = APIRouter(prefix="/api/onboarding", tags=["Conversion & Onboarding"])


@router.post(
    "/lead-response",
    response_model=OnboardingProcessResponse,
    summary="Capture lead response (interest / decline / callback)",
)
def capture_lead_response(
    request: LeadResponseCaptureRequest,
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingProcessResponse:
    return service.process_lead_response(request)


@router.post(
    "/webhooks/whatsapp",
    summary="Twilio WhatsApp inbound — capture replies and trigger onboarding",
)
async def whatsapp_inbound_webhook(
    request: Request,
    service: OnboardingService = Depends(get_onboarding_service),
) -> dict:
    form = dict(await request.form())
    result = service.process_whatsapp_inbound(form)
    if result:
        return {"status": "processed", "next_action": result.next_action}
    return {"status": "ignored"}


@router.get(
    "/status/{entity_id}",
    response_model=OnboardingStatusResponse,
    summary="Full onboarding journey for a lead",
)
def get_onboarding_status(
    entity_id: str,
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingStatusResponse:
    return service.get_status(entity_id)


@router.get(
    "/journeys",
    response_model=list[OnboardingJourneyResponse],
    summary="Recent onboarding journeys",
)
def list_journeys(
    limit: int = 50,
    service: OnboardingService = Depends(get_onboarding_service),
) -> list[OnboardingJourneyResponse]:
    return service.list_journeys(limit=limit)


@router.get(
    "/handoffs",
    response_model=list[RmHandoffResponse],
    summary="RM handoff queue",
)
def list_handoffs(
    status: str | None = None,
    service: OnboardingService = Depends(get_onboarding_service),
) -> list[RmHandoffResponse]:
    return service.list_handoffs(status=status)


@router.post("/kyc/documents", summary="Upload KYC document metadata (simulated)")
def upload_kyc_document(
    request: KycDocumentUploadRequest,
    service: OnboardingService = Depends(get_onboarding_service),
) -> dict:
    from app.schemas.ops import KycDocumentResponse

    doc = service.upload_kyc_document(
        entity_id=request.entity_id,
        document_type=request.document_type,
        file_name=request.file_name,
        file_size_kb=request.file_size_kb,
        checksum=request.checksum,
    )
    return KycDocumentResponse(**doc).model_dump()


@router.get("/kyc/documents/{entity_id}", summary="List uploaded KYC documents")
def list_kyc_documents(
    entity_id: str,
    service: OnboardingService = Depends(get_onboarding_service),
) -> dict:
    return service.kyc_document_status(entity_id)
