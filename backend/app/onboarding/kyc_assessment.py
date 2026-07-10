"""Lightweight KYC readiness from Mongo lead profile."""

from __future__ import annotations

from typing import Any


def assess_kyc_from_lead(
    lead_doc: dict[str, Any] | None,
    *,
    db=None,
    entity_id: str | None = None,
) -> tuple[str, list[str]]:
    """
    Returns (readiness, missing_items).
    readiness: Ready | Partially Ready | Not Ready
    """
    if entity_id and db is not None:
        from app.onboarding.kyc_documents import KycDocumentService

        doc_status = KycDocumentService(db).readiness(entity_id)
        if doc_status["uploaded_documents"]:
            return doc_status["kyc_readiness"], doc_status["missing_documents"]

    if not lead_doc:
        return "Not Ready", ["Lead profile not found"]

    missing: list[str] = []
    checks = 0

    phone = (lead_doc.get("phone_number") or "").strip()
    if len("".join(c for c in phone if c.isdigit())) >= 10:
        checks += 1
    else:
        missing.append("Phone Number")

    email = (lead_doc.get("email") or "").strip()
    if email and "@" in email:
        checks += 1
    else:
        missing.append("Email")

    name = (lead_doc.get("full_name") or "").strip()
    if len(name) > 2:
        checks += 1
    else:
        missing.append("Full Name")

    if lead_doc.get("consent"):
        checks += 1
    else:
        missing.append("Consent")

    occupation = (lead_doc.get("occupation") or "").strip().lower()
    if occupation and occupation != "unknown":
        checks += 1
    else:
        missing.append("Occupation")

    if checks >= 5:
        return "Ready", []
    if checks >= 3:
        return "Partially Ready", missing + ["PAN", "Address Proof", "Identity Verification"]
    return "Not Ready", missing + ["PAN", "Address Proof", "Identity Verification", "KYC Documents"]
