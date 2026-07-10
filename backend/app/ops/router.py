"""Tara Operations Desk API — RM workstation frontend backend."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_rm_desk_service, get_crm_service, get_platform_summary_service
from app.ops.rm_desk_service import RmDeskService
from app.ops.crm_service import CrmCustomerService
from app.ops.platform_summary_service import PlatformSummaryService
from app.schemas.ops import (
    RmAssignRequest,
    RmDashboardResponse,
    RmHandoffQueueItem,
    RmStatusUpdateRequest,
)

router = APIRouter(prefix="/api/ops", tags=["Operations Desk"])


@router.get("/dashboard", response_model=RmDashboardResponse)
def ops_dashboard(service: RmDeskService = Depends(get_rm_desk_service)) -> RmDashboardResponse:
    return RmDashboardResponse(**service.dashboard())


@router.get("/platform-summary")
def platform_summary(
    service: PlatformSummaryService = Depends(get_platform_summary_service),
) -> dict:
    """MongoDB counts, recent leads, and pipeline status for the admin UI."""
    return service.get_summary()


@router.get("/handoffs", response_model=list[RmHandoffQueueItem])
def ops_handoff_queue(
    status: str | None = None,
    assigned_rm: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: RmDeskService = Depends(get_rm_desk_service),
) -> list[RmHandoffQueueItem]:
    return [RmHandoffQueueItem(**h) for h in service.list_queue(status=status, assigned_rm=assigned_rm, limit=limit)]


@router.post("/handoffs/{handoff_id}/assign")
def assign_handoff(
    handoff_id: str,
    request: RmAssignRequest,
    service: RmDeskService = Depends(get_rm_desk_service),
) -> dict:
    doc = service.assign(handoff_id, request.rm_name, request.rm_id)
    if not doc:
        return {"status": "not_found"}
    return {"status": "assigned", "handoff": doc}


@router.post("/handoffs/{handoff_id}/status")
def update_handoff_status(
    handoff_id: str,
    request: RmStatusUpdateRequest,
    service: RmDeskService = Depends(get_rm_desk_service),
) -> dict:
    doc = service.update_status(handoff_id, request.status, notes=request.notes)
    if not doc:
        return {"status": "not_found"}
    return {"status": "updated", "handoff": doc}


@router.get("/rms")
def list_relationship_managers(
    service: RmDeskService = Depends(get_rm_desk_service),
) -> list[dict]:
    return service.list_rms()


@router.get("/crm/customers")
def search_crm_customers(
    q: str = "",
    customer_type: str = Query(default="all", description="all | internal | external"),
    limit: int = Query(default=500, ge=1, le=2000),
    service: CrmCustomerService = Depends(get_crm_service),
) -> list[dict]:
    return service.search_customers(query=q, limit=limit, customer_type=customer_type)


@router.get("/crm/customers/{entity_id}")
def get_crm_customer_360(
    entity_id: str,
    service: CrmCustomerService = Depends(get_crm_service),
) -> dict:
    return service.get_customer_360(entity_id)
