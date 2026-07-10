"""Create external leads from web forms and demo simulate actions."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.external.excel_importer import (
    CITY_LANGUAGE_MAP,
    CITY_STATE_MAP,
    ExcelImporter,
    ImportedLeadRow,
)


def _normalize_phone_input(phone: str | None, external_ref: str) -> str:
    if phone and phone.strip():
        digits = re.sub(r"\D", "", phone.strip())
        if digits.startswith("91") and len(digits) >= 12:
            return f"+{digits[:12]}"
        if len(digits) == 10:
            return f"+91{digits}"
        if digits.startswith("0") and len(digits) == 11:
            return f"+91{digits[1:]}"
        return f"+{digits}" if digits else ExcelImporter._normalize_phone(external_ref)
    return ExcelImporter._normalize_phone(external_ref)


def _normalize_email_input(email: str | None, name: str, external_ref: str) -> str:
    if email and "@" in email:
        return email.strip().lower()
    return ExcelImporter._derive_email(name, external_ref)


def _derive_credit_score(salary: int | float) -> int:
    base = 620 + int(float(salary) // 2500)
    return max(550, min(850, base))


def _build_row(
    *,
    name: str,
    salary: int | float,
    source: str,
    campaign: str,
    phone: str | None = None,
    email: str | None = None,
    city: str | None = None,
    interested_product: str | None = None,
    external_reference: str | None = None,
) -> ImportedLeadRow:
    now = datetime.utcnow()
    ext_ref = external_reference or f"WEB-{uuid.uuid4().hex[:12].upper()}"
    lead_uuid = ExcelImporter._deterministic_uuid(ext_ref)
    occupation = "Software Engineer" if float(salary) >= 50000 else "Sales Executive"
    normalized_city = ExcelImporter._normalize_city(city or "Hyderabad")
    state = CITY_STATE_MAP.get(normalized_city, "Telangana")
    product_campaign = interested_product or campaign

    return ImportedLeadRow(
        lead_id=lead_uuid,
        external_reference=ext_ref,
        full_name=name.strip().title(),
        phone_number=_normalize_phone_input(phone, ext_ref),
        email=_normalize_email_input(email, name, ext_ref),
        age=ExcelImporter._derive_age(ext_ref, occupation),
        gender=ExcelImporter._derive_gender(ext_ref, name),
        occupation=occupation,
        employer=interested_product or "Web Applicant",
        estimated_income=Decimal(str(int(float(salary)))),
        credit_score=_derive_credit_score(salary),
        city=normalized_city,
        state=state,
        preferred_language=CITY_LANGUAGE_MAP.get(normalized_city, "English"),
        referral_source=source.strip(),
        campaign=product_campaign.strip(),
        lead_status="NEW",
        consent=True,
        lead_created_date=date.today(),
        created_at=now,
        updated_at=now,
    )


def build_simulate_row(
    *,
    source: str = "Instagram",
    campaign: str = "Home Loan July",
    name: str = "Krishna",
    salary: int = 85000,
) -> ImportedLeadRow:
    ext_ref = f"SIM-IG-{uuid.uuid4().hex[:8].upper()}"
    return _build_row(
        name=name,
        salary=salary,
        source=source,
        campaign=campaign,
        city="Hyderabad",
        interested_product=campaign,
        external_reference=ext_ref,
    )


def build_form_row(
    *,
    name: str,
    phone: str,
    email: str,
    salary: int | float,
    city: str,
    interested_product: str,
    source: str = "University Portal",
) -> ImportedLeadRow:
    return _build_row(
        name=name,
        salary=salary,
        source=source,
        campaign=interested_product,
        phone=phone,
        email=email,
        city=city,
        interested_product=interested_product,
    )
