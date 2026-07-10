#!/usr/bin/env python3
"""Drop Tara MongoDB collections for a clean pipeline run."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import get_database

COLLECTIONS = (
    "customers",
    "products",
    "accounts",
    "transactions",
    "customer_products",
    "consent",
    "digital_activity",
    "external_leads",
    "customer_360_profile",
    "feature_store",
    "external_customer_profile",
    "lead_feature_store",
    "training_dataset",
    "repayment_predictions",
    "product_recommendations",
    "conversion_predictions",
    "ml_model_runs",
    "explainability_reports",
)


def main() -> None:
    db = get_database()
    existing = set(db.list_collection_names())
    for name in COLLECTIONS:
        if name in existing:
            db[name].drop()
            print(f"dropped: {name}")
        else:
            print(f"skip (missing): {name}")
    print("\nMongoDB reset complete. Next: python scripts/load_excel_to_mongo.py")


if __name__ == "__main__":
    main()
