"""External Customer Intelligence Layer — Excel import pipeline."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

EXTERNAL_LEAD_NAMESPACE = UUID("6ecc3c04-4ef3-11ef-9c3b-0242ac120002")

import pandas as pd

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Canonical occupation labels aligned with internal banking reference data
OCCUPATION_ALIASES: dict[str, str] = {
    "software engineer": "Software Engineer",
    "software dev": "Software Engineer",
    "it professional": "Software Engineer",
    "doctor": "Doctor",
    "physician": "Doctor",
    "teacher": "Teacher",
    "professor": "Professor",
    "government employee": "Government Employee",
    "govt employee": "Government Employee",
    "civil servant": "Government Employee",
    "business owner": "Business Owner",
    "entrepreneur": "Business Owner",
    "self employed": "Business Owner",
    "farmer": "Farmer",
    "lawyer": "Lawyer",
    "advocate": "Lawyer",
    "chartered accountant": "Chartered Accountant",
    "ca": "Chartered Accountant",
    "student": "Student",
    "retired": "Retired",
    "sales executive": "Sales Executive",
    "nurse": "Nurse",
    "police officer": "Police Officer",
}

CITY_ALIASES: dict[str, str] = {
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "chennai": "Chennai",
    "madras": "Chennai",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "ahmedabad": "Ahmedabad",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "lucknow": "Lucknow",
    "jaipur": "Jaipur",
    "indore": "Indore",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "vijayawada": "Vijayawada",
}

CITY_STATE_MAP: dict[str, str] = {
    "Hyderabad": "Telangana",
    "Bangalore": "Karnataka",
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Chennai": "Tamil Nadu",
    "Pune": "Maharashtra",
    "Ahmedabad": "Gujarat",
    "Kolkata": "West Bengal",
    "Lucknow": "Uttar Pradesh",
    "Jaipur": "Rajasthan",
    "Visakhapatnam": "Andhra Pradesh",
    "Vijayawada": "Andhra Pradesh",
    "Indore": "Madhya Pradesh",
}

CITY_LANGUAGE_MAP: dict[str, str] = {
    "Hyderabad": "Telugu",
    "Bangalore": "Kannada",
    "Mumbai": "Marathi",
    "Delhi": "Hindi",
    "Chennai": "Tamil",
    "Pune": "Marathi",
    "Ahmedabad": "Gujarati",
    "Kolkata": "Bengali",
    "Lucknow": "Hindi",
    "Jaipur": "Hindi",
    "Visakhapatnam": "Telugu",
    "Vijayawada": "Telugu",
    "Indore": "Hindi",
}

OCCUPATION_AGE_DEFAULTS: dict[str, int] = {
    "Student": 21,
    "Software Engineer": 28,
    "Doctor": 35,
    "Teacher": 38,
    "Government Employee": 40,
    "Business Owner": 42,
    "Farmer": 45,
    "Lawyer": 38,
    "Chartered Accountant": 36,
    "Retired": 62,
    "Sales Executive": 30,
    "Nurse": 32,
    "Professor": 45,
    "Police Officer": 35,
}

REQUIRED_COLUMNS = (
    "LeadID",
    "Name",
    "Occupation",
    "EstimatedIncome",
    "Employer",
    "ReferralSource",
    "Campaign",
    "Consent",
    "CreditScore",
    "City",
)


@dataclass(frozen=True)
class ImportedLeadRow:
    """Validated, normalized lead ready for database persistence."""

    lead_id: UUID
    external_reference: str
    full_name: str
    phone_number: str
    email: str
    age: int
    gender: str
    occupation: str
    employer: str
    estimated_income: Decimal
    credit_score: int
    city: str
    state: str
    preferred_language: str
    referral_source: str
    campaign: str
    lead_status: str
    consent: bool
    lead_created_date: date
    created_at: datetime
    updated_at: datetime


class ExcelImporter:
    """
    Reads external lead Excel files, validates and normalizes data,
    and produces ImportedLeadRow objects for repository persistence.
    """

    def read_and_transform(self, file_path: Path) -> list[ImportedLeadRow]:
        """Read Excel file and return normalized lead rows."""
        if not file_path.exists():
            raise FileNotFoundError(f"External leads Excel file not found: {file_path}")

        logger.info("Reading external leads from %s", file_path)
        df = pd.read_excel(file_path, engine="openpyxl")
        self._validate_columns(df)
        df = self._clean_dataframe(df)

        rows: list[ImportedLeadRow] = []
        now = datetime.utcnow()

        for _, record in df.iterrows():
            external_ref = str(record["LeadID"]).strip()
            lead_uuid = self._deterministic_uuid(external_ref)
            occupation = self._normalize_occupation(str(record["Occupation"]))
            city = self._normalize_city(str(record["City"]))
            state = CITY_STATE_MAP.get(city, "Unknown")
            age = self._derive_age(external_ref, occupation)
            gender = self._derive_gender(external_ref, str(record["Name"]))
            phone = self._normalize_phone(external_ref)
            email = self._derive_email(str(record["Name"]), external_ref)
            consent = self._parse_consent(record["Consent"])
            income = Decimal(str(int(record["EstimatedIncome"])))
            credit = int(record["CreditScore"])

            rows.append(
                ImportedLeadRow(
                    lead_id=lead_uuid,
                    external_reference=external_ref,
                    full_name=str(record["Name"]).strip().title(),
                    phone_number=phone,
                    email=email,
                    age=age,
                    gender=gender,
                    occupation=occupation,
                    employer=str(record["Employer"]).strip().title(),
                    estimated_income=income,
                    credit_score=credit,
                    city=city,
                    state=state,
                    preferred_language=CITY_LANGUAGE_MAP.get(city, "English"),
                    referral_source=str(record["ReferralSource"]).strip(),
                    campaign=str(record["Campaign"]).strip(),
                    lead_status="NEW",
                    consent=consent,
                    lead_created_date=self._derive_lead_date(external_ref),
                    created_at=now,
                    updated_at=now,
                )
            )

        logger.info("Transformed %d external leads from Excel", len(rows))
        return rows

    @staticmethod
    def _validate_columns(df: pd.DataFrame) -> None:
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Excel missing required columns: {missing}")

    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        cleaned = df.copy()
        for col in REQUIRED_COLUMNS:
            if cleaned[col].dtype == object:
                cleaned[col] = cleaned[col].astype(str).str.strip()
                cleaned[col] = cleaned[col].replace({"nan": None, "None": None, "": None})
        cleaned = cleaned.dropna(subset=["LeadID", "Name", "Occupation", "City"])
        cleaned["EstimatedIncome"] = pd.to_numeric(cleaned["EstimatedIncome"], errors="coerce").fillna(0)
        cleaned["CreditScore"] = pd.to_numeric(cleaned["CreditScore"], errors="coerce").fillna(650).astype(int)
        cleaned["Employer"] = cleaned["Employer"].fillna("Unknown")
        cleaned["ReferralSource"] = cleaned["ReferralSource"].fillna("Direct")
        cleaned["Campaign"] = cleaned["Campaign"].fillna("General")
        cleaned["Consent"] = cleaned["Consent"].fillna("No")
        return cleaned

    @staticmethod
    def _normalize_occupation(raw: str) -> str:
        key = raw.strip().lower()
        if key in OCCUPATION_ALIASES:
            return OCCUPATION_ALIASES[key]
        title = raw.strip().title()
        for alias, canonical in OCCUPATION_ALIASES.items():
            if alias in key:
                return canonical
        return title if title else "Unknown"

    @staticmethod
    def _normalize_city(raw: str) -> str:
        key = raw.strip().lower()
        if key in CITY_ALIASES:
            return CITY_ALIASES[key]
        return raw.strip().title() if raw.strip() else "Unknown"

    @staticmethod
    def _normalize_phone(external_ref: str) -> str:
        digest = hashlib.sha256(external_ref.encode()).hexdigest()
        digits = "".join(str(int(c, 16) % 10) for c in digest[:10])
        return f"+91{digits}"

    @staticmethod
    def _derive_email(name: str, external_ref: str) -> str:
        slug = re.sub(r"[^a-z0-9]", "", name.lower())[:20] or "lead"
        ref_suffix = re.sub(r"[^A-Z0-9]", "", external_ref.upper())[-6:]
        return f"{slug}.{ref_suffix}@leads.tara.bank".lower()

    @staticmethod
    def _derive_age(external_ref: str, occupation: str) -> int:
        base = OCCUPATION_AGE_DEFAULTS.get(occupation, 32)
        offset = int(hashlib.md5(external_ref.encode()).hexdigest()[:2], 16) % 11 - 5
        return max(18, min(70, base + offset))

    @staticmethod
    def _derive_gender(external_ref: str, name: str) -> str:
        female_endings = ("a", "i", "ee", "ya")
        first = name.split()[0].lower() if name else ""
        if first.endswith(female_endings):
            return "Female"
        digest = int(hashlib.md5(external_ref.encode()).hexdigest()[:1], 16)
        return "Female" if digest % 2 == 0 else "Male"

    @staticmethod
    def _parse_consent(value: object) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in ("yes", "y", "true", "1", "granted")

    @staticmethod
    def _derive_lead_date(external_ref: str) -> date:
        digits = re.sub(r"\D", "", external_ref)
        if len(digits) >= 4:
            day_offset = int(digits[-3:]) % 365
        else:
            day_offset = int(hashlib.md5(external_ref.encode()).hexdigest()[:3], 16) % 365
        return date(2024, 1, 1) + timedelta(days=day_offset)

    @staticmethod
    def _deterministic_uuid(external_ref: str) -> UUID:
        """Generate stable UUID from external reference for idempotent re-imports."""
        return uuid5(EXTERNAL_LEAD_NAMESPACE, external_ref)
