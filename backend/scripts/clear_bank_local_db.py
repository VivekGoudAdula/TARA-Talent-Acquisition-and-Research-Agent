"""Wipe local bank SQLite/Postgres demo data — project uses MongoDB only."""

from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parent.parent / "bank" / "bank" / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.database.postgres import SessionLocal


TABLES = [
    "sms_logs",
    "transcripts",
    "call_logs",
    "calls",
    "transactions",
    "tickets",
    "loans",
    "cards",
    "accounts",
    "customers",
    "agent_config_revisions",
    "agent_configs",
    "workflows",
    "custom_tools",
    "campaign_types",
    "sarvam_voices",
]


def main() -> None:
    db = SessionLocal()
    try:
        for table in TABLES:
            try:
                db.execute(text(f"DELETE FROM {table}"))
                print(f"cleared {table}")
            except Exception as exc:
                print(f"skip {table}: {exc}")
        db.commit()
        print("Local bank database cleared.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
