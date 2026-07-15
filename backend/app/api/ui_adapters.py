"""UI-friendly response adapters — map MongoDB / service shapes to frontend contracts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def adapt_platform_counts(db: Any) -> dict[str, int]:
    """Collection counts keyed for the admin dashboard KPIs."""
    internal = db.customers.count_documents({})
    external = db.external_leads.count_documents({})
    profiles_360 = db.customer_360_profile.count_documents({})
    feature_store = db.feature_store.count_documents({})
    lead_feature_store = db.lead_feature_store.count_documents({})
    training_dataset = db.training_dataset.count_documents({})
    explainability = db.explainability_reports.count_documents({})

    return {
        # Legacy keys (kept for backward compatibility)
        "internal_customers": internal,
        "external_leads": external,
        "enriched_profiles": db.external_customer_profile.count_documents({}),
        "conversion_scores": db.conversion_predictions.count_documents({}),
        "engagement_events": db.engagement_events.count_documents({}),
        "onboarding_journeys": db.onboarding_journeys.count_documents({}),
        "rm_handoffs": db.rm_handoffs.count_documents({}),
        "pipeline_runs": db.pipeline_runs.count_documents({}),
        # Frontend dashboard keys
        "customers": internal,
        "customer_360_profile": profiles_360,
        "feature_store": feature_store,
        "lead_feature_store": lead_feature_store,
        "training_dataset": training_dataset,
        "explainability_reports": explainability,
        "repayment_predictions": db.repayment_predictions.count_documents({}),
        "product_recommendations": db.product_recommendations.count_documents({}),
        "ml_model_runs": db.ml_model_runs.count_documents({}),
    }


def adapt_pipeline_status(counts: dict[str, int], recent_runs: list[dict[str, Any]]) -> dict[str, Any]:
    latest = recent_runs[0] if recent_runs else None
    if latest:
        status = "completed" if latest.get("success", True) else "failed"
        return {
            "status": status,
            "last_run_id": latest.get("run_id"),
            "pipeline_type": latest.get("pipeline_type"),
            "started_at": latest.get("started_at"),
            "completed_at": latest.get("completed_at"),
            "success": latest.get("success"),
        }
    if counts.get("customer_360_profile", 0) > 0:
        return {"status": "completed", "detail": "Profiles available in MongoDB"}
    return {"status": "pending", "detail": "No pipeline runs recorded yet"}


def adapt_recent_lead_row(lead: dict[str, Any], conversion_probability: Any = None) -> dict[str, Any]:
    eid = _str_id(lead.get("lead_id"))
    return {
        "entity_id": eid,
        "lead_id": eid,
        "name": lead.get("full_name"),
        "full_name": lead.get("full_name"),
        "phone": lead.get("phone_number"),
        "email": lead.get("email"),
        "city": lead.get("city"),
        "campaign": lead.get("campaign"),
        "source": lead.get("referral_source"),
        "referral_source": lead.get("referral_source"),
        "lead_status": lead.get("lead_status"),
        "status": lead.get("lead_status"),
        "customer_type": "External",
        "conversion_probability": conversion_probability,
        "created_at": lead.get("created_at") or lead.get("lead_created_date"),
    }


def _coalesce_num(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _num(data.get(key))
        if value is not None:
            return value
    return None


def _repayment_tier_from_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def _static_recommended_product(row: dict[str, Any], profile: dict[str, Any] | None = None) -> str:
    """Deterministic product label for list views when ML scoring has not run yet."""
    credit = row.get("credit_score") or 0
    health = row.get("financial_health_score") or 0
    engagement = row.get("engagement_score") or 0
    segment = str(row.get("segment") or (profile or {}).get("customer_segment") or "").lower()
    repayment = str(row.get("repayment_label") or row.get("repayment_capacity") or "").lower()

    if credit >= 750 or "premium" in segment or "hni" in segment:
        return "Premium Savings Plus"
    if repayment in ("very high", "high") and health >= 65:
        return "Personal Loan"
    if health >= 70 and credit >= 680:
        return "Gold Credit Card"
    if engagement >= 55:
        return "Digital Savings Account"
    if credit >= 600:
        return "Recurring Deposit"
    return "Secured Credit Card"


def adapt_crm_internal_row(cust: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    first = (cust.get("first_name") or "").strip()
    last = (cust.get("last_name") or "").strip()
    full_name = f"{first} {last}".strip()
    cid = _str_id(cust.get("customer_id"))

    row: dict[str, Any] = {
        "entity_id": cid,
        "customer_id": cid,
        "id": cid,
        "name": full_name,
        "full_name": full_name,
        "phone": cust.get("phone_number"),
        "email": cust.get("email"),
        "city": cust.get("city"),
        "conversion_probability": None,
        "journey_status": "internal",
        "customer_type": "Internal",
        "pipeline_type": "Internal",
    }

    if profile:
        row["segment"] = profile.get("customer_segment") or "Standard"
        risk = _num(profile.get("risk_score"))
        row["credit_score"] = int(round(risk * 9)) if risk is not None else None
        row["financial_health_score"] = _coalesce_num(
            profile,
            "financial_health_score",
            "customer_health_score",
            "cash_flow_score",
            "liquidity_score",
        )
        row["engagement_score"] = _coalesce_num(
            profile,
            "digital_engagement_score",
            "digital_adoption_score",
            "digital_banking_score",
            "channel_engagement_score",
        )
        row["repayment_label"] = profile.get("repayment_capacity_predicted")
        row["repayment_capacity"] = profile.get("repayment_capacity_predicted")
        row["recommended_product"] = profile.get("top_recommended_product")
        if not row["repayment_label"]:
            repay_score = _coalesce_num(
                profile,
                "repayment_behaviour_score",
                "cash_flow_score",
                "customer_health_score",
            )
            row["repayment_label"] = _repayment_tier_from_score(repay_score)
            row["repayment_capacity"] = row["repayment_label"]

    if not row.get("recommended_product"):
        row["recommended_product"] = _static_recommended_product(row, profile)

    return row


def adapt_customer360_view(
    profile: Any,
    *,
    full_name: str | None = None,
    customer_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Nest flat Customer360 fields for the React detail view."""
    data = profile.__dict__ if hasattr(profile, "__dict__") else dict(profile)
    if customer_doc and not full_name:
        first = (customer_doc.get("first_name") or "").strip()
        last = (customer_doc.get("last_name") or "").strip()
        full_name = f"{first} {last}".strip() or None

    risk = _num(data.get("risk_score"))
    credit_score = int(round(risk * 9)) if risk is not None else None

    base = {k: (str(v) if isinstance(v, (UUID, Decimal)) else v) for k, v in data.items() if not k.startswith("_")}
    base.update(
        {
            "personal_info": {
                "full_name": full_name,
                "gender": data.get("gender"),
                "age": data.get("age"),
                "occupation": data.get("occupation"),
                "monthly_income": _num(data.get("monthly_income")),
                "city": data.get("city"),
                "state": data.get("state"),
                "preferred_language": data.get("preferred_language"),
            },
            "intelligence_scores": {
                "credit_score": credit_score,
                "financial_health_score": _coalesce_num(
                    data,
                    "financial_health_score",
                    "customer_health_score",
                    "cash_flow_score",
                    "liquidity_score",
                ),
                "repayment_behaviour_score": _coalesce_num(
                    data,
                    "repayment_behaviour_score",
                    "cash_flow_score",
                ),
                "digital_adoption_score": _coalesce_num(
                    data,
                    "digital_adoption_score",
                    "digital_banking_score",
                    "digital_engagement_score",
                ),
                "relationship_strength_score": _num(data.get("relationship_strength_score")),
            },
            "system_alerts": data.get("system_alerts") or [],
        }
    )
    return base


def adapt_external_profile_view(profile_response: dict[str, Any]) -> dict[str, Any]:
    """Add lead_profile / enrichment_status aliases expected by the UI."""
    lead = profile_response.get("lead") or {}
    return {
        **profile_response,
        "lead_profile": profile_response.get("lead_profile") or lead,
        "enrichment_status": profile_response.get("enrichment_status")
        or {
            "status": lead.get("lead_status") or ("Enriched" if profile_response.get("profile_id") else "Pending"),
            "last_processed": profile_response.get("last_updated"),
        },
    }


def adapt_explainability_report(report: dict[str, Any]) -> dict[str, Any]:
    explanation = report.get("explanation") or {}
    summary = explanation.get("summary") or report.get("llm_summary") or ""
    raw_codes = report.get("reason_codes") or explanation.get("reason_codes") or []
    structured: list[dict[str, str]] = []
    for idx, item in enumerate(raw_codes):
        if isinstance(item, dict):
            structured.append(
                {
                    "code": str(item.get("code", idx + 1)),
                    "feature": str(item.get("feature", item.get("name", "Feature"))),
                    "explanation": str(item.get("explanation", item.get("detail", ""))),
                }
            )
        else:
            text = str(item)
            match = re.match(r"^([A-Z0-9_]+):\s*(.+)$", text)
            if match:
                structured.append({"code": match.group(1), "feature": match.group(1), "explanation": match.group(2)})
            else:
                structured.append({"code": str(idx + 1), "feature": "Insight", "explanation": text})
    return {**report, "narrative": summary, "reason_codes": structured}


def adapt_channel_status(channels: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, str]] = []
    for name, meta in (channels or {}).items():
        if not isinstance(meta, dict):
            items.append({"channel": name.lower(), "status": str(meta)})
            continue
        if meta.get("configured") is False:
            status = "not configured"
        elif meta.get("reachable") is False:
            status = "unreachable"
        elif meta.get("simulated"):
            status = "simulated"
        else:
            status = "active"
        items.append({"channel": name.lower(), "status": status})
    return {"channels": items, "channels_by_name": channels}


def adapt_engagement_lead(record: dict[str, Any]) -> dict[str, Any]:
    prob = _num(record.get("conversion_probability"))
    return {
        **record,
        "full_name": record.get("full_name") or record.get("name"),
        "phone_number": record.get("phone_number") or record.get("phone"),
        "lead_id": record.get("lead_id") or record.get("entity_id"),
        "profile_type": record.get("profile_type") or record.get("entity_type"),
        "conversion_probability": prob,
    }


def adapt_financial_profile(data: dict[str, Any], profile_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = profile_doc or {}
    monthly_income = _num(data.get("monthly_income")) or _num(doc.get("monthly_income"))
    annual = _num(doc.get("annual_income"))
    if annual is None and monthly_income is not None:
        annual = monthly_income * 12
    emi = _num(data.get("emi_burden")) or 0
    return {
        **data,
        "monthly_income": monthly_income,
        "annual_income": annual,
        "estimated_net_worth": _num(doc.get("average_balance")),
        "emi_burden_ratio": emi / 100 if emi and emi > 1 else emi,
        "savings_balance": _num(doc.get("monthly_savings")),
        "investments_balance": _num(doc.get("investment_ratio")),
        "total_loan_outstanding": _num(doc.get("debt_ratio")),
        "repayment_capacity_class": doc.get("repayment_capacity_predicted"),
    }


def adapt_behaviour_profile(data: dict[str, Any], profile_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = profile_doc or {}
    digital = _num(doc.get("digital_adoption_score")) or _num(data.get("digital_banking_score"))
    tier = "High" if (digital or 0) >= 70 else "Medium" if (digital or 0) >= 40 else "Low"
    return {
        **data,
        "digital_adoption_tier": tier,
        "monthly_login_frequency": doc.get("monthly_login_frequency"),
        "preferred_transaction_channel": doc.get("preferred_channel"),
        "last_transaction_date": doc.get("last_transaction_date"),
        "email_open_rate": doc.get("email_open_rate"),
        "sms_click_rate": doc.get("sms_click_rate"),
        "social_media_click_count": doc.get("social_media_click_count"),
        "last_call_outcome": doc.get("last_call_outcome"),
    }


def adapt_relationship_profile(data: dict[str, Any]) -> dict[str, Any]:
    tenure_years = _num(data.get("relationship_age")) or 0
    return {
        **data,
        "tenure_months": int(tenure_years * 12),
        "active_products_count": data.get("number_of_products"),
        "clv_score": _num(data.get("estimated_customer_value")),
        "relationship_strength_level": data.get("relationship_tier"),
        "risk_rating": data.get("relationship_tier"),
        "churn_probability": _num(data.get("relationship_stability")),
        "nps_score": _num(data.get("engagement_score")),
    }


def adapt_external_analytics(data: dict[str, Any]) -> dict[str, Any]:
    fin = data.get("financial_capacity") or {}
    conv = _num(data.get("conversion_probability"))
    if conv is None:
        readiness = _num(data.get("conversion_readiness"))
        conv = readiness / 100 if readiness is not None and readiness > 1 else readiness
    return {
        **data,
        "credit_score_band": data.get("credit_score_band") or data.get("credit_quality"),
        "income_category": data.get("income_category") or fin.get("income_segment"),
        "estimated_debt_capacity": _num(data.get("estimated_debt_capacity") or data.get("estimated_repayment_capacity")),
        "conversion_probability": conv,
        "best_contact_channel": data.get("best_contact_channel") or data.get("preferred_channel"),
        "recommended_campaign": data.get("recommended_campaign"),
    }


def adapt_external_intelligence(data: dict[str, Any], lead: dict[str, Any] | None = None) -> dict[str, Any]:
    lead = lead or {}
    missing = data.get("kyc_missing_items") or []
    if isinstance(missing, str):
        try:
            missing = json.loads(missing)
        except json.JSONDecodeError:
            missing = [missing] if missing else []
    return {
        **data,
        "kyc_missing_items": missing,
        "fraud_screening_result": data.get("fraud_risk") or (data.get("fraud_screening") or {}).get("fraud_risk"),
        "reported_income": _num(lead.get("estimated_income")),
        "income_confidence_score": _num(data.get("income_confidence_score")),
        "income_verification_method": (data.get("income_confidence") or {}).get("income_confidence_level"),
    }


def is_regression_test_metrics(test_metrics: dict[str, Any]) -> bool:
    """True when metrics look like a regression model (MAE/R²), not classification."""
    if not test_metrics:
        return False
    if test_metrics.get("accuracy") is not None or test_metrics.get("f1_macro") is not None:
        return False
    return test_metrics.get("r2") is not None or test_metrics.get("mae") is not None


def regression_metrics_for_ui(test_metrics: dict[str, Any]) -> dict[str, Any]:
    """Expose regression metrics for UI (target scale 0–100 percentage points)."""
    return {
        "model_type": "regression",
        "mae": float(test_metrics.get("mae", 0)),
        "rmse": float(test_metrics.get("rmse", 0)),
        "r2": float(test_metrics.get("r2", 0)),
    }


def classification_metrics_for_ui(test_metrics: dict[str, Any]) -> dict[str, Any]:
    """Expose classification metrics for UI."""
    return {
        "model_type": "classification",
        "accuracy": test_metrics.get("accuracy"),
        "f1": test_metrics.get("f1_macro") or test_metrics.get("f1"),
        "roc_auc": test_metrics.get("roc_auc"),
    }


def model_info_from_db_run(run: dict[str, Any]) -> dict[str, Any]:
    test_metrics = run.get("test_metrics") or {}
    if isinstance(test_metrics, str):
        try:
            test_metrics = json.loads(test_metrics)
        except json.JSONDecodeError:
            test_metrics = {}
    if is_regression_test_metrics(test_metrics):
        ui_metrics = regression_metrics_for_ui(test_metrics)
    else:
        ui_metrics = classification_metrics_for_ui(test_metrics)
    created = run.get("created_at")
    feature_importance = run.get("feature_importance") or {}
    if not feature_importance:
        fi_path = run.get("feature_importance_path")
        if fi_path:
            try:
                from pathlib import Path

                path = Path(fi_path)
                if path.is_file():
                    feature_importance = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                feature_importance = {}
    return {
        "trained": True,
        "algorithm": run.get("best_model") or run.get("model_name"),
        "version": "1.0.0",
        "last_trained": created.isoformat() if isinstance(created, datetime) else created,
        "train_samples": run.get("train_size") or run.get("records_used") or 0,
        "test_samples": run.get("test_size") or 0,
        "metrics": ui_metrics,
        "feature_importance": feature_importance,
    }
