"""Simulated KYC document upload — metadata only, no CKYC API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.db.mongo import MongoDatabase


REQUIRED_DOCS = ["aadhaar", "pan", "income_proof"]


class KycDocumentService:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def upload(
        self,
        *,
        entity_id: str,
        document_type: str,
        file_name: str,
        file_size_kb: int | None = None,
        checksum: str | None = None,
    ) -> dict[str, Any]:
        doc_id = str(uuid4())
        now = datetime.utcnow()
        record = {
            "document_id": doc_id,
            "entity_id": str(entity_id),
            "document_type": document_type.lower(),
            "file_name": file_name,
            "file_size_kb": file_size_kb,
            "checksum": checksum or f"sim-{doc_id[:8]}",
            "status": "received",
            "verification": "simulated_pending",
            "uploaded_at": now,
        }
        self._db.kyc_documents.insert_one(record)
        return record

    def list_documents(self, entity_id: str) -> list[dict[str, Any]]:
        rows = list(self._db.kyc_documents.find({"entity_id": str(entity_id)}, {"_id": 0}))
        rows.sort(key=lambda r: r.get("uploaded_at") or "", reverse=True)
        return rows

    def readiness(self, entity_id: str) -> dict[str, Any]:
        uploaded = {d["document_type"] for d in self.list_documents(entity_id)}
        missing = [t for t in REQUIRED_DOCS if t not in uploaded]
        if not missing:
            status = "Ready"
        elif len(uploaded) > 0:
            status = "Partially Ready"
        else:
            status = "Not Ready"
        return {
            "entity_id": entity_id,
            "kyc_readiness": status,
            "uploaded_documents": sorted(uploaded),
            "missing_documents": missing,
        }
