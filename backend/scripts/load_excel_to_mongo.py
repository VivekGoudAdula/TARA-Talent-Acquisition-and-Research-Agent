#!/usr/bin/env python3
"""Load Tara Excel into MongoDB. Use --append to add a batch without wiping internal data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import MongoDatabase
from app.external.external_import_service import ExternalImportService
from app.internal.banking_import_service import BankingImportService
from app.repositories.banking_import_repository import BankingImportRepository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.utils.database import new_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Excel workbooks into MongoDB")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append internal banking rows (do not drop existing customers)",
    )
    parser.add_argument("--skip-external", action="store_true")
    args = parser.parse_args()

    session = new_session()
    try:
        print(f"=== Internal banking (append={args.append}) ===")
        banking = BankingImportService(BankingImportRepository(session))
        internal = banking.import_from_excel(replace_existing=not args.append)
        for key in ("customers", "accounts", "transactions", "customer_products", "consent"):
            print(f"  {key}: {internal.get(key)}")

        if not args.skip_external:
            print("\n=== External leads ===")
            external = ExternalImportService(ExternalLeadRepository(session)).import_from_excel()
            print(f"  external_leads imported: {external.get('leads_imported')}")
            print(f"  external_leads updated: {external.get('leads_updated')}")
    finally:
        session.close()

    db = MongoDatabase()
    print(
        f"\nTotals: internal={db.customers.count_documents({})} "
        f"external={db.external_leads.count_documents({})}"
    )
    print("\nDone. Next: python scripts/run_pre_xai_pipeline.py")


if __name__ == "__main__":
    main()
