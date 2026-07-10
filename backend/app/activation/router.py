"""Activation API — simulated UPI / YONO onboarding."""

from fastapi import APIRouter, Depends

from app.dependencies import get_activation_service
from app.activation.service import ActivationService
from app.schemas.activation import (
    ActivationStartRequest,
    ActivationStartResponse,
    ActivationStatusResponse,
    ActivationStepRequest,
)

router = APIRouter(prefix="/api/activation", tags=["Digital Activation"])


@router.post("/start", response_model=ActivationStartResponse)
def start_activation(
    request: ActivationStartRequest,
    service: ActivationService = Depends(get_activation_service),
) -> ActivationStartResponse:
    return service.start(request)


@router.post("/step", response_model=ActivationStatusResponse | None)
def complete_activation_step(
    request: ActivationStepRequest,
    service: ActivationService = Depends(get_activation_service),
) -> ActivationStatusResponse | None:
    return service.complete_step(request)


@router.get("/status/{entity_id}", response_model=ActivationStatusResponse | None)
def get_activation_status(
    entity_id: str,
    service: ActivationService = Depends(get_activation_service),
) -> ActivationStatusResponse | None:
    return service.get_status(entity_id)
