#!/usr/bin/env python3
"""Export Tara engagement-ready leads to CSV for the voice platform."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.config import get_settings
from app.db.mongo import MongoDatabase
from app.engagement.export_service import EngagementExportService


def main() -> None:
    parser = argparse.ArgumentParser(description="Export engagement leads from Tara MongoDB")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "exports" / "tara_engagement_leads.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--profile-types",
        default="External",
        help="Comma-separated profile types: External, Internal",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max records to export")
    parser.add_argument(
        "--min-conversion",
        type=float,
        default=None,
        help="Minimum conversion probability (0-100)",
    )
    parser.add_argument("--json", action="store_true", help="Also print JSON summary to stdout")
    args = parser.parse_args()

    settings = get_settings()
    types = [part.strip() for part in args.profile_types.split(",") if part.strip()]

    service = EngagementExportService(MongoDatabase())
    result = service.export_csv(
        Path(args.output),
        profile_types=types,
        limit=args.limit,
        min_conversion_probability=args.min_conversion,
    )

    print(f"Database: {settings.mongodb_db_name}")
    print(f"Exported: {len(result.records)} leads")
    print(f"CSV: {result.file_path}")
    if result.records:
        top = result.records[0]
        print(
            f"Top lead: {top.name} | {top.phone} | "
            f"{top.recommended_product} | conv={top.conversion_probability}"
        )

    if args.json:
        print(
            json.dumps(
                {
                    "records_exported": len(result.records),
                    "file_path": str(result.file_path),
                    "records": [r.model_dump() for r in result.records],
                },
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
