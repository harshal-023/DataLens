import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.report import (
    BusinessReportCreate,
    BusinessReportResponse,
    BusinessReportUpdate,
    PaginatedBusinessReportListResponse,
    PaginatedReportListResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportRunResponse,
    ReportRunTriggerRequest,
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleUpdate,
    ReportTemplateResponse,
)
from app.services.reports.business_report_service import BusinessReportService
from app.services.reports.report_assembly import ReportAssemblyEngine
from app.services.reports.report_service import ReportService
from app.services.reports.scheduler_service import ReportSchedulerService

router = APIRouter(prefix="/reports", tags=["Reports"])


# ===========================================================================
# PHASE 4D: TEMPLATES
# ===========================================================================

@router.get("/templates", response_model=list[ReportTemplateResponse])
async def list_report_templates(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Annotated[str | None, Query()] = None,
) -> list[ReportTemplateResponse]:
    workspace, _ = ws_context
    templates = await BusinessReportService.list_templates(
        workspace_id=workspace.id,
        category=category,
        db=db,
    )
    return [ReportTemplateResponse(**t) for t in templates]


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_report_template(
    template_id: str,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportTemplateResponse:
    workspace, _ = ws_context
    tpl = await BusinessReportService.get_template(template_id, workspace.id, db)
    return ReportTemplateResponse(**tpl)


# ===========================================================================
# PHASE 4D: BUSINESS REPORTS CRUD
# ===========================================================================

@router.get("/business", response_model=PaginatedBusinessReportListResponse)
async def list_business_reports(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    report_type: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> PaginatedBusinessReportListResponse:
    workspace, _ = ws_context
    res = await BusinessReportService.list_reports(
        workspace_id=workspace.id,
        page=page,
        page_size=page_size,
        report_type=report_type,
        search=search,
        db=db,
    )
    return PaginatedBusinessReportListResponse(
        items=[BusinessReportResponse.model_validate(r) for r in res["items"]],
        total=res["total"],
        page=res["page"],
        page_size=res["page_size"],
        total_pages=res["total_pages"],
    )


@router.post("/business", response_model=BusinessReportResponse, status_code=status.HTTP_201_CREATED)
async def create_business_report(
    req: BusinessReportCreate,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessReportResponse:
    workspace, _ = ws_context
    report = await BusinessReportService.create_report(
        workspace_id=workspace.id,
        owner_id=current_user.id,
        title=req.title,
        description=req.description,
        report_type=req.report_type,
        template_id=req.template_id,
        configuration=req.configuration,
        source_dashboard_ids=req.source_dashboard_ids,
        source_dataset_refs=req.source_dataset_refs,
        source_model_run_refs=req.source_model_run_refs,
        db=db,
    )
    return BusinessReportResponse.model_validate(report)


@router.get("/business/{report_id}", response_model=BusinessReportResponse)
async def get_business_report(
    report_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessReportResponse:
    workspace, _ = ws_context
    report = await BusinessReportService.get_report(report_id, workspace.id, db)
    return BusinessReportResponse.model_validate(report)


@router.put("/business/{report_id}", response_model=BusinessReportResponse)
async def update_business_report(
    report_id: uuid.UUID,
    req: BusinessReportUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessReportResponse:
    workspace, _ = ws_context
    report = await BusinessReportService.update_report(
        report_id=report_id,
        workspace_id=workspace.id,
        payload=req.model_dump(exclude_unset=True),
        db=db,
    )
    return BusinessReportResponse.model_validate(report)


@router.delete("/business/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_report(
    report_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    await BusinessReportService.delete_report(report_id, workspace.id, db)


@router.post("/business/{report_id}/duplicate", response_model=BusinessReportResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_business_report(
    report_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessReportResponse:
    workspace, _ = ws_context
    dup = await BusinessReportService.duplicate_report(
        report_id=report_id,
        workspace_id=workspace.id,
        owner_id=current_user.id,
        db=db,
    )
    return BusinessReportResponse.model_validate(dup)


# ===========================================================================
# PHASE 4D: PREVIEW & RUN EXECUTION
# ===========================================================================

@router.post("/business/{report_id}/preview")
async def preview_business_report(
    report_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    workspace, _ = ws_context
    report = await BusinessReportService.get_report(report_id, workspace.id, db)
    evidence = await ReportAssemblyEngine.assemble_report_evidence(
        workspace_id=workspace.id,
        report=report,
        runtime_filters=[],
        period=period,
        db=db,
    )
    return evidence


@router.post("/business/{report_id}/run", response_model=ReportRunResponse)
async def trigger_business_report_run(
    report_id: uuid.UUID,
    req: ReportRunTriggerRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportRunResponse:
    workspace, _ = ws_context
    run = await BusinessReportService.generate_report_run(
        report_id=report_id,
        workspace_id=workspace.id,
        triggered_by=current_user.id,
        period=req.period,
        formats=req.formats,
        applied_filters=req.applied_filters,
        db=db,
    )
    return ReportRunResponse.model_validate(run)


@router.get("/business/{report_id}/runs", response_model=list[ReportRunResponse])
async def list_report_runs(
    report_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ReportRunResponse]:
    workspace, _ = ws_context
    runs = await BusinessReportService.list_report_runs(report_id, workspace.id, db)
    return [ReportRunResponse.model_validate(r) for r in runs]


# ===========================================================================
# PHASE 4D: DOWNLOADS & FILES
# ===========================================================================

@router.get("/runs/{run_id}/download")
async def download_report_run_file(
    run_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    format_type: Annotated[str, Query(alias="format")] = "pdf",
) -> Response:
    workspace, _ = ws_context
    file_bytes, media_type, filename = await BusinessReportService.get_run_file(
        run_id=run_id,
        format_type=format_type,
        workspace_id=workspace.id,
        db=db,
    )
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===========================================================================
# PHASE 4D: SCHEDULES
# ===========================================================================

@router.post("/business/{report_id}/schedules", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_report_schedule(
    report_id: uuid.UUID,
    req: ReportScheduleCreate,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportScheduleResponse:
    workspace, _ = ws_context
    sched = await BusinessReportService.create_schedule(
        report_id=report_id,
        workspace_id=workspace.id,
        created_by=current_user.id,
        frequency=req.frequency,
        hour=req.hour,
        minute=req.minute,
        day_of_week=req.day_of_week,
        day_of_month=req.day_of_month,
        timezone=req.timezone,
        delivery_configuration=req.delivery_configuration,
        db=db,
    )
    return ReportScheduleResponse.model_validate(sched)


@router.put("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
async def update_report_schedule(
    schedule_id: uuid.UUID,
    req: ReportScheduleUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportScheduleResponse:
    workspace, _ = ws_context
    sched = await BusinessReportService.update_schedule(
        schedule_id=schedule_id,
        workspace_id=workspace.id,
        payload=req.model_dump(exclude_unset=True),
        db=db,
    )
    return ReportScheduleResponse.model_validate(sched)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_schedule(
    schedule_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    await BusinessReportService.delete_schedule(schedule_id, workspace.id, db)


@router.post("/schedules/trigger-due", response_model=list[ReportRunResponse])
async def trigger_due_report_schedules(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ReportRunResponse]:
    runs = await ReportSchedulerService.trigger_due_schedules(db)
    return [ReportRunResponse.model_validate(r) for r in runs]


# ===========================================================================
# LEGACY PHASE 1/2 ENDPOINTS (PRESERVED)
# ===========================================================================

@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def legacy_create_report(
    req: ReportCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    workspace, _ = ws_context
    report = await ReportService.create_report(
        workspace_id=workspace.id,
        creator_id=current_user.id,
        dataset_id=req.dataset_id,
        title=req.title,
        report_format=req.format,
        version_id=req.version_id,
        report_config=req.report_config,
        db=db,
    )
    return ReportResponse.model_validate(report)


@router.get("", response_model=PaginatedReportListResponse)
async def legacy_list_reports(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset_id: Annotated[uuid.UUID | None, Query()] = None,
    format_filter: Annotated[str | None, Query(alias="format")] = None,
) -> PaginatedReportListResponse:
    workspace, _ = ws_context
    res = await ReportService.list_reports(
        workspace_id=workspace.id,
        page=page,
        page_size=page_size,
        dataset_id=dataset_id,
        format_filter=format_filter,
        db=db,
    )
    return PaginatedReportListResponse(
        items=[ReportResponse.model_validate(r) for r in res["items"]],
        total=res["total"],
        page=res["page"],
        page_size=res["page_size"],
        total_pages=res["total_pages"],
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def legacy_get_report_detail(
    report_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    workspace, _ = ws_context
    report = await ReportService.get_report(report_id, workspace.id, db)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
async def legacy_download_report_file(
    report_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    workspace, _ = ws_context
    file_bytes, media_type, filename = await ReportService.get_report_file(report_id, workspace.id, db)
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
