#!/usr/bin/env python3
"""
Load customers 51-100 (batch 2) and send sample engagement:
  - 1 Internal + 1 External only (not 50 messages to same number)
  - WhatsApp -> ENGAGEMENT_WHATSAPP_OVERRIDE_PHONE (2 messages max)
  - SMS Internal -> first test phone, External -> second test phone
  - Email Internal -> first test email, External -> second test email

Usage:
  python scripts/load_batch2_sample_engagement.py --dry-run
  python scripts/load_batch2_sample_engagement.py --live --skip-slice --skip-load --skip-pipeline
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

BATCH_DIR = PROJECT_ROOT / "data" / "excel_batch_50_50"
BATCH_OFFSET = 50
BATCH_LIMIT = 50
SAMPLE_LIMIT = 1  # per type: 1 internal + 1 external


def _run(cmd: list[str], env: dict | None = None) -> None:
    print(f"\n>> {' '.join(cmd)}\n", flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, env=env or os.environ.copy(), check=True)


def _batch_env() -> dict:
    env = os.environ.copy()
    env["EXPECTED_CUSTOMER_COUNT"] = str(BATCH_LIMIT)
    env["EXPECTED_LEAD_COUNT"] = str(BATCH_LIMIT)
    env["CUSTOMER_MASTER_EXCEL_PATH"] = str(BATCH_DIR / "customer_master.xlsx")
    env["TRANSACTION_HISTORY_EXCEL_PATH"] = str(BATCH_DIR / "transaction_history.xlsx")
    env["LOAN_HISTORY_EXCEL_PATH"] = str(BATCH_DIR / "loan_history.xlsx")
    env["DIGITAL_ACTIVITY_EXCEL_PATH"] = str(BATCH_DIR / "digital_activity.xlsx")
    env["EXTERNAL_LEADS_EXCEL_PATH"] = str(BATCH_DIR / "external_leads.xlsx")
    return env


def _counts() -> dict:
    from app.db.mongo import MongoDatabase

    db = MongoDatabase()
    return {
        "internal": db.customers.count_documents({}),
        "external": db.external_leads.count_documents({}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load batch 2 (51-100) + sample engagement")
    parser.add_argument("--dry-run", action="store_true", help="Preview outreach only")
    parser.add_argument("--live", action="store_true", help="Send real WhatsApp/SMS/Email")
    parser.add_argument("--skip-slice", action="store_true")
    parser.add_argument("--skip-load", action="store_true")
    parser.add_argument("--skip-pipeline", action="store_true")
    parser.add_argument(
        "--engage-offset",
        type=int,
        default=BATCH_OFFSET,
        help="Engagement offset per type (50 = pick from batch 2)",
    )
    args = parser.parse_args()

    live = args.live and not args.dry_run

    print("Counts before:", json.dumps(_counts(), indent=2))
    db_counts = _counts()

    if not args.skip_slice:
        _run(
            [
                sys.executable,
                "scripts/slice_excel_batch.py",
                "--offset",
                str(BATCH_OFFSET),
                "--limit",
                str(BATCH_LIMIT),
                "--output-dir",
                str(BATCH_DIR),
            ]
        )

    if not args.skip_load:
        subset_dir = PROJECT_ROOT / "data" / "excel_subset_50"
        if db_counts.get("internal", 0) < BATCH_OFFSET and subset_dir.is_dir():
            print("Restoring batch 1 internal (rows 1-50)...")
            env1 = _batch_env()
            env1["CUSTOMER_MASTER_EXCEL_PATH"] = str(subset_dir / "customer_master.xlsx")
            env1["TRANSACTION_HISTORY_EXCEL_PATH"] = str(subset_dir / "transaction_history.xlsx")
            env1["LOAN_HISTORY_EXCEL_PATH"] = str(subset_dir / "loan_history.xlsx")
            env1["DIGITAL_ACTIVITY_EXCEL_PATH"] = str(subset_dir / "digital_activity.xlsx")
            env1["EXTERNAL_LEADS_EXCEL_PATH"] = str(subset_dir / "external_leads.xlsx")
            _run([sys.executable, "scripts/load_excel_to_mongo.py"], env=env1)

        print("Appending batch 2 (rows 51-100)...")
        _run(
            [sys.executable, "scripts/load_excel_to_mongo.py", "--append"],
            env=_batch_env(),
        )

    if not args.skip_pipeline:
        _run([sys.executable, "scripts/run_pre_xai_pipeline.py"], env=_batch_env())

    print("\nCounts after load/pipeline:", json.dumps(_counts(), indent=2))

    engage_cmd = [
        sys.executable,
        "scripts/run_engagement_test_batch.py",
        "--limit",
        str(SAMPLE_LIMIT),
        "--offset",
        str(args.engage_offset),
        "--all-channels",
    ]
    if live:
        engage_cmd.append("--live")
    else:
        engage_cmd.append("--dry-run")

    _run(engage_cmd)

    print("\nDone.")
    print(f"  Loaded batch 2: rows {BATCH_OFFSET + 1}-{BATCH_OFFSET + BATCH_LIMIT}")
    print(f"  Engagement: {SAMPLE_LIMIT} internal + {SAMPLE_LIMIT} external from offset {args.engage_offset}")
    print(f"  Mode: {'LIVE' if live else 'DRY-RUN'}")


if __name__ == "__main__":
    main()
