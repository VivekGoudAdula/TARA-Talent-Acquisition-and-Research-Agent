"""UPI / YONO activation service facade."""

from __future__ import annotations

from app.activation.repository import ActivationRepository
from app.db.mongo import MongoDatabase
from app.schemas.activation import (
    ActivationStartRequest,
    ActivationStartResponse,
    ActivationStatusResponse,
    ActivationStepRequest,
)


class ActivationService:
    def __init__(self, db: MongoDatabase) -> None:
        self._repo = ActivationRepository(db)

    def start(self, request: ActivationStartRequest) -> ActivationStartResponse:
        activation_id = self._repo.start(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            phone=request.phone,
            product=request.product,
        )
        doc = self._repo.get_by_entity(request.entity_id)
        return ActivationStartResponse(
            message="YONO / UPI activation journey started (simulated)",
            activation_id=activation_id,
            deep_link=doc.get("deep_link") if doc else None,
            steps_total=len(doc.get("steps", [])) if doc else 0,
        )

    def complete_step(self, request: ActivationStepRequest) -> ActivationStatusResponse | None:
        doc = self._repo.complete_step(request.activation_id, request.step)
        return self._to_status(doc) if doc else None

    def get_status(self, entity_id: str) -> ActivationStatusResponse | None:
        doc = self._repo.get_by_entity(entity_id)
        return self._to_status(doc) if doc else None

    def list_recent(self, limit: int = 20) -> list[ActivationStatusResponse]:
        return [self._to_status(d) for d in self._repo.list_recent(limit) if d]

    @staticmethod
    def _to_status(doc: dict) -> ActivationStatusResponse:
        return ActivationStatusResponse(
            activation_id=doc["activation_id"],
            entity_id=doc["entity_id"],
            entity_type=doc.get("entity_type", "External"),
            phone=doc.get("phone", ""),
            product=doc.get("product"),
            status=doc.get("status", "in_progress"),
            channel=doc.get("channel", "YONO_UPI"),
            deep_link=doc.get("deep_link"),
            steps=doc.get("steps", []),
            created_at=doc.get("created_at"),
            completed_at=doc.get("completed_at"),
        )
