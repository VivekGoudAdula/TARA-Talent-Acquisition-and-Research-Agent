"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.ml_dataset_router import router as ml_dataset_router
from app.ml.repayment.router import router as repayment_router
from app.ml.product_recommendation.router import router as product_recommendation_router
from app.ml.conversion.router import router as conversion_router
from app.ml.scoring_router import router as scoring_router
from app.explainability.router import router as explainability_router
from app.internal_pipeline.router import router as internal_pipeline_router
from app.routers.banking_import_router import router as banking_import_router
from app.engagement.router import router as engagement_router
from app.onboarding.router import router as onboarding_router
from app.learning.router import router as learning_router
from app.pipeline.router import router as pipeline_router
from app.activation.router import router as activation_router
from app.ops.router import router as ops_router
from app.platform_validation.router import router as platform_validation_router
from app.routers.customer_health_router import router as customer_health_router
from app.routers.channel_router import router as channel_router
from app.routers.external_analytics_router import router as external_analytics_router
from app.routers.external_intelligence_router import router as external_intelligence_router
from app.routers.external_router import router as external_router
from app.routers.relationship_router import router as relationship_router, frontend_router as relationship_frontend_router
from app.routers.behaviour_summary_router import router as behaviour_summary_router, frontend_router as behaviour_summary_frontend_router
from app.routers.behaviour_router import router as behaviour_router, frontend_router as behaviour_frontend_router
from app.routers.customer360_router import router as customer360_router
from app.routers.financial_router import router as financial_router, frontend_router as financial_frontend_router
from app.routers.transaction_router import router as transaction_router, frontend_router as transaction_frontend_router
from app.db.mongo import ensure_indexes
from app.utils.exceptions import (
    AppException,
    BehaviourSummaryNotFoundError,
    CustomerNotFoundError,
    ExternalAnalyticsNotFoundError,
    ExternalIntelligenceNotFoundError,
    ExternalProfileNotFoundError,
    LeadNotFoundError,
    MLDatasetNotFoundError,
    RepaymentModelNotFoundError,
    ConversionModelNotFoundError,
    ConversionDataNotFoundError,
    ExplainabilityReportNotFoundError,
    ProfileNotFoundError,
    UnifiedProfileNotFoundError,
)
from app.utils.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure MongoDB indexes on startup; optional learning scheduler."""
    ensure_indexes()
    scheduler = None
    if settings.learning_scheduler_enabled:
        try:
            from app.learning.scheduler import start_learning_scheduler

            scheduler = start_learning_scheduler(
                interval_hours=settings.learning_scheduler_interval_hours
            )
            logger.info("Learning scheduler started (every %sh)", settings.learning_scheduler_interval_hours)
        except Exception as exc:
            logger.warning("Learning scheduler failed to start: %s", exc)
    logger.info("Customer360 Intelligence Engine started — MongoDB ready")
    sid = (settings.twilio_account_sid or "").strip()
    if sid:
        logger.info("Twilio account SID: %s…%s", sid[:4], sid[-4:] if len(sid) > 8 else sid)
    else:
        logger.warning("TWILIO_ACCOUNT_SID not set — voice callbacks will fail")
    try:
        from app.engagement.callback_links import resolve_public_api_base

        callback_base = resolve_public_api_base(settings)
        if "localhost" in callback_base or "127.0.0.1" in callback_base:
            logger.warning(
                "Email callback links use %s — mobile email will FAIL. "
                "Set ENGAGEMENT_API_BASE_URL to ngrok/public URL.",
                callback_base,
            )
        else:
            logger.info("Email callback CTA base URL: %s", callback_base)
            if "192.168." in callback_base or "10." in callback_base:
                logger.warning(
                    "Mobile email on cellular data cannot reach LAN IP. "
                    "Use ngrok: ENGAGEMENT_API_BASE_URL=https://xxx.ngrok-free.app"
                )
            logger.warning(
                "For phone callback links, start backend with: "
                "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
            )
    except Exception:
        pass
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
    logger.info("Customer360 Intelligence Engine shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Enterprise Customer 360 Intelligence Engine for SBI Tara. "
        "Aggregates core banking data into a unified, trusted customer profile."
    ),
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow the Vite dev server and any local port, plus production origins.
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customer360_router)
app.include_router(financial_router)
app.include_router(transaction_router)
app.include_router(behaviour_router)
app.include_router(relationship_router)
app.include_router(channel_router)
app.include_router(customer_health_router)
app.include_router(external_router)
app.include_router(external_analytics_router)
app.include_router(external_intelligence_router)
app.include_router(behaviour_summary_router)
app.include_router(ml_dataset_router)
app.include_router(repayment_router)
app.include_router(product_recommendation_router)
app.include_router(conversion_router)
app.include_router(scoring_router)
app.include_router(explainability_router)
app.include_router(internal_pipeline_router)
app.include_router(banking_import_router)
app.include_router(platform_validation_router)
app.include_router(engagement_router)
app.include_router(onboarding_router)
app.include_router(learning_router)
app.include_router(pipeline_router)
app.include_router(activation_router)
app.include_router(ops_router)

# Frontend specific routes for backwards compatibility and single-origin API layout
app.include_router(financial_frontend_router)
app.include_router(transaction_frontend_router)
app.include_router(behaviour_frontend_router)
app.include_router(behaviour_summary_frontend_router)
app.include_router(relationship_frontend_router)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_PORTAL_URL = os.getenv("TARA_PORTAL_URL", "http://localhost:5173/tara/crm")


@app.get("/api/ml/product-recommendation/model-info", tags=["Product Recommendation"])
def get_product_recommendation_model_info() -> dict:
    """Mock metadata endpoint for hybrid rule-based + ML product recommendation."""
    return {
        "trained": True,
        "algorithm": "Hybrid Rules + Repayment ML Ranker",
        "version": "1.0.0",
        "last_trained": None,
        "train_samples": 1000,
        "test_samples": 0,
        "metrics": {
            "accuracy": 0.94,
            "f1": 0.92,
            "roc_auc": 0.96
        },
        "feature_importance": {
            "credit_score": 0.40,
            "monthly_income": 0.30,
            "repayment_capacity": 0.20,
            "emi_ratio": 0.10
        }
    }



@app.get("/ops", include_in_schema=False)
@app.get("/ops/", include_in_schema=False)
async def redirect_legacy_ops_portal() -> RedirectResponse:
    """Legacy static CRM — redirect to unified TARA admin portal."""
    return RedirectResponse(url=_PORTAL_URL, status_code=302)


if _STATIC_DIR.is_dir():
    # Keep static files for assets; HTML portal replaced by unified React admin.
    pass


@app.exception_handler(CustomerNotFoundError)
async def customer_not_found_handler(_request: Request, exc: CustomerNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ProfileNotFoundError)
async def profile_not_found_handler(_request: Request, exc: ProfileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(LeadNotFoundError)
async def lead_not_found_handler(_request: Request, exc: LeadNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ExternalProfileNotFoundError)
async def external_profile_not_found_handler(
    _request: Request, exc: ExternalProfileNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ExternalAnalyticsNotFoundError)
async def external_analytics_not_found_handler(
    _request: Request, exc: ExternalAnalyticsNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ExternalIntelligenceNotFoundError)
async def external_intelligence_not_found_handler(
    _request: Request, exc: ExternalIntelligenceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(UnifiedProfileNotFoundError)
async def unified_profile_not_found_handler(
    _request: Request, exc: UnifiedProfileNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(BehaviourSummaryNotFoundError)
async def behaviour_summary_not_found_handler(
    _request: Request, exc: BehaviourSummaryNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(MLDatasetNotFoundError)
async def ml_dataset_not_found_handler(
    _request: Request, exc: MLDatasetNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(RepaymentModelNotFoundError)
async def repayment_model_not_found_handler(
    _request: Request, exc: RepaymentModelNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ConversionModelNotFoundError)
async def conversion_model_not_found_handler(
    _request: Request, exc: ConversionModelNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ConversionDataNotFoundError)
async def conversion_data_not_found_handler(
    _request: Request, exc: ConversionDataNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ExplainabilityReportNotFoundError)
async def explainability_not_found_handler(
    _request: Request, exc: ExplainabilityReportNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": exc.message})


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": settings.app_name}
