"""Layer 6 — Learning & Continuous Performance Improvement API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import get_learning_service
from app.learning.service import LearningService
from app.schemas.learning import (
    BuildOutcomeLabelsRequest,
    BuildOutcomeLabelsResponse,
    IngestOutcomeRequest,
    ModelRunSummary,
    OutcomeLabelRecord,
    PerformanceSnapshotResponse,
    PerformanceSummaryResponse,
    RetrainRequest,
    RetrainResponse,
)

router = APIRouter(prefix="/api/learning", tags=["Learning & Optimization"])


@router.get(
    "/performance/summary",
    response_model=PerformanceSummaryResponse,
    summary="Outreach funnel, channel KPIs, and prediction accuracy",
)
def get_performance_summary(
    capture_snapshot: bool = False,
    service: LearningService = Depends(get_learning_service),
) -> PerformanceSummaryResponse:
    return service.get_performance_summary(capture_snapshot=capture_snapshot)


@router.get(
    "/performance/snapshots",
    response_model=list[PerformanceSnapshotResponse],
    summary="Historical performance snapshots",
)
def list_performance_snapshots(
    limit: int = 20,
    service: LearningService = Depends(get_learning_service),
) -> list[PerformanceSnapshotResponse]:
    return service.list_snapshots(limit=limit)


@router.post(
    "/feedback/build-labels",
    response_model=BuildOutcomeLabelsResponse,
    summary="Derive conversion labels from Layer 5 outcomes",
)
def build_outcome_labels(
    request: BuildOutcomeLabelsRequest,
    service: LearningService = Depends(get_learning_service),
) -> BuildOutcomeLabelsResponse:
    return service.build_outcome_labels(limit=request.limit, persist=request.persist)


@router.get(
    "/feedback/labels",
    response_model=list[OutcomeLabelRecord],
    summary="Outcome-derived training labels",
)
def list_outcome_labels(
    limit: int = 100,
    service: LearningService = Depends(get_learning_service),
) -> list[OutcomeLabelRecord]:
    return service.list_outcome_labels(limit=limit)


@router.post(
    "/feedback/ingest",
    response_model=OutcomeLabelRecord | None,
    summary="Ingest a single outcome after Layer 5 response capture",
)
def ingest_outcome(
    request: IngestOutcomeRequest,
    service: LearningService = Depends(get_learning_service),
) -> OutcomeLabelRecord | None:
    return service.ingest_outcome(request)


@router.post(
    "/retrain",
    response_model=RetrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrain conversion model using real outreach outcomes",
)
def retrain_with_outcomes(
    request: RetrainRequest,
    service: LearningService = Depends(get_learning_service),
) -> RetrainResponse:
    return service.retrain_models(
        label_source=request.label_source,
        min_outcome_labels=request.min_outcome_labels,
        refresh_scores=request.refresh_scores,
    )


@router.get(
    "/model-runs",
    response_model=list[ModelRunSummary],
    summary="ML training run history with outcome metrics",
)
def list_model_runs(
    model_name: str | None = None,
    limit: int = 20,
    service: LearningService = Depends(get_learning_service),
) -> list[ModelRunSummary]:
    return service.list_model_runs(model_name=model_name, limit=limit)
