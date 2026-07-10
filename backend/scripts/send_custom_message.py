#!/usr/bin/env python3
"""Send one custom WhatsApp/SMS message — for sandbox testing or single outreach."""

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
from app.schemas.engagement import CustomSendRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send custom WhatsApp/SMS with Tara personalization"
    )
    parser.add_argument("--channel", default="WhatsApp", choices=["WhatsApp", "SMS", "Email"])
    parser.add_argument("--phone", default=None, help="e.g. +918897371942 or 8897371942")
    parser.add_argument("--email", default=None, help="Recipient email (required for Email channel)")
    parser.add_argument("--name", default="Customer")
    parser.add_argument("--message", default=None, help="Override message text (optional)")
    parser.add_argument(
        "--whatsapp-type",
        default=None,
        choices=["welcome", "main_menu", "loan_media", "loan_carousel", "preapproved_buttons", "credit_card_offer", "text"],
        help="Rich WhatsApp message type",
    )
    parser.add_argument("--live", action="store_true", help="Actually send (default: preview only)")
    parser.add_argument(
        "--no-intel",
        action="store_true",
        help="Skip Tara ML product/talking-points (plain message only)",
    )
    args = parser.parse_args()

    if args.channel == "Email" and not args.email:
        parser.error("--email is required when channel is Email")
    if not args.phone and args.channel != "Email":
        parser.error("--phone is required for SMS/WhatsApp")

    service = EngagementService(MongoDatabase())
    request = CustomSendRequest(
        channel=args.channel,
        phone=args.phone or "",
        email=args.email,
        name=args.name,
        message=args.message,
        use_tara_intelligence=not args.no_intel,
        whatsapp_message_type=args.whatsapp_type,
        dry_run=not args.live,
    )
    result = service.send_custom(request)
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
