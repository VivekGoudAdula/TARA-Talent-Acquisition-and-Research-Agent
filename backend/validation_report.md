# Tara Platform Validation Report

**Generated:** 2026-07-09T09:33:35.351902+00:00
**Overall Health:** 73.5%

## System Health

| Component | Status |
|-----------|--------|
| Database | FAIL |
| Internal | FAIL |
| External | FAIL |
| Customer360 | FAIL |
| Feature Store | FAIL |
| Behaviour Analytics | FAIL |
| Ml | FAIL |
| Repayment Model | PASS |
| Product Recommendation | PASS |
| Lead Conversion | PASS |
| Api | PASS |
| Data Integrity | FAIL |
| End To End Workflow | FAIL |
| Overall Health | 73.5% |

## Category Details

### API — PASS
_Passed: 32, Failed: 0, Warnings: 0, Skipped: 0_

- **[PASS]** Health: HTTP 200
- **[PASS]** Internal pipeline status: HTTP 200
- **[PASS]** Customer360 GET: HTTP 200
- **[PASS]** Transaction Analytics GET: HTTP 200
- **[PASS]** Behaviour Analytics GET: HTTP 200
- **[PASS]** Relationship Analytics GET: HTTP 200
- **[PASS]** Digital Channel Analytics GET: HTTP 200
- **[PASS]** Customer Health GET: HTTP 200
- **[PASS]** Behaviour Summary GET: HTTP 200
- **[PASS]** External leads list: HTTP 200
- **[PASS]** ML dataset GET: HTTP 200
- **[PASS]** ML dataset stats: HTTP 200
- **[PASS]** Repayment model info: HTTP 200
- **[PASS]** Conversion model info: HTTP 200
- **[PASS]** Product catalog: HTTP 200
- **[PASS]** External profile GET: HTTP 200
- **[PASS]** External analytics GET: HTTP 200
- **[PASS]** External intelligence GET: HTTP 200
- **[PASS]** Repayment predict (Internal): HTTP 200
- **[PASS]** Product recommend (Internal): HTTP 200
- **[PASS]** Product recommend (External): HTTP 200
- **[PASS]** Conversion predict: HTTP 200
- **[PASS]** Explainability GET: HTTP 200
- **[PASS]** Route registered: Customer360 build: POST endpoint present in OpenAPI
- **[PASS]** Route registered: Financial analytics: POST endpoint present in OpenAPI
- **[PASS]** Route registered: External import: POST endpoint present in OpenAPI
- **[PASS]** Route registered: External enrichment: POST endpoint present in OpenAPI
- **[PASS]** Route registered: ML dataset build: POST endpoint present in OpenAPI
- **[PASS]** Route registered: Repayment train: POST endpoint present in OpenAPI
- **[PASS]** Route registered: Conversion train: POST endpoint present in OpenAPI
- **[PASS]** Route registered: Internal pipeline build-all: POST endpoint present in OpenAPI
- **[PASS]** Route registered: Explainability generate: POST endpoint present in OpenAPI

### Business Validation — PASS
_Passed: 4, Failed: 0, Warnings: 0, Skipped: 1_

- **[PASS]** Repayment prediction (Internal): capacity=Medium, confidence=0.415
- **[SKIP]** Repayment prediction (External): No training dataset profile available
- **[PASS]** Product recommendation (Internal): product=Education Loan, probability=22.0, eligible=False
- **[PASS]** Product recommendation (External): product=Education Loan, probability=26.7, eligible=False
- **[PASS]** Conversion prediction: conversion_probability=36.89

### Data Integrity — FAIL
_Passed: 5, Failed: 7, Warnings: 0, Skipped: 0_

- **[PASS]** Negative account balances: negative_balances=0
- **[FAIL]** Impossible customer ages: invalid_ages=1000
- **[FAIL]** Duplicate customer phone numbers: duplicate_phones=1000
- **[FAIL]** Duplicate external lead phone numbers: duplicate_lead_phones=1000
- **[FAIL]** Invalid customer income (<= 0): invalid_income=1000
- **[FAIL]** Invalid EMI burden (> 100%): invalid_emi=95
- **[FAIL]** Invalid debt ratio (> 100%): invalid_debt_ratio=95
- **[FAIL]** Duplicate Customer360 per customer: duplicate_customer360=95
- **[PASS]** Duplicate external profile per lead: duplicate_external_profile=0
- **[PASS]** Training dataset duplicate profile rows: duplicate_training_rows=0
- **[PASS]** Missing customer names: null_full_name=0
- **[PASS]** Missing training target variable: null_target_repayment_capacity=0

### Database — FAIL
_Passed: 33, Failed: 4, Warnings: 0, Skipped: 0_

- **[PASS]** Table structure: customers: PK=['customer_id'], indexes=2, constraints=2, duplicate_pk_groups=0
- **[PASS]** Table structure: accounts: PK=['account_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Table structure: transactions: PK=['transaction_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Table structure: products: PK=['product_id'], indexes=2, constraints=2, duplicate_pk_groups=0
- **[PASS]** Table structure: customer_products: PK=['customer_product_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Table structure: consent: PK=['consent_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Table structure: customer_360_profile: PK=['profile_id'], indexes=1, constraints=1, duplicate_pk_groups=0
- **[PASS]** Table structure: feature_store: PK=['feature_id'], indexes=2, constraints=2, duplicate_pk_groups=0
- **[PASS]** Table structure: external_leads: PK=['lead_id'], indexes=1, constraints=1, duplicate_pk_groups=0
- **[PASS]** Table structure: external_customer_profile: PK=['profile_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Table structure: lead_feature_store: PK=['feature_id'], indexes=2, constraints=2, duplicate_pk_groups=0
- **[PASS]** Table structure: training_dataset: PK=['record_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Table structure: explainability_reports: PK=['report_id'], indexes=3, constraints=3, duplicate_pk_groups=0
- **[PASS]** Record count: customers: count=1000, expected=1000
- **[PASS]** Record count: accounts: count=1000, expected>=1000
- **[PASS]** Record count: transactions: count=27999, expected>=10000
- **[PASS]** Record count: products: count=10, expected>=1
- **[PASS]** Record count: customer_products: count=1823, expected>=1
- **[PASS]** Record count: consent: count=1000, expected>=1000
- **[FAIL]** Record count: customer_360_profile: count=95, expected=1000
- **[FAIL]** Record count: feature_store: count=95, expected=1000
- **[PASS]** Record count: external_leads: count=1000, expected=1000
- **[FAIL]** Record count: external_customer_profile: count=458, expected=1000
- **[FAIL]** Record count: lead_feature_store: count=2, expected=1000
- **[PASS]** Record count: training_dataset: count=20, expected>=1
- **[PASS]** Record count: explainability_reports: count=50, expected>=0
- **[PASS]** Referential integrity: Orphan accounts (no customer): orphan_rows=0
- **[PASS]** Referential integrity: Orphan transactions (no account): orphan_rows=0
- **[PASS]** Referential integrity: Orphan customer_products (no customer): orphan_rows=0
- **[PASS]** Referential integrity: Orphan customer_products (no product): orphan_rows=0
- **[PASS]** Referential integrity: Orphan consent (no customer): orphan_rows=0
- **[PASS]** Referential integrity: Orphan Customer360 profiles (no customer): orphan_rows=0
- **[PASS]** Referential integrity: Orphan feature_store rows (no customer): orphan_rows=0
- **[PASS]** Referential integrity: Orphan external profiles (no lead): orphan_rows=0
- **[PASS]** Referential integrity: Orphan lead_feature_store rows (no lead): orphan_rows=0
- **[PASS]** Behaviour summary (internal feature_store): customers_with_behaviour_summary=95
- **[PASS]** Behaviour summary (lead_feature_store): leads_with_behaviour_summary=2

### Database Consistency — FAIL
_Passed: 1, Failed: 3, Warnings: 0, Skipped: 0_

- **[FAIL]** Every Customer360 has Feature Store: profiles_without_features=95
- **[FAIL]** Every External Profile has Lead Feature Store: profiles_without_lead_features=456
- **[FAIL]** Training dataset references valid profiles: orphan_internal=20, orphan_external=0
- **[PASS]** Product catalog references valid products: catalog_products=5

### End to End Workflow — FAIL
_Passed: 0, Failed: 2, Warnings: 0, Skipped: 0_

- **[FAIL]** Internal customer end-to-end workflow: stages_ok=['Customer360', 'Feature Store', 'Training Dataset', 'Repayment Prediction', 'Product Recommendation'], failed=['Repayment Prediction']
- **[FAIL]** External lead end-to-end workflow: stages_ok=['Import', 'Enrichment', 'Lead Analytics', 'Lead Feature Store', 'Training Dataset', 'Lead Conversion'], failed=['Enrichment', 'Lead Analytics', 'Lead Feature Store', 'Training Dataset']

### External Intelligence — FAIL
_Passed: 0, Failed: 5, Warnings: 2, Skipped: 0_

- **[FAIL]** Lead enrichment coverage: profiles=458, leads=1000
- **[FAIL]** Lead Analytics coverage: leads_with_stage=2/1000
- **[FAIL]** Lead Intelligence coverage: leads_with_stage=2/1000
- **[FAIL]** Behaviour Summary coverage: leads_with_stage=2/1000
- **[WARN]** Lead status ANALYTICS_READY: analytics_ready=0/1000
- **[WARN]** Lead status INTELLIGENCE_VALIDATED: intelligence_validated=2/1000
- **[FAIL]** Lead Feature Store coverage: leads_in_feature_store=2/1000

### Internal Intelligence — FAIL
_Passed: 0, Failed: 9, Warnings: 0, Skipped: 0_

- **[FAIL]** Customer360 coverage: profiles=95, customers=1000
- **[FAIL]** Financial Analytics coverage: profiles_with_financial_kpis=95/1000
- **[FAIL]** Transaction Analytics coverage: customers_with_stage=95/1000
- **[FAIL]** Behaviour Analytics coverage: customers_with_stage=95/1000
- **[FAIL]** Relationship Analytics coverage: customers_with_stage=95/1000
- **[FAIL]** Digital & Channel Analytics coverage: customers_with_stage=95/1000
- **[FAIL]** Customer Health Analytics coverage: customers_with_stage=95/1000
- **[FAIL]** Feature Store coverage: customers_with_stage=95/1000
- **[FAIL]** Pipeline completion markers: pipeline_completed=91/1000

### Machine Learning — FAIL
_Passed: 11, Failed: 1, Warnings: 1, Skipped: 0_

- **[PASS]** Training dataset populated: records=20 (internal=20, external=0)
- **[FAIL]** Training dataset has internal and external records: internal=20, external=0
- **[PASS]** Training dataset target variable valid: invalid_targets=0
- **[PASS]** Training dataset no duplicate rows: duplicate_profile_groups=0
- **[WARN]** Training dataset feature completeness: rows_missing_all_core_scores=20
- **[PASS]** Repayment Capacity Model file exists: C:\Users\krish\OneDrive\Desktop\Tara\backend\app\ml\models\best_repayment_model.pkl
- **[PASS]** Repayment Capacity Model metrics valid JSON: keys=7
- **[PASS]** Repayment Capacity Model feature importance valid JSON: keys=15
- **[PASS]** Lead Conversion Model file exists: C:\Users\krish\OneDrive\Desktop\Tara\backend\app\ml\models\best_conversion_model.pkl
- **[PASS]** Lead Conversion Model metrics valid JSON: keys=7
- **[PASS]** Lead Conversion Model feature importance valid JSON: keys=37
- **[PASS]** Product Recommendation catalog module: C:\Users\krish\OneDrive\Desktop\Tara\backend\app\ml\product_recommendation\catalog.py
- **[PASS]** Product Recommendation engine type: Rule-based hybrid engine (no pickle artifact required)
