# External Lead Analytics

Deterministic CRM analytics for external acquisition leads — **no banking transaction data**.

## Prerequisites

1. `POST /api/external/import`
2. `POST /api/external/enrich`

## Analytics modules

| Module | Engine | Metrics |
|--------|--------|---------|
| Lead Behaviour | `lead_behaviour_analytics.py` | Campaign engagement, referral quality, digital/communication readiness, consent strength, marketing responsiveness, persona confidence |
| Financial Capacity | `financial_capacity_analytics.py` | Financial capacity score, repayment capacity, income stability, EMI burden, credit quality, affordability |
| Lead Quality | `lead_quality_analytics.py` | Lead quality score, conversion readiness, qualification status, KYC readiness, priority level, sales readiness |

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/external/analytics/build/{lead_id}` | Compute analytics for one lead |
| POST | `/api/external/analytics/build-all` | Batch analytics for all enriched leads |
| GET | `/api/external/analytics/{lead_id}` | Retrieve analytics profile |

## Example response

```json
{
  "lead_quality_score": 91,
  "financial_capacity_score": 86,
  "campaign_engagement_score": 72,
  "digital_readiness_score": 94,
  "communication_readiness_score": 88,
  "qualification_status": "Qualified",
  "priority_level": "High",
  "preferred_channel": "Voice",
  "preferred_contact_time": "Evening (18:00–20:00)"
}
```

## Persistence

**`external_customer_profile`** (new columns):
- `campaign_engagement_score`, `digital_readiness_score`, `communication_readiness_score`
- `financial_capacity_score`, `estimated_repayment_capacity`
- `lead_quality_score`, `qualification_status`, `priority_level`

**`lead_feature_store`** (EAV feature store):
- `lead_score`, `financial_capacity_score`, `campaign_engagement_score`
- `digital_readiness_score`, `lead_quality_score`, `credit_quality`
- `preferred_channel`, `preferred_contact_time`

## What is NOT included

No shopping, travel, food, or transaction analytics — those require real banking transactions and belong only to internal Customer360.

## Workflow

```bash
curl -X POST http://localhost:8000/api/external/import
curl -X POST http://localhost:8000/api/external/enrich
curl -X POST http://localhost:8000/api/external/analytics/build-all
curl http://localhost:8000/api/external/analytics/{lead_id}
```
