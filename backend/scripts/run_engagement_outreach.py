#!/usr/bin/env python3
"""Run multi-channel engagement outreach (dry-run or live)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import MongoDatabase
from app.engagement.service import EngagementService
from app.schemas.engagement import OutreachRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Tara multi-channel engagement outreach")
    parser.add_argument(
        "--channel",
        choices=["Voice", "WhatsApp", "SMS", "Email"],
        default="WhatsApp",
        help="Outreach channel (default: WhatsApp). Use Voice only for bank/bank dialer.",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--profile-types", default="External")
    parser.add_argument("--min-conversion", type=float, default=None)
    parser.add_argument("--live", action="store_true", help="Send for real (default is dry-run)")
    parser.add_argument("--start-voice", action="store_true", help="Start voice dialer (Voice only)")
    args = parser.parse_args()

    types = [p.strip() for p in args.profile_types.split(",") if p.strip()]
    service = EngagementService(MongoDatabase())

    print("Channel status:", json.dumps(service.channel_status().channels, indent=2))

    request = OutreachRequest(
        channel=args.channel,
        limit=args.limit,
        offset=args.offset,
        profile_types=types,
        min_conversion_probability=args.min_conversion,
        dry_run=not args.live,
        start_voice_campaign=args.start_voice,
        require_consent=False,
    )
    result = service.run_outreach(request)
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
