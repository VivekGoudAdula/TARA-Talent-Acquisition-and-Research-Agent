#!/usr/bin/env python3
"""Send rich WhatsApp messages — welcome, menu, carousel, buttons."""

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

MESSAGE_TYPES = ["welcome", "main_menu", "loan_media", "loan_carousel", "preapproved_buttons", "credit_card_offer", "text"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Send rich WhatsApp message types")
    parser.add_argument("--type", required=True, choices=MESSAGE_TYPES, dest="message_type")
    parser.add_argument("--phone", required=True, help="e.g. +918897371942")
    parser.add_argument("--name", default="Customer")
    parser.add_argument("--live", action="store_true", help="Actually send")
    args = parser.parse_args()

    service = EngagementService(MongoDatabase())
    request = CustomSendRequest(
        channel="WhatsApp",
        phone=args.phone,
        name=args.name,
        whatsapp_message_type=args.message_type,
        use_tara_intelligence=True,
        dry_run=not args.live,
    )
    result = service.send_custom(request)
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
