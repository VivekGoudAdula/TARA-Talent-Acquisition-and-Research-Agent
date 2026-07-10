# External Lead Intelligence (Final Layer)

Enterprise validation, authenticity, fraud screening, income confidence, and KYC readiness for external leads.

## Engines

| Engine | File | Output |
|--------|------|--------|
| Lead Authenticity | `lead_authenticity_engine.py` | `lead_authenticity_score` (0–100), reason codes |
| Income Confidence | `income_confidence_engine.py` | `income_confidence_score`, `income_confidence_level` |
| Fraud Screening | `fraud_screening_engine.py` | `fraud_score`, `fraud_risk`, `fraud_reason_codes` |
| KYC Readiness | `kyc_readiness_engine.py` | `kyc_readiness`, `kyc_missing_items` |

**Input only:** `external_leads`, `external_customer_profile`, duplicate checks from DB.

**Not included:** AML, ML fraud prediction, fake transactions, shopping/travel scores.

## API

| Method | Path |
|--------|------|
| POST | `/api/external/intelligence/build/{lead_id}` |
| POST | `/api/external/intelligence/build-all` |
| GET | `/api/external/intelligence/{lead_id}` |

## Prerequisites

```bash
curl -X POST http://localhost:8000/api/external/import
curl -X POST http://localhost:8000/api/external/enrich
curl -X POST http://localhost:8000/api/external/analytics/build-all   # optional
curl -X POST http://localhost:8000/api/external/intelligence/build-all
```

## Example response

```json
{
  "lead_authenticity_score": 95,
  "income_confidence_score": 91,
  "income_confidence_level": "High",
  "fraud_score": 8,
  "fraud_risk": "Low",
  "kyc_readiness": "Ready",
  "kyc_missing_items": [],
  "reason_codes": [
    "Valid phone number",
    "Employer information available",
    "Income consistent with occupation",
    "Consent verified"
  ]
}
```

## Persistence

**`external_customer_profile`** — new columns: `lead_authenticity_score`, `income_confidence_score`, `income_confidence_level`, `fraud_score`, `fraud_risk`, `fraud_reason_codes`, `kyc_readiness`, `kyc_missing_items`, `last_validation_timestamp`

**`lead_feature_store`** — `lead_authenticity_score`, `income_confidence_score`, `fraud_score`, `kyc_readiness` (module: `external_lead_intelligence`)

## Migration

`migrations/010_external_lead_intelligence.sql`
