# Behaviour Analytics Summary Layer

Enterprise aggregation and standardization layer that exposes three normalized scores (0–100) for both internal customers and external leads. **No new analytics engines** — this module only combines values already computed by prior Customer360 and External Lead modules.

## Purpose

Standardize behaviour outputs for the next architecture layer: **Repayment Capacity Prediction**.

## Standardized Outputs

| Score | Description |
|-------|-------------|
| `financial_health_score` | Aggregated financial wellness |
| `repayment_behaviour_score` | Aggregated repayment capacity signals |
| `digital_engagement_score` | Aggregated digital and channel engagement |

## Internal Customer Inputs

### Financial Health Score
- Customer Health (`customer_health_score`)
- Financial Stability (inverse of `financial_stress_score`)
- Savings Ratio (`monthly_savings` / `monthly_income`)
- Cash Flow (`cash_flow_score`)
- Liquidity (`liquidity_score`)
- Debt (inverse of `debt_ratio`)

### Repayment Behaviour Score
- Income Regularity (`income_regularity_score`)
- Savings Behaviour (derived from savings ratio)
- EMI Burden (inverse of `emi_burden`)
- Cash Flow (`cash_flow_score`)
- Expense Stability (`expense_stability_score`)
- Digital Payment Ratio (`digital_payment_ratio`)

### Digital Engagement Score
- Digital Adoption (`digital_adoption_score`)
- Voice / SMS / WhatsApp / Email readiness scores
- UPI and Internet Banking usage (from `feature_store` transaction counts)

## External Lead Inputs

### Financial Health Score
- Financial Capacity (`financial_capacity_score`)
- Lead Quality (`lead_quality_score`)
- Income Confidence (`income_confidence_score`)

### Repayment Behaviour Score
- Financial Capacity
- Estimated Repayment (normalized from `estimated_repayment_capacity`)
- Income Stability (proxy: `income_confidence_score`)
- Credit Quality (`lead_feature_store`)
- Lead Authenticity (`lead_authenticity_score`)

### Digital Engagement Score
- Digital Readiness (`digital_readiness_score`)
- Communication Readiness (`communication_readiness_score`)
- Campaign Engagement (`campaign_engagement_score`)
- Preferred Channel (mapped to engagement score)

## Persistence

| Table | New Columns |
|-------|-------------|
| `customer_360_profile` | `financial_health_score`, `repayment_behaviour_score`, `digital_engagement_score` |
| `external_customer_profile` | same |
| `feature_store` | summary features (`source_module = behaviour_summary`) |
| `lead_feature_store` | summary features (`source_module = behaviour_summary`) |

Migration: `migrations/011_behaviour_analytics_summary.sql`

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/behaviour/build/{profile_id}` | Build summary for one profile (internal or external) |
| `POST` | `/api/behaviour/build-all` | Build summaries for all profiles |
| `GET` | `/api/behaviour/{profile_id}` | Return standardized summary |

### Example Response

```json
{
  "profile_id": "…",
  "profile_type": "Internal",
  "entity_id": "…",
  "financial_health_score": 91.00,
  "repayment_behaviour_score": 88.00,
  "digital_engagement_score": 95.00
}
```

## Module Layout

```
app/behaviour_summary/
  internal_aggregator.py   # Weighted aggregation for internal profiles
  external_aggregator.py   # Weighted aggregation for external profiles
  behaviour_summary_service.py
app/routers/behaviour_summary_router.py
```

## Prerequisites

Run upstream analytics before building behaviour summaries:

**Internal:** Customer360 build → financial → transaction → behaviour → relationship → channel → customer-health

**External:** enrich → analytics build → intelligence build

## Tests

```bash
python -m unittest tests.test_behaviour_summary -v
python -m unittest tests.test_behaviour_summary_api -v
```
