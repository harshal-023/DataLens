import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user, require_workspace_role
from app.models.dataset import Dataset
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.auto_dashboard import (
    AutoDashboardPreviewResponse,
    AutoDashboardRequest,
    AutoDashboardSaveRequest,
    AutoDashboardStatusResponse,
)
from app.schemas.dashboard import DashboardDetailResponse
from app.services.dashboards.auto_generator import AutoDashboardSessionManager

router = APIRouter(prefix="/dashboards/auto-generate", tags=["AI Auto Dashboard"])


@router.post("", response_model=AutoDashboardStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_auto_dashboard(
    req: AutoDashboardRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutoDashboardStatusResponse:
    workspace, _ = ws_context

    # Fetch dataset name for session tracking
    ds = await db.get(Dataset, req.dataset_id)
    dataset_name = ds.name if ds else "Selected Dataset"

    gen_id = AutoDashboardSessionManager.create_session(
        workspace_id=workspace.id,
        dataset_id=req.dataset_id,
        dataset_name=dataset_name,
    )

    # Run the pipeline (can run synchronously or in background)
    await AutoDashboardSessionManager.run_pipeline(
        gen_id=gen_id,
        workspace_id=workspace.id,
        req=req,
        db=db,
    )

    return AutoDashboardSessionManager.get_status(gen_id, workspace.id)


@router.get("/{generation_id}", response_model=AutoDashboardStatusResponse, status_code=status.HTTP_200_OK)
async def get_auto_dashboard_status(
    generation_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
) -> AutoDashboardStatusResponse:
    workspace, _ = ws_context
    return AutoDashboardSessionManager.get_status(generation_id, workspace.id)


@router.get("/{generation_id}/preview", response_model=AutoDashboardPreviewResponse, status_code=status.HTTP_200_OK)
async def get_auto_dashboard_preview(
    generation_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
) -> AutoDashboardPreviewResponse:
    workspace, _ = ws_context
    return AutoDashboardSessionManager.get_preview(generation_id, workspace.id)


@router.post("/{generation_id}/save", response_model=DashboardDetailResponse, status_code=status.HTTP_201_CREATED)
async def save_auto_dashboard(
    generation_id: uuid.UUID,
    save_req: AutoDashboardSaveRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardDetailResponse:
    workspace, _ = ws_context
    return await AutoDashboardSessionManager.save_dashboard_to_database(
        gen_id=generation_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        save_req=save_req,
        db=db,
    )


@router.post("/{generation_id}/cancel", response_model=dict[str, bool], status_code=status.HTTP_200_OK)
async def cancel_auto_dashboard(
    generation_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
) -> dict[str, bool]:
    workspace, _ = ws_context
    return AutoDashboardSessionManager.cancel_session(generation_id, workspace.id)
