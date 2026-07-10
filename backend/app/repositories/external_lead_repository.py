"""Repository for external_leads collection."""

from __future__ import annotations

import time
from datetime import datetime
from uuid import UUID

from pymongo import InsertOne, ReplaceOne
from pymongo.errors import BulkWriteError

from app.db.mongo import MongoDatabase
from app.external.excel_importer import ImportedLeadRow
from app.models.external_lead import ExternalLead
from app.utils.exceptions import LeadNotFoundError

# Cosmos DB error codes
_DUPLICATE_KEY_CODE = 11000
_THROTTLE_CODE = 16500  # HTTP 429 TooManyRequests

# Max ops per bulk_write batch (keeps RU consumption below free-tier burst limit)
_BULK_BATCH_SIZE = 50


def _retry_after_ms(write_errors: list[dict]) -> float:
    """Extract the maximum RetryAfterMs hint from Cosmos DB throttle errors."""
    max_ms = 500.0
    for err in write_errors:
        msg = err.get("errmsg", "")
        import re
        m = re.search(r"RetryAfterMs=(\d+)", msg)
        if m:
            max_ms = max(max_ms, float(m.group(1)))
    return max_ms


class ExternalLeadRepository:
    """Data access layer for externally sourced CRM leads."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def upsert_lead(self, row: ImportedLeadRow) -> tuple[ExternalLead, bool]:
        existing = self.get_by_external_reference(row.external_reference)
        if existing:
            self._apply_row(existing, row)
            doc = existing.to_doc()
            self._db.external_leads.replace_one(
                {"lead_id": doc["lead_id"]}, doc, upsert=True
            )
            return existing, False

        lead = ExternalLead(
            lead_id=row.lead_id,
            external_reference=row.external_reference,
            full_name=row.full_name,
            phone_number=row.phone_number,
            email=row.email,
            age=row.age,
            gender=row.gender,
            occupation=row.occupation,
            employer=row.employer,
            estimated_income=row.estimated_income,
            credit_score=row.credit_score,
            city=row.city,
            state=row.state,
            preferred_language=row.preferred_language,
            referral_source=row.referral_source,
            campaign=row.campaign,
            lead_status=row.lead_status,
            consent=row.consent,
            lead_created_date=row.lead_created_date,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        self._db.external_leads.insert_one(lead.to_doc())
        return lead, True

    def bulk_upsert(self, rows: list[ImportedLeadRow]) -> tuple[int, int, int]:
        """Bulk upsert with Cosmos DB throttle-aware batching.

        Strategy:
        - Fetches all existing external_references in ONE query (avoids per-row lookups).
        - Builds ops in memory (InsertOne for new, ReplaceOne for existing).
        - Sends ops in batches of _BULK_BATCH_SIZE with retry on 429 (code 16500).
        """
        # Single round-trip to find existing refs
        existing_refs: set[str] = {
            doc["external_reference"]
            for doc in self._db.external_leads.find(
                {}, {"external_reference": 1, "_id": 0}
            )
        }

        all_ops: list = []
        imported = 0
        updated = 0

        for row in rows:
            lead = ExternalLead(
                lead_id=row.lead_id,
                external_reference=row.external_reference,
                full_name=row.full_name,
                phone_number=row.phone_number,
                email=row.email,
                age=row.age,
                gender=row.gender,
                occupation=row.occupation,
                employer=row.employer,
                estimated_income=row.estimated_income,
                credit_score=row.credit_score,
                city=row.city,
                state=row.state,
                preferred_language=row.preferred_language,
                referral_source=row.referral_source,
                campaign=row.campaign,
                lead_status=row.lead_status,
                consent=row.consent,
                lead_created_date=row.lead_created_date,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            doc = lead.to_doc()
            if row.external_reference in existing_refs:
                all_ops.append(
                    ReplaceOne(
                        {"external_reference": row.external_reference},
                        doc,
                        upsert=True,
                    )
                )
                updated += 1
            else:
                all_ops.append(InsertOne(doc))
                imported += 1

        # Send in throttle-safe batches
        for i in range(0, len(all_ops), _BULK_BATCH_SIZE):
            batch = all_ops[i : i + _BULK_BATCH_SIZE]
            self._bulk_write_with_retry(batch)

        return imported, updated, 0

    def _bulk_write_with_retry(self, ops: list, max_attempts: int = 8) -> None:
        """Execute a bulk_write batch, retrying on Cosmos DB 429 throttle errors."""
        pending = ops
        for attempt in range(max_attempts):
            try:
                self._db.external_leads.bulk_write(pending, ordered=False)
                return
            except BulkWriteError as exc:
                write_errors = exc.details.get("writeErrors", [])
                throttle_errors = [e for e in write_errors if e.get("code") == _THROTTLE_CODE]
                dup_errors = [e for e in write_errors if e.get("code") == _DUPLICATE_KEY_CODE]
                other_errors = [
                    e for e in write_errors
                    if e.get("code") not in (_THROTTLE_CODE, _DUPLICATE_KEY_CODE)
                ]

                if dup_errors:
                    # Duplicates are non-retryable — already exist, ignore
                    pass

                if other_errors and attempt == max_attempts - 1:
                    raise

                if throttle_errors:
                    wait_ms = _retry_after_ms(throttle_errors)
                    wait_s = (wait_ms / 1000.0) * (1.5 ** attempt)  # exponential growth
                    time.sleep(wait_s)
                    # Rebuild pending ops from failed indices
                    failed_indices = {e["index"] for e in write_errors if e.get("code") == _THROTTLE_CODE}
                    pending = [op for idx, op in enumerate(pending) if idx in failed_indices]
                    if not pending:
                        return
                elif other_errors:
                    time.sleep(2 ** attempt)
                else:
                    # Only duplicates — nothing more to do
                    return

    def get_all(self, limit: int = 1000, offset: int = 0) -> list[ExternalLead]:
        # No server-side sort — Azure Cosmos DB rejects order-by on many paths.
        docs = self._db.external_leads.find().skip(offset).limit(limit)
        return [ExternalLead.from_doc(d) for d in docs if d]

    def count_all(self) -> int:
        return self._db.external_leads.count_documents({})

    def get_by_lead_id(self, lead_id: UUID) -> ExternalLead | None:
        doc = self._db.external_leads.find_one({"lead_id": str(lead_id)})
        return ExternalLead.from_doc(doc)

    def get_by_lead_id_or_raise(self, lead_id: UUID) -> ExternalLead:
        lead = self.get_by_lead_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)
        return lead

    def get_by_external_reference(self, external_reference: str) -> ExternalLead | None:
        doc = self._db.external_leads.find_one(
            {"external_reference": external_reference}
        )
        return ExternalLead.from_doc(doc)

    def update_after_enrichment(
        self, lead_id: UUID, preferred_language: str, status: str = "ENRICHED"
    ) -> ExternalLead:
        lead = self.get_by_lead_id_or_raise(lead_id)
        lead.preferred_language = preferred_language
        lead.lead_status = status
        lead.updated_at = datetime.utcnow()
        self._db.external_leads.replace_one(
            {"lead_id": str(lead_id)}, lead.to_doc(), upsert=True
        )
        return lead

    def commit(self) -> None:
        self._db.commit()

    def count_duplicates_by_phone(self, phone_number: str, exclude_lead_id: UUID) -> int:
        return self._db.external_leads.count_documents(
            {
                "phone_number": phone_number,
                "lead_id": {"$ne": str(exclude_lead_id)},
            }
        )

    def count_duplicates_by_email(self, email: str, exclude_lead_id: UUID) -> int:
        return self._db.external_leads.count_documents(
            {
                "email": email,
                "lead_id": {"$ne": str(exclude_lead_id)},
            }
        )

    def count_duplicates_by_reference(
        self, external_reference: str, exclude_lead_id: UUID
    ) -> int:
        return self._db.external_leads.count_documents(
            {
                "external_reference": external_reference,
                "lead_id": {"$ne": str(exclude_lead_id)},
            }
        )

    @staticmethod
    def _apply_row(lead: ExternalLead, row: ImportedLeadRow) -> None:
        lead.full_name = row.full_name
        lead.phone_number = row.phone_number
        lead.email = row.email
        lead.age = row.age
        lead.gender = row.gender
        lead.occupation = row.occupation
        lead.employer = row.employer
        lead.estimated_income = row.estimated_income
        lead.credit_score = row.credit_score
        lead.city = row.city
        lead.state = row.state
        lead.preferred_language = row.preferred_language
        lead.referral_source = row.referral_source
        lead.campaign = row.campaign
        lead.consent = row.consent
        lead.lead_created_date = row.lead_created_date
        lead.updated_at = row.updated_at
