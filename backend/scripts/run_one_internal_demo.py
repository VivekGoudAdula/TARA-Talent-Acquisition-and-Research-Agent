#!/usr/bin/env python3
"""
Run internal intelligence pipeline for ONE customer, then send WhatsApp + SMS + Email.

Default contacts (demo):
  Email:    krishnajai008@gmail.com
  SMS:      +918897371942
  WhatsApp: +918897371942 (Twilio sandbox / ENGAGEMENT_WHATSAPP_OVERRIDE_PHONE)

Usage:
  python scripts/run_one_internal_demo.py
  python scripts/run_one_internal_demo.py --live
  python scripts/run_one_internal_demo.py --customer-id <uuid> --live
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

DEMO_EMAIL = "krishnajai008@gmail.com"
DEMO_PHONE = "+918897371942"


def _pick_customer_id(db, explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    row = db.customers.find_one({}, {"customer_id": 1, "first_name": 1, "last_name": 1})
    if not row:
        raise SystemExit("No internal customers in MongoDB. Load Excel first.")
    return str(row["customer_id"])


def _patch_customer(db, customer_id: str, email: str, phone: str) -> None:
    now = datetime.utcnow()
    db.customers.update_one(
        {"customer_id": customer_id},
        {"$set": {"email": email, "phone_number": phone, "updated_at": now}},
    )
    db.consent.update_one(
        {"customer_id": customer_id},
        {
            "$set": {
                "customer_id": customer_id,
                "marketing_email": True,
                "marketing_sms": True,
                "marketing_voice": True,
                "updated_at": now,
            }
        },
        upsert=True,
    )
    print(f"Patched customer {customer_id} -> {email} / {phone}")


def _run_internal_pipeline(customer_id: str) -> dict:
    from app.dependencies import (
        create_internal_pipeline_orchestrator,
        get_customer_query_repository,
        get_customer360_repository,
        get_feature_store_repository,
        get_pipeline_progress_tracker,
        get_pipeline_validator,
    )
    from app.internal_pipeline.pipeline_service import InternalPipelineService
    from app.utils.database import new_session

    db = new_session()
    try:
        cqr = get_customer_query_repository(db)
        c360 = get_customer360_repository(db)
        fs = get_feature_store_repository(db)
        pipeline = InternalPipelineService(
            cqr,
            c360,
            fs,
            create_internal_pipeline_orchestrator,
            get_pipeline_validator(cqr, c360, fs),
            get_pipeline_progress_tracker(),
            db,
        )
        summary = pipeline.build_one(UUID(customer_id))
        return summary.model_dump()
    finally:
        db.close()


def _run_ml_layers(customer_id: str) -> dict:
    from app.dependencies import (
        get_explainability_service,
        get_external_lead_repository,
        get_external_profile_repository,
        get_feature_store_repository,
        get_lead_feature_store_repository,
        get_ml_scoring_repository,
        get_product_recommendation_service,
        get_repayment_capacity_service,
    )
    from app.repositories.customer360_repository import Customer360Repository
    from app.schemas.explainability import ExplainabilityGenerateRequest
    from app.schemas.product_recommendation import ProductRecommendRequest
    from app.utils.database import new_session

    db = new_session()
    out: dict = {}
    try:
        c360 = Customer360Repository(db)
        profile = c360.get_profile_by_customer_id(UUID(customer_id))
        if not profile:
            out["ml"] = "skipped — no Customer360 profile after pipeline"
            return out

        prod_svc = get_product_recommendation_service(
            customer360_repo=c360,
            external_profile_repo=get_external_profile_repository(db),
            lead_repo=get_external_lead_repository(db),
            feature_repo=get_feature_store_repository(db),
            lead_feature_repo=get_lead_feature_store_repository(db),
            repayment_service=get_repayment_capacity_service(db),
            scoring_repo=get_ml_scoring_repository(db),
        )
        prod = prod_svc.recommend(
            ProductRecommendRequest(profile_id=profile.profile_id, top_n=3)
        )
        out["product_recommendation"] = prod.model_dump()

        expl_svc = get_explainability_service(
            explainability_repo=__import__(
                "app.dependencies", fromlist=["get_explainability_repository"]
            ).get_explainability_repository(db),
            decision_summary_builder=__import__(
                "app.dependencies", fromlist=["get_decision_summary_builder"]
            ).get_decision_summary_builder(db),
        )
        expl = expl_svc.generate(
            ExplainabilityGenerateRequest(customer_id=UUID(customer_id))
        )
        out["explainability"] = expl.model_dump()
    except Exception as exc:
        out["ml_error"] = str(exc)
    finally:
        db.close()
    return out


def _send_engagement(customer_id: str, *, live: bool) -> dict:
    from app.db.mongo import MongoDatabase
    from app.engagement.export_service import EngagementExportService
    from app.engagement.orchestrator import EngagementOrchestrator
    from app.engagement.repository import EngagementRepository

    db = MongoDatabase()
    export = EngagementExportService(db)
    record = export.build_record_for_entity(customer_id, "Internal")
    if not record:
        return {"error": "Could not build engagement record"}

    orch = EngagementOrchestrator(export, EngagementRepository(db))
    results = []
    for channel in ("WhatsApp", "SMS", "Email"):
        r = orch.send_one(record, channel=channel, dry_run=not live)
        results.append(
            {
                "channel": r.channel,
                "success": r.success,
                "recipient": r.recipient,
                "status": r.status,
                "error": r.error,
            }
        )
    return {"entity_id": customer_id, "name": record.name, "results": results}


def _place_voice_call(customer_id: str, phone: str) -> dict:
    from app.engagement.voice_bridge import VoiceBridge, VoiceBridgeError

    bridge = VoiceBridge()
    if not bridge.is_configured:
        return {"error": "VOICE_AGENT_BASE_URL not set"}
    health = bridge.health_check()
    if not health.get("reachable"):
        return {"error": "Voice platform not reachable", "health": health}
    try:
        result = bridge.initiate_call_by_phone(
            phone=phone,
            agent_id="lending_offer_agent",
            entity_id=customer_id,
            entity_type="Internal",
        )
        return {"status": "call_initiated", "health": health, **result}
    except VoiceBridgeError as exc:
        return {"error": str(exc), "health": health}


def main() -> None:
    parser = argparse.ArgumentParser(description="One internal customer pipeline + engagement")
    parser.add_argument("--customer-id", default=None, help="UUID; default = first customer")
    parser.add_argument("--email", default=DEMO_EMAIL)
    parser.add_argument("--phone", default=DEMO_PHONE)
    parser.add_argument("--live", action="store_true", help="Send real WhatsApp/SMS/Email")
    parser.add_argument("--skip-engagement", action="store_true")
    parser.add_argument("--skip-pipeline", action="store_true")
    parser.add_argument("--voice", action="store_true", help="Place AI voice call via bank/Twilio")
    args = parser.parse_args()

    from app.db.mongo import MongoDatabase

    db = MongoDatabase()
    customer_id = _pick_customer_id(db, args.customer_id)
    cust = db.customers.find_one({"customer_id": customer_id}, {"_id": 0})
    print("Customer:", json.dumps(cust, default=str, indent=2))

    _patch_customer(db, customer_id, args.email, args.phone)

    print("\n=== Internal pipeline (build-one) ===")
    if args.skip_pipeline:
        pipeline_result = {"skipped": True}
        print("Skipped (--skip-pipeline)")
    else:
        pipeline_result = _run_internal_pipeline(customer_id)
        print(json.dumps(pipeline_result, indent=2, default=str))

    print("\n=== ML: product recommendation + explainability ===")
    ml_result = _run_ml_layers(customer_id)
    print(json.dumps(ml_result, indent=2, default=str))

    if not args.skip_engagement:
        print(f"\n=== Engagement ({'LIVE' if args.live else 'DRY-RUN'}) ===")
        eng = _send_engagement(customer_id, live=args.live)
        print(json.dumps(eng, indent=2, default=str))

    if args.voice:
        print("\n=== Voice AI callback ===")
        voice = _place_voice_call(customer_id, args.phone)
        print(json.dumps(voice, indent=2, default=str))
        if voice.get("call_sid"):
            print("\nAnswer your phone (+918897371942). Speak in Telugu or English — agent auto-switches.")

    print("\nDone. View thread in CRM 360 or:")
    print(f"  GET /api/engagement/conversations/{customer_id}")


if __name__ == "__main__":
    main()
