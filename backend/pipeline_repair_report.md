# Internal Intelligence Pipeline — Repair Report

**Generated:** 2026-07-06  
**Task:** Debug, fix, and complete the existing internal Customer360 pipeline

---

## Root Cause

Two compounding issues prevented all 100 customers from reaching `customer_360_profile` and `feature_store`:

### 1. Batch session poisoning (primary code defect)

`POST /api/internal/build-all` processed all customers in a **single shared SQLAlchemy session** (one FastAPI request scope).

When any customer failed at Financial, Transaction, Behaviour, or later stages:
- SQLAlchemy marked the session as **rolled back**
- Subsequent customers could not persist profiles or features
- The orchestrator caught exceptions and continued, but **never called `session.rollback()`**
- Result: only the first successful customer(s) were persisted; the rest silently failed

This matches the observed state:
- `customer_360_profile = 1` (one manual or first successful run)
- `feature_store = 72` distinct customers (partial runs from individual analytics `build-all` endpoints before profiles existed for all)

### 2. Full pipeline never executed end-to-end

The internal orchestrator (`/api/internal/build-all`) was implemented but **not run across all 100 customers**. Partial coverage came from per-module endpoints (e.g. transaction `build-all`) which require an existing Customer360 profile and skip customers with `ProfileNotFoundError`.

---

## Files Fixed

| File | Change |
|------|--------|
| `app/internal_pipeline/pipeline_service.py` | Per-customer isolated DB sessions via `_run_customer_isolated()` |
| `app/internal_pipeline/orchestrator.py` | Session rollback on failure; `failed_stage` + stack trace in result |
| `app/dependencies.py` | `create_internal_pipeline_orchestrator(db)` factory for isolated sessions |
| `app/repositories/customer360_repository.py` | `update_profile()` calls `add()` before commit |
| `app/schemas/internal_pipeline.py` | Added `failed_stage` to `CustomerPipelineResult` |
| `tests/test_internal_pipeline.py` | Updated for factory-based service wiring |

**No analytics engines, business logic, or API contracts were changed.**

---

## Methods Changed

- `InternalPipelineService._run_customer_isolated` — **new**: dedicated `SessionLocal()` per customer
- `InternalPipelineService._run_batch` — uses isolated sessions; logs failed stage per customer
- `InternalPipelineOrchestrator._rollback_session` — **new**: cleans session after failure
- `InternalPipelineOrchestrator._next_stage` — **new**: identifies failed pipeline stage
- `create_internal_pipeline_orchestrator` — **new**: builds orchestrator bound to a session
- `Customer360Repository.update_profile` — ensures profile is attached before commit

---

## Validation Before (observed)

| Check | Status |
|-------|--------|
| Database | FAIL |
| Customer360 | FAIL |
| Feature Store | FAIL |
| Internal Intelligence | FAIL |
| End-to-End | FAIL |
| External Intelligence | PASS |
| ML | PASS |
| API | PASS |

| Table | Count |
|-------|-------|
| customers | 100 |
| customer_360_profile | 1 |
| feature_store (distinct customer_id) | 72 |
| pipeline_completed markers | 0 |

---

## Post-Repair Actions (run locally)

### Step 1 — Build all customers

```powershell
.\.venv\Scripts\python.exe scripts\run_build_all_only.py
```

Or via API (server must be running):

```http
POST http://localhost:8001/api/internal/build-all
```

Expected: `completed=100`, `failed=0`, `success_rate=100%`

### Step 2 — Verify counts

```sql
SELECT COUNT(*) FROM customers;                        -- 100
SELECT COUNT(*) FROM customer_360_profile;             -- 100
SELECT COUNT(DISTINCT customer_id) FROM feature_store; -- 100
```

### Step 3 — Platform validation

```http
POST http://localhost:8001/api/system/validate
```

Or:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_repair.py
```

**Target:** Overall Health ≥ 95%

---

## Expected Validation After

| Check | Target |
|-------|--------|
| Database | PASS |
| Customer360 | PASS |
| Feature Store | PASS |
| Internal Intelligence | PASS |
| End-to-End | PASS |
| Overall Health | ≥ 95% |

---

## Per-Customer Trace (orchestrator stages)

For each customer the pipeline now runs in an isolated transaction:

```
Customer Loaded
  → Customer360 Created/Updated
  → Financial Analytics
  → Transaction Analytics
  → Behaviour Analytics
  → Relationship Analytics
  → Digital & Channel Analytics
  → Customer Health Analytics
  → Feature Store (pipeline_completed marker)
  → Pipeline Completed
```

On failure: `failed_stage`, full exception, and stack trace are logged; remaining customers continue in new sessions.

---

## Customers Failed

Re-run build-all after deploying fixes. Any failures will appear in:
- API response `failed_customer_ids`
- `GET /api/internal/status`
- Application logs: `Pipeline failed customer_id=... stage=...`

---

## Summary

The pipeline orchestration logic and service wiring were correct; the defect was **transaction boundary management** in batch mode. Per-customer session isolation ensures one failure cannot block the remaining 99 customers. Execute `build-all` once after deploy to backfill all profiles and feature store records.
