import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.collaboration import DashboardDuplicateRequest
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardDetailResponse,
    DashboardExportRequest,
    DashboardFilterCreate,
    DashboardFilterResponse,
    DashboardFilterUpdate,
    DashboardLayoutUpdate,
    DashboardListResponse,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
    WidgetQueryRequest,
    WidgetQueryResponse,
)
from app.services.dashboards.dashboard_export import (
    export_dashboard_csv,
    export_dashboard_pdf,
    export_dashboard_xlsx,
)
from app.services.dashboards.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


# ---------------------------------------------------------------------------
# Dashboard CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=DashboardDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    req: DashboardCreate,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardDetailResponse:
    workspace, _ = ws_context
    return await DashboardService.create_dashboard(
        workspace_id=workspace.id,
        creator_id=current_user.id,
        req=req,
        db=db,
    )


@router.get("", response_model=DashboardListResponse)
async def list_dashboards(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: Annotated[str | None, Query(description="Search title and description")] = None,
    include_archived: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardListResponse:
    workspace, _ = ws_context
    return await DashboardService.list_dashboards(
        workspace_id=workspace.id,
        db=db,
        search=search,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.get("/{dashboard_id}", response_model=DashboardDetailResponse)
async def get_dashboard(
    dashboard_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardDetailResponse:
    workspace, _ = ws_context
    return await DashboardService.get_dashboard(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        db=db,
    )


@router.put("/{dashboard_id}", response_model=DashboardDetailResponse)
async def update_dashboard(
    dashboard_id: uuid.UUID,
    req: DashboardUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardDetailResponse:
    workspace, _ = ws_context
    return await DashboardService.update_dashboard(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )


@router.post("/{dashboard_id}/duplicate", response_model=DashboardDetailResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_dashboard(
    dashboard_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    req: DashboardDuplicateRequest | None = None,
) -> DashboardDetailResponse:
    workspace, _ = ws_context
    target_ws_id = req.target_workspace_id if req and req.target_workspace_id else workspace.id
    new_title = req.new_title if req and req.new_title else None
    return await DashboardService.duplicate_dashboard(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        creator_id=current_user.id,
        db=db,
        target_workspace_id=target_ws_id,
        new_title=new_title,
    )


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[bool, Query()] = False,
) -> None:
    workspace, _ = ws_context
    await DashboardService.delete_dashboard(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        db=db,
        hard_delete=hard_delete,
    )


# ---------------------------------------------------------------------------
# Widget Endpoints
# ---------------------------------------------------------------------------

@router.post("/{dashboard_id}/widgets", response_model=DashboardWidgetResponse, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: uuid.UUID,
    req: DashboardWidgetCreate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardWidgetResponse:
    workspace, _ = ws_context
    return await DashboardService.add_widget(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardWidgetResponse)
async def update_widget(
    dashboard_id: uuid.UUID,
    widget_id: uuid.UUID,
    req: DashboardWidgetUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardWidgetResponse:
    workspace, _ = ws_context
    return await DashboardService.update_widget(
        dashboard_id=dashboard_id,
        widget_id=widget_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    dashboard_id: uuid.UUID,
    widget_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    await DashboardService.delete_widget(
        dashboard_id=dashboard_id,
        widget_id=widget_id,
        workspace_id=workspace.id,
        db=db,
    )


@router.post("/{dashboard_id}/layout", response_model=list[DashboardWidgetResponse])
async def update_dashboard_layout(
    dashboard_id: uuid.UUID,
    req: DashboardLayoutUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DashboardWidgetResponse]:
    workspace, _ = ws_context
    return await DashboardService.update_layout(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )


# ---------------------------------------------------------------------------
# Filter Endpoints
# ---------------------------------------------------------------------------

@router.post("/{dashboard_id}/filters", response_model=DashboardFilterResponse, status_code=status.HTTP_201_CREATED)
async def add_filter(
    dashboard_id: uuid.UUID,
    req: DashboardFilterCreate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardFilterResponse:
    workspace, _ = ws_context
    return await DashboardService.add_filter(
        dashboard_id=dashboard_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )


@router.put("/{dashboard_id}/filters/{filter_id}", response_model=DashboardFilterResponse)
async def update_filter(
    dashboard_id: uuid.UUID,
    filter_id: uuid.UUID,
    req: DashboardFilterUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardFilterResponse:
    workspace, _ = ws_context
    return await DashboardService.update_filter(
        dashboard_id=dashboard_id,
        filter_id=filter_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )


@router.delete("/{dashboard_id}/filters/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter(
    dashboard_id: uuid.UUID,
    filter_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    await DashboardService.delete_filter(
        dashboard_id=dashboard_id,
        filter_id=filter_id,
        workspace_id=workspace.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# Analytics Query & Export Endpoints
# ---------------------------------------------------------------------------

@router.post("/{dashboard_id}/widgets/{widget_id}/query", response_model=WidgetQueryResponse)
async def query_widget_data(
    dashboard_id: uuid.UUID,
    widget_id: uuid.UUID,
    req: WidgetQueryRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WidgetQueryResponse:
    workspace, _ = ws_context
    return await DashboardService.execute_widget_query(
        dashboard_id=dashboard_id,
        widget_id=widget_id,
        workspace_id=workspace.id,
        override_filters=req.filters,
        drill_level=req.drill_level,
        drill_filters=req.drill_filters,
        compare_to=req.compare_to,
        target_value=req.target_value,
        db=db,
    )


@router.post("/{dashboard_id}/export")
async def export_dashboard(
    dashboard_id: uuid.UUID,
    req: DashboardExportRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    workspace, _ = ws_context
    dashboard = await DashboardService.get_dashboard(dashboard_id, workspace.id, db)

    # Evaluate all widgets with the requested export filters
    widget_results = []
    for w in dashboard.widgets:
        try:
            q_res = await DashboardService.execute_widget_query(
                dashboard_id=dashboard.id,
                widget_id=w.id,
                workspace_id=workspace.id,
                override_filters=req.filters,
                db=db,
            )
            widget_results.append({
                "title": w.title,
                "widget_type": w.widget_type,
                "data": q_res.data,
                "row_count": q_res.row_count,
            })
        except Exception as e:
            widget_results.append({
                "title": w.title,
                "widget_type": w.widget_type,
                "data": {"error": str(e)},
                "row_count": 0,
            })

    export_fmt = req.format.lower().strip()
    clean_title = "".join(c for c in dashboard.title if c.isalnum() or c in ("-", "_")).strip() or "dashboard"

    if export_fmt == "csv":
        csv_bytes = export_dashboard_csv(dashboard.title, widget_results)
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.csv"'},
        )
    elif export_fmt == "xlsx":
        xlsx_bytes = export_dashboard_xlsx(dashboard.title, workspace.name, widget_results)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.xlsx"'},
        )
    else:  # Default to PDF
        pdf_bytes = export_dashboard_pdf(
            dashboard_title=dashboard.title,
            workspace_name=workspace.name,
            description=dashboard.description,
            widget_results=widget_results,
            applied_filters=[f.model_dump() for f in req.filters] if req.filters else None,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.pdf"'},
        )

