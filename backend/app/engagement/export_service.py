"""Build engagement-ready lead payloads from Tara MongoDB intelligence."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.mongo import MongoDatabase
from app.schemas.engagement import EngagementLeadRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

CSV_COLUMNS = [
    "phone",
    "name",
    "product",
    "customer_id",
    "profile_id",
    "entity_type",
    "conversion_probability",
    "marketing_priority",
    "preferred_channel",
    "repayment_capacity",
    "talking_points",
    "reason_codes",
]


@dataclass
class EngagementExportResult:
    records: list[EngagementLeadRecord]
    file_path: Path | None = None


class EngagementExportService:
    """Reads ML + explainability outputs and produces voice-campaign-ready rows."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def build_records(
        self,
        *,
        profile_types: list[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
        min_conversion_probability: float | None = None,
        require_phone: bool = True,
        require_consent: bool = True,
    ) -> list[EngagementLeadRecord]:
        types = {t.strip().title() for t in (profile_types or ["External", "Internal"])}
        # Cap MongoDB reads for preview/export — avoids full collection scans on Cosmos DB.
        db_fetch_limit: int | None = None
        if limit is not None:
            db_fetch_limit = min(max((limit + offset) * 3, 20), 100)

        records: list[EngagementLeadRecord] = []

        if "External" in types and "Internal" in types and db_fetch_limit is not None:
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_ext = pool.submit(
                    self._build_external_records,
                    require_phone,
                    require_consent,
                    db_limit=db_fetch_limit,
                )
                f_int = pool.submit(
                    self._build_internal_records,
                    require_phone,
                    require_consent,
                    db_limit=max(db_fetch_limit // 2, 10),
                )
                records.extend(f_ext.result())
                records.extend(f_int.result())
        else:
            if "External" in types:
                records.extend(
                    self._build_external_records(
                        require_phone, require_consent, db_limit=db_fetch_limit
                    )
                )
            if "Internal" in types:
                records.extend(
                    self._build_internal_records(
                        require_phone, require_consent, db_limit=db_fetch_limit
                    )
                )

        if min_conversion_probability is not None:
            records = [
                r
                for r in records
                if r.conversion_probability is not None
                and r.conversion_probability >= min_conversion_probability
            ]

        records = self._sort_and_slice(records, offset, limit)

        logger.info(
            "Built %d engagement records (types=%s offset=%d limit=%s)",
            len(records),
            sorted(types),
            offset,
            limit,
        )
        return records

    def build_preview_records(
        self,
        *,
        profile_types: list[str] | None = None,
        limit: int = 20,
        min_conversion_probability: float | None = None,
    ) -> list[EngagementLeadRecord]:
        """Fast preview path — minimal Cosmos DB round-trips for the engagement UI."""
        types = {t.strip().title() for t in (profile_types or ["External"])}
        records: list[EngagementLeadRecord] = []
        fetch_cap = min(max(limit * 3, 15), 60)

        if "External" in types:
            cursor = self._db.external_leads.find(
                {},
                {
                    "lead_id": 1,
                    "phone_number": 1,
                    "full_name": 1,
                    "email": 1,
                    "consent": 1,
                },
            ).limit(fetch_cap)
            leads = list(cursor)
            lead_ids = [str(l["lead_id"]) for l in leads if l.get("lead_id")]
            conversions: dict[str, dict[str, Any]] = {}
            if lead_ids:
                conversions = {
                    str(c["lead_id"]): c
                    for c in self._db.conversion_predictions.find(
                        {"lead_id": {"$in": lead_ids}},
                        {
                            "lead_id": 1,
                            "conversion_probability": 1,
                            "marketing_priority": 1,
                            "lead_priority": 1,
                        },
                    )
                    if c.get("lead_id")
                }
            for lead_doc in leads:
                if not lead_doc.get("consent", False):
                    continue
                phone = (lead_doc.get("phone_number") or "").strip()
                if not phone:
                    continue
                lead_id = str(lead_doc.get("lead_id", ""))
                conv_doc = conversions.get(lead_id)
                records.append(
                    self._assemble_record(
                        entity_type="External",
                        entity_id=lead_id,
                        profile_id=None,
                        phone=phone,
                        name=(lead_doc.get("full_name") or "Customer").strip(),
                        email=lead_doc.get("email"),
                        preferred_channel=None,
                        product_doc=None,
                        repayment_doc=None,
                        conv_doc=conv_doc,
                        expl_doc=None,
                        consent=bool(lead_doc.get("consent")),
                    )
                )

        if min_conversion_probability is not None:
            records = [
                r
                for r in records
                if r.conversion_probability is not None
                and r.conversion_probability >= min_conversion_probability
            ]

        records = self._sort_and_slice(records, 0, limit)
        logger.info("Built %d lightweight preview records (limit=%s)", len(records), limit)
        return records

    @staticmethod
    def _sort_and_slice(
        records: list[EngagementLeadRecord],
        offset: int,
        limit: int | None,
    ) -> list[EngagementLeadRecord]:
        records.sort(
            key=lambda r: (r.conversion_probability is not None, r.conversion_probability or 0),
            reverse=True,
        )
        if offset:
            records = records[offset:]
        if limit is not None:
            records = records[:limit]
        return records

    def build_record_for_entity(
        self,
        entity_id: str,
        entity_type: str,
    ) -> EngagementLeadRecord | None:
        """Build one engagement record by entity id (avoids full collection scan)."""
        et = entity_type.strip().title()
        if et == "External":
            if entity_id.startswith("phone:"):
                digits = entity_id.split(":", 1)[-1][-10:]
                lead_doc = self._db.external_leads.find_one(
                    {"phone_number": {"$regex": digits}}
                )
            else:
                lead_doc = self._db.external_leads.find_one({"lead_id": str(entity_id)})
            if not lead_doc:
                return None
            lead_id = str(lead_doc.get("lead_id", ""))
            profile_doc = self._db.external_customer_profile.find_one({"lead_id": lead_id})
            profile_id = str(profile_doc.get("profile_id")) if profile_doc else None
            product_doc = (
                self._db.product_recommendations.find_one({"profile_id": profile_id})
                if profile_id
                else None
            )
            repayment_doc = (
                self._db.repayment_predictions.find_one({"profile_id": profile_id})
                if profile_id
                else None
            )
            conv_doc = self._db.conversion_predictions.find_one({"lead_id": lead_id})
            expl_doc = self._db.explainability_reports.find_one({"customer_id": lead_id})
            return self._assemble_record(
                entity_type="External",
                entity_id=lead_id,
                profile_id=profile_id,
                phone=(lead_doc.get("phone_number") or "").strip(),
                name=(lead_doc.get("full_name") or "Customer").strip(),
                email=lead_doc.get("email"),
                preferred_channel=profile_doc.get("preferred_channel") if profile_doc else None,
                product_doc=product_doc,
                repayment_doc=repayment_doc,
                conv_doc=conv_doc,
                expl_doc=expl_doc,
                consent=bool(lead_doc.get("consent")),
            )

        customer_doc = self._db.customers.find_one({"customer_id": str(entity_id)})
        if not customer_doc:
            return None
        profile_doc = self._db.customer_360_profile.find_one({"customer_id": str(entity_id)})
        profile_id = str(profile_doc.get("profile_id", "")) if profile_doc else ""
        product_doc = (
            self._db.product_recommendations.find_one({"profile_id": profile_id})
            if profile_id
            else None
        )
        repayment_doc = (
            self._db.repayment_predictions.find_one({"profile_id": profile_id})
            if profile_id
            else None
        )
        expl_doc = self._db.explainability_reports.find_one({"customer_id": str(entity_id)})
        consent_doc = self._db.consent.find_one({"customer_id": str(entity_id)})
        marketing_ok = True if not consent_doc else bool(consent_doc.get("marketing_voice", True))
        first = (customer_doc.get("first_name") or "").strip()
        last = (customer_doc.get("last_name") or "").strip()
        return self._assemble_record(
            entity_type="Internal",
            entity_id=str(entity_id),
            profile_id=profile_id or None,
            phone=(customer_doc.get("phone_number") or "").strip(),
            name=f"{first} {last}".strip() or "Customer",
            email=customer_doc.get("email"),
            preferred_channel=profile_doc.get("preferred_channel") if profile_doc else None,
            product_doc=product_doc,
            repayment_doc=repayment_doc,
            conv_doc=None,
            expl_doc=expl_doc,
            consent=marketing_ok,
        )

    def export_csv(
        self,
        output_path: Path,
        *,
        profile_types: list[str] | None = None,
        limit: int | None = None,
        min_conversion_probability: float | None = None,
    ) -> EngagementExportResult:
        records = self.build_records(
            profile_types=profile_types,
            limit=limit,
            min_conversion_probability=min_conversion_probability,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow(self._record_to_csv_row(record))
        return EngagementExportResult(records=records, file_path=output_path)

    def records_to_csv_text(self, records: list[EngagementLeadRecord]) -> str:
        from io import StringIO

        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(self._record_to_csv_row(record))
        return buffer.getvalue()

    def _build_external_records(
        self,
        require_phone: bool,
        require_consent: bool,
        *,
        db_limit: int | None = None,
    ) -> list[EngagementLeadRecord]:
        cursor = self._db.external_leads.find()
        if db_limit is not None:
            cursor = cursor.limit(db_limit)
        leads = list(cursor)
        lead_ids = [str(l["lead_id"]) for l in leads if l.get("lead_id")]

        profiles: dict[str, dict[str, Any]] = {}
        products: dict[str, dict[str, Any]] = {}
        repayments: dict[str, dict[str, Any]] = {}
        conversions: dict[str, dict[str, Any]] = {}
        explains: dict[str, dict[str, Any]] = {}

        if lead_ids:
            with ThreadPoolExecutor(max_workers=5) as pool:
                f_profiles = pool.submit(
                    lambda: list(
                        self._db.external_customer_profile.find({"lead_id": {"$in": lead_ids}})
                    )
                )
                f_conversions = pool.submit(
                    lambda: list(
                        self._db.conversion_predictions.find({"lead_id": {"$in": lead_ids}})
                    )
                )
                f_explains = pool.submit(
                    lambda: list(
                        self._db.explainability_reports.find({"customer_id": {"$in": lead_ids}})
                    )
                )
                profile_rows = f_profiles.result()
                conversion_rows = f_conversions.result()
                explain_rows = f_explains.result()

            profiles = {str(p["lead_id"]): p for p in profile_rows if p.get("lead_id")}
            profile_ids = [str(p["profile_id"]) for p in profiles.values() if p.get("profile_id")]
            conversions = {str(c["lead_id"]): c for c in conversion_rows if c.get("lead_id")}
            explains = {str(e["customer_id"]): e for e in explain_rows if e.get("customer_id")}

            if profile_ids:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    f_products = pool.submit(
                        lambda: list(
                            self._db.product_recommendations.find({"profile_id": {"$in": profile_ids}})
                        )
                    )
                    f_repayments = pool.submit(
                        lambda: list(
                            self._db.repayment_predictions.find({"profile_id": {"$in": profile_ids}})
                        )
                    )
                    product_rows = f_products.result()
                    repayment_rows = f_repayments.result()
                products = {str(p["profile_id"]): p for p in product_rows if p.get("profile_id")}
                repayments = {str(r["profile_id"]): r for r in repayment_rows if r.get("profile_id")}

        records: list[EngagementLeadRecord] = []
        for lead_doc in leads:
            if not lead_doc:
                continue
            if require_consent and not lead_doc.get("consent", False):
                continue
            phone = (lead_doc.get("phone_number") or "").strip()
            if require_phone and not phone:
                continue

            lead_id = str(lead_doc.get("lead_id", ""))
            profile_doc = profiles.get(lead_id)
            profile_id = str(profile_doc.get("profile_id")) if profile_doc else None

            records.append(
                self._assemble_record(
                    entity_type="External",
                    entity_id=lead_id,
                    profile_id=profile_id,
                    phone=phone,
                    name=(lead_doc.get("full_name") or "Customer").strip(),
                    email=lead_doc.get("email"),
                    preferred_channel=(
                        profile_doc.get("preferred_channel") if profile_doc else None
                    ),
                    product_doc=products.get(profile_id) if profile_id else None,
                    repayment_doc=repayments.get(profile_id) if profile_id else None,
                    conv_doc=conversions.get(lead_id),
                    expl_doc=explains.get(lead_id),
                    consent=bool(lead_doc.get("consent")),
                )
            )
        return records

    def _build_internal_records(
        self,
        require_phone: bool,
        require_consent: bool,
        *,
        db_limit: int | None = None,
    ) -> list[EngagementLeadRecord]:
        cursor = self._db.customer_360_profile.find()
        if db_limit is not None:
            cursor = cursor.limit(db_limit)
        profiles = list(cursor)
        customer_ids = [str(p["customer_id"]) for p in profiles if p.get("customer_id")]

        customers: dict[str, dict[str, Any]] = {}
        consents: dict[str, dict[str, Any]] = {}
        products: dict[str, dict[str, Any]] = {}
        repayments: dict[str, dict[str, Any]] = {}
        explains: dict[str, dict[str, Any]] = {}

        profile_ids = [str(p["profile_id"]) for p in profiles if p.get("profile_id")]

        if customer_ids:
            with ThreadPoolExecutor(max_workers=4) as pool:
                f_customers = pool.submit(
                    lambda: list(self._db.customers.find({"customer_id": {"$in": customer_ids}}))
                )
                f_consents = pool.submit(
                    lambda: list(self._db.consent.find({"customer_id": {"$in": customer_ids}}))
                )
                f_explains = pool.submit(
                    lambda: list(
                        self._db.explainability_reports.find({"customer_id": {"$in": customer_ids}})
                    )
                )
                customer_rows = f_customers.result()
                consent_rows = f_consents.result()
                explain_rows = f_explains.result()

            customers = {str(c["customer_id"]): c for c in customer_rows if c.get("customer_id")}
            consents = {str(c["customer_id"]): c for c in consent_rows if c.get("customer_id")}
            explains = {str(e["customer_id"]): e for e in explain_rows if e.get("customer_id")}

        if profile_ids:
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_products = pool.submit(
                    lambda: list(
                        self._db.product_recommendations.find({"profile_id": {"$in": profile_ids}})
                    )
                )
                f_repayments = pool.submit(
                    lambda: list(
                        self._db.repayment_predictions.find({"profile_id": {"$in": profile_ids}})
                    )
                )
                product_rows = f_products.result()
                repayment_rows = f_repayments.result()
            products = {str(p["profile_id"]): p for p in product_rows if p.get("profile_id")}
            repayments = {str(r["profile_id"]): r for r in repayment_rows if r.get("profile_id")}

        records: list[EngagementLeadRecord] = []
        for profile_doc in profiles:
            if not profile_doc:
                continue
            customer_id = str(profile_doc.get("customer_id", ""))
            customer_doc = customers.get(customer_id)
            if not customer_doc:
                continue

            consent_doc = consents.get(customer_id)
            marketing_ok = True
            if require_consent and consent_doc:
                marketing_ok = bool(consent_doc.get("marketing_voice", True))
            if require_consent and not marketing_ok:
                continue

            phone = (customer_doc.get("phone_number") or "").strip()
            if require_phone and not phone:
                continue

            profile_id = str(profile_doc.get("profile_id", ""))
            first = (customer_doc.get("first_name") or "").strip()
            last = (customer_doc.get("last_name") or "").strip()
            name = f"{first} {last}".strip() or "Customer"

            records.append(
                self._assemble_record(
                    entity_type="Internal",
                    entity_id=customer_id,
                    profile_id=profile_id,
                    phone=phone,
                    name=name,
                    email=customer_doc.get("email"),
                    preferred_channel=profile_doc.get("preferred_channel"),
                    product_doc=products.get(profile_id),
                    repayment_doc=repayments.get(profile_id),
                    conv_doc=None,
                    expl_doc=explains.get(customer_id),
                    consent=marketing_ok,
                )
            )
        return records

    def _assemble_record(
        self,
        *,
        entity_type: str,
        entity_id: str,
        profile_id: str | None,
        phone: str,
        name: str,
        email: str | None,
        preferred_channel: str | None,
        product_doc: dict[str, Any] | None,
        repayment_doc: dict[str, Any] | None,
        conv_doc: dict[str, Any] | None,
        expl_doc: dict[str, Any] | None,
        consent: bool | None,
    ) -> EngagementLeadRecord:
        reason_codes: list[str] = []
        talking_points = None
        if expl_doc:
            raw_codes = expl_doc.get("reason_codes")
            if isinstance(raw_codes, list):
                reason_codes = [str(c) for c in raw_codes]
            talking_points = expl_doc.get("llm_summary") or None
            if not talking_points and isinstance(expl_doc.get("llm_response"), dict):
                talking_points = expl_doc["llm_response"].get("summary")

        conversion_probability = None
        marketing_priority = None
        lead_priority = None
        if conv_doc:
            conversion_probability = self._as_float(conv_doc.get("conversion_probability"))
            marketing_priority = conv_doc.get("marketing_priority")
            lead_priority = conv_doc.get("lead_priority")
        elif entity_type == "External" and product_doc is None:
            pass

        repayment_capacity = None
        if repayment_doc:
            repayment_capacity = repayment_doc.get("repayment_capacity")
        elif product_doc:
            repayment_capacity = product_doc.get("repayment_capacity")

        recommended_product = None
        product_names: list[str] = []
        if product_doc:
            recommended_product = product_doc.get("top_recommendation")
            recs = product_doc.get("recommendations") or []
            if isinstance(recs, list):
                for item in recs:
                    if isinstance(item, dict) and item.get("product_name"):
                        product_names.append(str(item["product_name"]))
                    elif isinstance(item, str):
                        product_names.append(item)

        return EngagementLeadRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            profile_id=profile_id,
            phone=phone,
            name=name,
            email=email,
            recommended_product=recommended_product,
            conversion_probability=conversion_probability,
            marketing_priority=marketing_priority,
            lead_priority=lead_priority,
            preferred_channel=preferred_channel,
            repayment_capacity=repayment_capacity,
            talking_points=talking_points,
            reason_codes=reason_codes,
            consent=consent,
            product_recommendations=product_names,
        )

    @staticmethod
    def _record_to_csv_row(record: EngagementLeadRecord) -> dict[str, str]:
        return {
            "phone": record.phone,
            "name": record.name,
            "product": record.recommended_product or "",
            "customer_id": record.entity_id,
            "profile_id": record.profile_id or "",
            "entity_type": record.entity_type,
            "conversion_probability": (
                f"{record.conversion_probability:.1f}"
                if record.conversion_probability is not None
                else ""
            ),
            "marketing_priority": record.marketing_priority or "",
            "preferred_channel": record.preferred_channel or "",
            "repayment_capacity": record.repayment_capacity or "",
            "talking_points": record.talking_points or "",
            "reason_codes": ", ".join(record.reason_codes),
        }

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
