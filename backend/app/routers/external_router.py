"""External Customer Intelligence API routes."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.ui_adapters import adapt_external_profile_view
from app.dependencies import (
    get_external_enrichment_service,
    get_external_import_service,
    get_external_lead_repository,
    get_pipeline_orchestrator,
)
from app.external.external_enrichment_service import ExternalEnrichmentService
from app.external.external_import_service import ExternalImportService
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.schemas.external_intelligence import (
    ExternalCustomerProfileResponse,
    ExternalEnrichResponse,
    ExternalImportResponse,
    ExternalLeadCreateRequest,
    ExternalLeadCreateResponse,
    ExternalLeadListResponse,
    ExternalLeadResponse,
    ExternalLeadSimulateRequest,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/external", tags=["External Customer Intelligence"])


@router.post(
    "/import",
    response_model=ExternalImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import external leads from Excel",
    description=(
        "Reads the configured Excel file (external_leads_1000.xlsx), validates and normalizes "
        "lead data, and upserts rows into the external_leads table."
    ),
)
def import_external_leads(
    run_pipeline: bool = Query(default=False, description="Run intelligence+scoring pipeline after import"),
    import_service: ExternalImportService = Depends(get_external_import_service),
    pipeline=Depends(get_pipeline_orchestrator),
) -> ExternalImportResponse:
    from app.config import get_settings

    result = import_service.import_from_excel()
    logger.info("External leads imported: %s", result)
    settings = get_settings()
    if run_pipeline or settings.pipeline_auto_run_on_import:
        try:
            pipeline.run_external_pipeline()
        except Exception as exc:
            logger.warning("Post-import pipeline failed: %s", exc)
    return ExternalImportResponse(
        message="External leads imported successfully",
        file_path=str(result["file_path"]),
        leads_imported=int(result["leads_imported"]),
        leads_skipped=int(result["leads_skipped"]),
        leads_updated=int(result["leads_updated"]),
    )


def _create_lead_and_pipeline(
    row,
    lead_repo: ExternalLeadRepository,
    pipeline,
    run_pipeline: bool,
) -> ExternalLeadCreateResponse:
    from app.config import get_settings

    lead, _created = lead_repo.upsert_lead(row)
    settings = get_settings()
    pipeline_started = False
    if run_pipeline or settings.pipeline_auto_run_on_import:
        try:
            pipeline.run_external_pipeline()
            pipeline_started = True
        except Exception as exc:
            logger.warning("Post-create pipeline failed: %s", exc)
    return ExternalLeadCreateResponse(
        message="External lead created — Lead Intelligence Engine started",
        lead_id=lead.lead_id,
        external_reference=lead.external_reference,
        pipeline_started=pipeline_started,
        lead=ExternalLeadResponse.model_validate(lead),
    )


@router.post(
    "/leads",
    response_model=ExternalLeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create external lead from web form",
)
def create_external_lead(
    request: ExternalLeadCreateRequest,
    run_pipeline: bool = Query(default=True, description="Run intelligence pipeline after create"),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    pipeline=Depends(get_pipeline_orchestrator),
) -> ExternalLeadCreateResponse:
    from app.external.web_lead_service import build_form_row

    row = build_form_row(
        name=request.name,
        phone=request.phone,
        email=request.email,
        salary=request.salary,
        city=request.city,
        interested_product=request.interested_product,
        source=request.source,
    )
    logger.info("Web lead created: %s (%s)", row.full_name, row.external_reference)
    return _create_lead_and_pipeline(row, lead_repo, pipeline, run_pipeline)


@router.post(
    "/leads/simulate",
    response_model=ExternalLeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Simulate Instagram / campaign external lead",
)
def simulate_external_lead(
    request: ExternalLeadSimulateRequest | None = Body(default=None),
    run_pipeline: bool = Query(default=True),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    pipeline=Depends(get_pipeline_orchestrator),
) -> ExternalLeadCreateResponse:
    from app.external.web_lead_service import build_simulate_row

    payload = request or ExternalLeadSimulateRequest()
    row = build_simulate_row(
        source=payload.source,
        campaign=payload.campaign,
        name=payload.name,
        salary=payload.salary,
    )
    logger.info("Simulated lead: %s via %s", row.full_name, row.referral_source)
    return _create_lead_and_pipeline(row, lead_repo, pipeline, run_pipeline)


@router.post(
    "/enrich",
    response_model=ExternalEnrichResponse,
    status_code=status.HTTP_200_OK,
    summary="Enrich all imported external leads",
    description=(
        "Runs the deterministic enrichment and lead scoring engines for every lead in "
        "external_leads and persists results to external_customer_profile."
    ),
)
def enrich_external_leads(
    enrichment_service: ExternalEnrichmentService = Depends(get_external_enrichment_service),
) -> ExternalEnrichResponse:
    result = enrichment_service.enrich_all()
    return ExternalEnrichResponse(
        message="External lead enrichment completed",
        leads_processed=result["leads_processed"],
        leads_enriched=result["leads_enriched"],
        leads_failed=result["leads_failed"],
    )


@router.get(
    "/leads",
    response_model=ExternalLeadListResponse,
    summary="List imported external leads",
)
def list_external_leads(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
) -> ExternalLeadListResponse:
    leads = lead_repo.get_all(limit=limit, offset=offset)
    total = lead_repo.count_all()
    return ExternalLeadListResponse(
        total=total,
        leads=[ExternalLeadResponse.model_validate(lead) for lead in leads],
    )


@router.get(
    "/profile/{lead_id}",
    summary="Get enriched external lead profile",
    description=(
        "Returns the enriched external_customer_profile for a lead. "
        "Parallel to customer_360_profile for internal bank customers."
    ),
)
def get_external_profile(
    lead_id: UUID,
    enrichment_service: ExternalEnrichmentService = Depends(get_external_enrichment_service),
) -> dict:
    profile = enrichment_service.get_enriched_profile(lead_id)
    return adapt_external_profile_view(profile.model_dump(mode="json"))
