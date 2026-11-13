import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.collaboration import (
    CreateMemberShareRequest,
    CreateShareLinkRequest,
    MemberShareResponse,
    PublicDashboardAccessRequest,
    PublicDashboardResponse,
    PublicReportAccessRequest,
    ShareAccessTokenResponse,
)
from app.schemas.common import SuccessEnvelope
from app.services.collaboration_service import CollaborationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["Collaboration & Sharing"])

# ---------------------------------------------------------------------------
# Dashboard Shares & Share Links
# ---------------------------------------------------------------------------


@router.post(
    "/dashboards/{dashboard_id}/shares",
    response_model=SuccessEnvelope[MemberShareResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Share Dashboard with Workspace Member",
)
async def share_dashboard_with_member(
    dashboard_id: uuid.UUID,
    req: CreateMemberShareRequest,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    share = await CollaborationService.share_resource_with_member(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        resource_type="dashboard",
        resource_id=dashboard_id,
        target_user_id=req.target_user_id,
        permission=req.permission,
    )
    return SuccessEnvelope(data=share, message="Dashboard shared successfully.")


@router.get(
    "/dashboards/{dashboard_id}/shares",
    response_model=SuccessEnvelope[list[MemberShareResponse]],
    summary="List Dashboard Member Shares",
)
async def list_dashboard_shares(
    dashboard_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    shares = await CollaborationService.list_resource_shares(
        db=db, workspace_id=workspace_id, resource_type="dashboard", resource_id=dashboard_id
    )
    return SuccessEnvelope(data=shares)


@router.delete(
    "/dashboards/{dashboard_id}/shares/{share_id}",
    response_model=SuccessEnvelope[dict],
    summary="Revoke Dashboard Member Share",
)
async def revoke_dashboard_share(
    dashboard_id: uuid.UUID,
    share_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await CollaborationService.revoke_resource_share(
        db=db, workspace_id=workspace_id, share_id=share_id, actor=current_user
    )
    return SuccessEnvelope(data={"revoked": True}, message="Share revoked successfully.")


@router.post(
    "/dashboards/{dashboard_id}/links",
    response_model=SuccessEnvelope[ShareAccessTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Dashboard Share Link",
)
async def create_dashboard_share_link(
    dashboard_id: uuid.UUID,
    req: CreateShareLinkRequest,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    link, _ = await CollaborationService.create_share_link(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        resource_type="dashboard",
        resource_id=dashboard_id,
        permission=req.permission,
        allow_download=req.allow_download,
        expires_in_days=req.expires_in_days,
        password=req.password,
    )
    return SuccessEnvelope(data=link, message="Share link generated.")


@router.get(
    "/dashboards/{dashboard_id}/links",
    response_model=SuccessEnvelope[list[ShareAccessTokenResponse]],
    summary="List Dashboard Share Links",
)
async def list_dashboard_share_links(
    dashboard_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    links = await CollaborationService.list_share_links(
        db=db, workspace_id=workspace_id, resource_type="dashboard", resource_id=dashboard_id
    )
    return SuccessEnvelope(data=links)


@router.delete(
    "/dashboards/{dashboard_id}/links/{token_id}",
    response_model=SuccessEnvelope[dict],
    summary="Revoke Dashboard Share Link",
)
async def revoke_dashboard_share_link(
    dashboard_id: uuid.UUID,
    token_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await CollaborationService.revoke_share_link(
        db=db, workspace_id=workspace_id, token_id=token_id, actor=current_user
    )
    return SuccessEnvelope(data={"revoked": True}, message="Share link revoked.")


# ---------------------------------------------------------------------------
# Report Shares & Share Links
# ---------------------------------------------------------------------------


@router.post(
    "/reports/{report_id}/shares",
    response_model=SuccessEnvelope[MemberShareResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Share Report with Workspace Member",
)
async def share_report_with_member(
    report_id: uuid.UUID,
    req: CreateMemberShareRequest,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    share = await CollaborationService.share_resource_with_member(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        resource_type="report",
        resource_id=report_id,
        target_user_id=req.target_user_id,
        permission=req.permission,
    )
    return SuccessEnvelope(data=share, message="Report shared successfully.")


@router.get(
    "/reports/{report_id}/shares",
    response_model=SuccessEnvelope[list[MemberShareResponse]],
    summary="List Report Member Shares",
)
async def list_report_shares(
    report_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    shares = await CollaborationService.list_resource_shares(
        db=db, workspace_id=workspace_id, resource_type="report", resource_id=report_id
    )
    return SuccessEnvelope(data=shares)


@router.delete(
    "/reports/{report_id}/shares/{share_id}",
    response_model=SuccessEnvelope[dict],
    summary="Revoke Report Member Share",
)
async def revoke_report_share(
    report_id: uuid.UUID,
    share_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await CollaborationService.revoke_resource_share(
        db=db, workspace_id=workspace_id, share_id=share_id, actor=current_user
    )
    return SuccessEnvelope(data={"revoked": True}, message="Report share revoked.")


@router.post(
    "/reports/{report_id}/links",
    response_model=SuccessEnvelope[ShareAccessTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Report Share / Download Link",
)
async def create_report_share_link(
    report_id: uuid.UUID,
    req: CreateShareLinkRequest,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    link, _ = await CollaborationService.create_share_link(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        resource_type="report",
        resource_id=report_id,
        permission="viewer",
        allow_download=req.allow_download,
        expires_in_days=req.expires_in_days,
        password=req.password,
    )
    return SuccessEnvelope(data=link, message="Report link generated.")


@router.get(
    "/reports/{report_id}/links",
    response_model=SuccessEnvelope[list[ShareAccessTokenResponse]],
    summary="List Report Share Links",
)
async def list_report_share_links(
    report_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    links = await CollaborationService.list_share_links(
        db=db, workspace_id=workspace_id, resource_type="report", resource_id=report_id
    )
    return SuccessEnvelope(data=links)


@router.delete(
    "/reports/{report_id}/links/{token_id}",
    response_model=SuccessEnvelope[dict],
    summary="Revoke Report Share Link",
)
async def revoke_report_share_link(
    report_id: uuid.UUID,
    token_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await CollaborationService.revoke_share_link(
        db=db, workspace_id=workspace_id, token_id=token_id, actor=current_user
    )
    return SuccessEnvelope(data={"revoked": True}, message="Report share link revoked.")


# ---------------------------------------------------------------------------
# Public Link Resolvers (No Login Required)
# ---------------------------------------------------------------------------


@router.post(
    "/shared/dashboards/{token}",
    response_model=SuccessEnvelope[PublicDashboardResponse],
    summary="Resolve Shared Dashboard",
)
async def resolve_shared_dashboard(
    token: str,
    req: PublicDashboardAccessRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await CollaborationService.resolve_shared_dashboard(
        db=db, raw_token=token, password=req.password
    )
    return SuccessEnvelope(data=res)


@router.post(
    "/shared/reports/{token}/download",
    summary="Download Shared Report",
)
async def download_shared_report(
    token: str,
    req: PublicReportAccessRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    file_bytes, filename, media_type = await CollaborationService.resolve_shared_report_download(
        db=db, raw_token=token, password=req.password
    )
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

