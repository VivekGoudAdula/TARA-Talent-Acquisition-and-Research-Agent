#!/usr/bin/env python3
"""
Run engagement outreach for the next batch of internal + external customers.

Test routing (when ENGAGEMENT_TEST_MODE=true in .env):
  WhatsApp → ENGAGEMENT_WHATSAPP_OVERRIDE_PHONE only
  SMS      → round-robin ENGAGEMENT_SMS_TEST_PHONES
  Email    → round-robin ENGAGEMENT_EMAIL_TEST_ADDRESSES

Example — live WhatsApp for customers 51–100 (offset 50, limit 50 each type):
  python scripts/run_engagement_test_batch.py --live --channel WhatsApp --offset 50 --limit 50

Example — all three channels (dry-run first):
  python scripts/run_engagement_test_batch.py --dry-run --all-channels --limit 50
"""

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
from app.engagement.service import EngagementService
from app.schemas.engagement import OutreachRequest


def _count_records(db: MongoDatabase) -> dict[str, int]:
    return {
        "internal_customers": db.customers.count_documents({}),
        "external_leads": db.external_leads.count_documents({}),
    }


def _run_channel(
    service: EngagementService,
    *,
    channel: str,
    limit: int,
    offset: int,
    dry_run: bool,
) -> dict:
    request = OutreachRequest(
        channel=channel,
        limit=limit,
        offset=offset,
        profile_types=["Internal", "External"],
        dry_run=dry_run,
        require_consent=False,
        auto_sequence=not dry_run,
    )
    result = service.run_outreach(request)
    return result.model_dump()


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Engagement test batch — 50 internal + 50 external")
    parser.add_argument("--limit", type=int, default=1, help="Per type (Internal + External); use 1 for safe test")
    parser.add_argument(
        "--offset",
        type=int,
        default=settings.engagement_test_offset,
        help="Skip first N per type (50 = next batch after first 50)",
    )
    parser.add_argument("--channel", choices=["WhatsApp", "SMS", "Email"], default="WhatsApp")
    parser.add_argument("--all-channels", action="store_true", help="Run WhatsApp, SMS, Email")
    parser.add_argument("--live", action="store_true", help="Send for real")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default if --live omitted)")
    args = parser.parse_args()

    dry_run = not args.live if not args.dry_run else True
    if args.live and args.dry_run:
        dry_run = True

    db = MongoDatabase()
    counts = _count_records(db)
    print("Mongo counts:", json.dumps(counts, indent=2))
    print(
        "Test mode:",
        settings.engagement_test_mode,
        "| WhatsApp override:",
        settings.engagement_whatsapp_override_phone or "(none)",
    )
    print(
        "SMS pool:",
        settings.engagement_sms_test_phones or "(record phones)",
        "| Email pool:",
        settings.engagement_email_test_addresses or "(record emails)",
    )
    print(f"Batch: offset={args.offset} limit={args.limit} per type -> up to {args.limit * 2} total")
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}\n")

    service = EngagementService(db)
    channels = ["WhatsApp", "SMS", "Email"] if args.all_channels else [args.channel]

    summary: dict[str, dict] = {}
    for ch in channels:
        print(f"=== {ch} ===")
        out = _run_channel(
            service,
            channel=ch,
            limit=args.limit,
            offset=args.offset,
            dry_run=dry_run,
        )
        summary[ch] = {
            "total": out.get("total"),
            "succeeded": out.get("succeeded"),
            "failed": out.get("failed"),
            "skipped": out.get("skipped"),
            "by_channel": out.get("by_channel"),
        }
        print(json.dumps(summary[ch], indent=2))
        print()

    print("=== Summary ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
