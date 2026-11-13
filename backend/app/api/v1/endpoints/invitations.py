from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.collaboration import InvitationPublicDetailResponse
from app.schemas.common import SuccessEnvelope
from app.schemas.workspace import AcceptInvitationRequest, WorkspaceResponse
from app.services.collaboration_service import CollaborationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/invitations", tags=["Invitations"])


@router.get(
    "/{token}",
    response_model=SuccessEnvelope[InvitationPublicDetailResponse],
    summary="Get Invitation Details",
    description="Inspect public workspace invitation details before accepting.",
)
async def get_invitation_details(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    details = await CollaborationService.get_invitation_by_token(db=db, token=token)
    return SuccessEnvelope(data=details)


@router.post(
    "/{token}/accept",
    response_model=SuccessEnvelope[dict],
    summary="Accept Invitation by Token Path",
    description="Accept workspace invitation for authenticated user.",
)
async def accept_invitation_by_token(
    token: str,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await CollaborationService.accept_invitation(db=db, token=token, user=current_user)
    return SuccessEnvelope(data=res, message=f"Successfully joined {res.get('workspace_name', 'workspace')}.")


@router.post(
    "/{token}/decline",
    response_model=SuccessEnvelope[dict],
    summary="Decline Invitation",
    description="Decline workspace invitation.",
)
async def decline_invitation(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await CollaborationService.decline_invitation(db=db, token=token)
    return SuccessEnvelope(data={"success": True}, message="Invitation declined.")


@router.post(
    "/accept",
    response_model=SuccessEnvelope[WorkspaceResponse],
    summary="Accept Workspace Invitation (Legacy Body)",
    description="Validates single-use invitation token and adds authenticated user to workspace.",
)
async def accept_invitation(
    req: AcceptInvitationRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Backward compatible acceptance using workspace service
    ws_resp = await WorkspaceService.accept_invitation(req.token, current_user, db)
    return SuccessEnvelope(data=ws_resp, message=f"Successfully joined {ws_resp.name}.")
