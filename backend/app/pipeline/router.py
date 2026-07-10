"""Pipeline orchestration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_pipeline_orchestrator, get_complete_flow_orchestrator
from app.pipeline.master_orchestrator import MasterPipelineOrchestrator, PipelineRunResult
from app.pipeline.full_flow_orchestrator import CompleteFlowOrchestrator, CompleteFlowRequest
from app.pipeline.progress import live_pipeline_progress
from app.schemas.pipeline import PipelineRunResponse, PipelineStatusResponse

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Orchestration"])


def _to_response(run: PipelineRunResult) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=run.run_id,
        pipeline_type=run.pipeline_type,
        success=run.success,
        started_at=run.started_at,
        completed_at=run.completed_at,
        steps=[
            {"step": s.step, "status": s.status, "detail": s.detail, "duration_ms": s.duration_ms}
            for s in run.steps
        ],
    )


@router.post("/run/external", response_model=PipelineRunResponse)
def run_external_pipeline(
    train_models: bool = Query(default=True),
    orchestrator: MasterPipelineOrchestrator = Depends(get_pipeline_orchestrator),
) -> PipelineRunResponse:
    return _to_response(orchestrator.run_external_pipeline(train_models=train_models))


@router.post("/run/internal", response_model=PipelineRunResponse)
def run_internal_pipeline(
    train_models: bool = Query(default=True),
    orchestrator: MasterPipelineOrchestrator = Depends(get_pipeline_orchestrator),
) -> PipelineRunResponse:
    return _to_response(orchestrator.run_internal_pipeline(train_models=train_models))


@router.post("/run/full", response_model=PipelineRunResponse)
def run_full_pipeline(
    orchestrator: MasterPipelineOrchestrator = Depends(get_pipeline_orchestrator),
) -> PipelineRunResponse:
    return _to_response(orchestrator.run_full_demo_pipeline())


@router.post("/run/subset", response_model=PipelineRunResponse)
def run_subset_pipeline(
    target: str = Query(default="both", description="Choices: internal, external, both"),
    limit_internal: int = Query(default=5, ge=1, le=1000),
    limit_external: int = Query(default=5, ge=1, le=1000),
    train_models: bool = Query(default=True),
    orchestrator: MasterPipelineOrchestrator = Depends(get_pipeline_orchestrator),
) -> PipelineRunResponse:
    return _to_response(
        orchestrator.run_subset_pipeline(
            target=target,
            limit_internal=limit_internal,
            limit_external=limit_external,
            train_models=train_models,
        )
    )


@router.post("/run/complete-flow", response_model=PipelineRunResponse)
def run_complete_architecture_flow(
    outreach_limit: int = Query(default=10, ge=1, le=100),
    outreach_dry_run: bool = Query(default=False),
    auto_retrain: bool = Query(default=True),
    orchestrator: CompleteFlowOrchestrator = Depends(get_complete_flow_orchestrator),
) -> PipelineRunResponse:
    """L1→L6: scoring pipeline → outreach → sequences → learning → retrain → score refresh."""
    return _to_response(
        orchestrator.run(
            CompleteFlowRequest(
                outreach_limit=outreach_limit,
                outreach_dry_run=outreach_dry_run,
                auto_retrain=auto_retrain,
            )
        )
    )


@router.get("/live")
def get_live_pipeline_progress() -> dict:
    """Poll active pipeline step progress for the admin UI flow line."""
    return live_pipeline_progress.snapshot()


@router.get("/runs", response_model=list[PipelineStatusResponse])
def list_pipeline_runs(
    limit: int = Query(default=10, ge=1, le=50),
    orchestrator: MasterPipelineOrchestrator = Depends(get_pipeline_orchestrator),
) -> list[PipelineStatusResponse]:
    docs = list(orchestrator._db.pipeline_runs.find({}, {"_id": 0}))
    docs.sort(key=lambda d: d.get("started_at") or "", reverse=True)
    return [PipelineStatusResponse(**d) for d in docs[:limit]]
