"""Load database settings from .env and shared test helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_db_env() -> None:
    """Load .env from the project root (does not override existing env vars)."""
    load_dotenv(_ENV_PATH)


def sample_customer_id() -> UUID:
    from app.db.mongo import MongoDatabase

    db = MongoDatabase()
    doc = db.customers.find_one({}, {"customer_id": 1})
    if not doc:
        raise RuntimeError("No customers in MongoDB — run migration or seed data first")
    return UUID(doc["customer_id"])


def sample_lead_id() -> UUID:
    from app.db.mongo import MongoDatabase

    db = MongoDatabase()
    doc = db.external_leads.find_one({}, {"lead_id": 1})
    if not doc:
        raise RuntimeError("No external leads in MongoDB — run migration or seed data first")
    return UUID(doc["lead_id"])
