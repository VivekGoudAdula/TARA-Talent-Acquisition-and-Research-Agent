#!/usr/bin/env python3
"""Load generated CSV banking data and external leads Excel into MongoDB."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import pandas as pd

from app.config import get_settings
from app.db.codec import encode_value
from app.db.mongo import ensure_indexes, get_database
from app.external.external_import_service import ExternalImportService
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.utils.database import new_session

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

CSV_TABLES: list[tuple[str, str]] = [
    ("customers", "customers.csv"),
    ("products", "products.csv"),
    ("accounts", "accounts.csv"),
    ("transactions", "transactions.csv"),
    ("customer_products", "customer_products.csv"),
    ("consent", "consent.csv"),
]

BOOL_COLUMNS = {"is_existing_customer", "marketing_consent", "data_processing_consent", "is_active"}
DATE_COLUMNS = {"date_of_birth", "account_open_date", "transaction_date", "consent_date"}
DATETIME_COLUMNS = {"created_at", "updated_at", "last_updated", "consent_timestamp"}


def _coerce_value(column: str, value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if column in BOOL_COLUMNS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"true", "1", "yes", "t"}
    if column in DATE_COLUMNS:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        return datetime.combine(ts.date(), datetime.min.time())
    if column in DATETIME_COLUMNS:
        ts = pd.to_datetime(value, errors="coerce")
        return None if pd.isna(ts) else ts.to_pydatetime()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return encode_value(value)


def _rows_from_csv(csv_path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(csv_path)
    docs: list[dict[str, Any]] = []
    for record in df.to_dict(orient="records"):
        doc: dict[str, Any] = {}
        for key, value in record.items():
            coerced = _coerce_value(key, value)
            if coerced is not None:
                doc[key] = coerced
        docs.append(doc)
    return docs


def load_csv_tables(*, drop_existing: bool = False) -> dict[str, int]:
    settings = get_settings()
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI is not set in .env")

    db = get_database()

    if drop_existing:
        for collection, _ in CSV_TABLES:
            db[collection].drop()
            print(f"  dropped {collection}")

    ensure_indexes()

    counts: dict[str, int] = {}

    for collection, filename in CSV_TABLES:
        csv_path = OUTPUT_DIR / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing {csv_path} — run generate_banking_data.py first")

        docs = _rows_from_csv(csv_path)
        if docs:
            batch_size = 100
            for i in range(0, len(docs), batch_size):
                db[collection].insert_many(docs[i : i + batch_size], ordered=False)
        counts[collection] = len(docs)
        print(f"  {collection}: {len(docs)} documents")

    return counts


def import_external_leads() -> dict[str, int | str]:
    session = new_session()
    try:
        service = ExternalImportService(ExternalLeadRepository(session))
        return service.import_from_excel()
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load CSV + Excel data into MongoDB")
    parser.add_argument("--drop", action="store_true", help="Drop banking collections before load")
    parser.add_argument("--skip-external", action="store_true", help="Skip external leads Excel import")
    args = parser.parse_args()

    print("Loading banking CSVs from output/ ...")
    banking = load_csv_tables(drop_existing=args.drop)

    external: dict[str, int | str] = {}
    if not args.skip_external:
        print("Importing external leads from Excel ...")
        external = import_external_leads()
        print(f"  external_leads: imported={external.get('leads_imported')} updated={external.get('leads_updated')}")

    db = get_database()
    print("\nMongoDB totals:")
    for name in [*banking.keys(), "external_leads"]:
        print(f"  {name}: {db[name].count_documents({})}")

    print("\nLoad complete.")


if __name__ == "__main__":
    main()
