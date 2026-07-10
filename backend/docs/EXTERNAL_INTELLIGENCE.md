# External Customer Intelligence Layer

Enterprise CRM pipeline for importing, enriching, and scoring external acquisition leads.

## Overview

The External Customer Intelligence Layer is a **separate module** from Phase 2 Customer360 analytics. It provides:

| Audience | Profile table |
|----------|---------------|
| Internal bank customers | `customer_360_profile` |
| External acquisition leads | `external_customer_profile` |

Future Decision Engine, Voice AI, Campaign, and Recommendation engines can consume **both** profile types.

## Architecture

```
external_leads_1000.xlsx
        │
        ▼
  ExcelImporter          ── validate, normalize, UUID
        │
        ▼
  external_leads         ── CRM lead master
        │
        ▼
  LeadEnrichmentEngine   ── deterministic enrichment
  LeadScoringEngine      ── composite score 0–100
        │
        ▼
  external_customer_profile
```

## Input file

Default path: `external_leads_1000.xlsx` (project root)

Excel columns: `LeadID`, `Name`, `Occupation`, `EstimatedIncome`, `Employer`, `ReferralSource`, `Campaign`, `Consent`, `CreditScore`, `City`

Fields not in Excel (phone, email, age, gender, state) are **deterministically derived** at import time.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/external/import` | Import Excel into `external_leads` |
| POST | `/api/external/enrich` | Enrich all leads → `external_customer_profile` |
| GET | `/api/external/leads` | List imported leads (`limit`, `offset`) |
| GET | `/api/external/profile/{lead_id}` | Get enriched profile |

## Typical workflow

```bash
# 1. Start the API
uvicorn app.main:app --reload

# 2. Import leads
curl -X POST http://localhost:8000/api/external/import

# 3. Enrich all leads
curl -X POST http://localhost:8000/api/external/enrich

# 4. List leads
curl http://localhost:8000/api/external/leads?limit=10

# 5. Get enriched profile (use lead_id UUID from list response)
curl http://localhost:8000/api/external/profile/{lead_id}
```

## Lead scoring factors

Composite score (0–100) from:

- Estimated income (max 25)
- Credit score (max 20)
- Occupation tier (max 15)
- Employer quality (max 10)
- Campaign value (max 10)
- Marketing consent (max 5)
- Relationship potential (max 10)
- Financial stability (max 5)

## Customer personas

Automatic segmentation: High Net Worth, Salary Elite, Premium, Business Owner, Young Professional, Family, Student, Retired, Mass Market.

## Module layout

```
app/external/
  excel_importer.py           # Excel read, validate, normalize
  lead_enrichment.py          # Enrichment + segmentation
  lead_scoring.py             # Lead score engine
  external_import_service.py  # Import orchestration
  external_enrichment_service.py

app/models/
  external_lead.py
  external_customer_profile.py

app/repositories/
  external_lead_repository.py
  external_profile_repository.py

app/routers/
  external_router.py

migrations/
  008_external_customer_intelligence.sql
```

## Configuration

Set custom Excel path via environment or `.env`:

```
EXTERNAL_LEADS_EXCEL_PATH=C:\path\to\leads.xlsx
```

Or use default: `{project_root}/external_leads_1000.xlsx`
