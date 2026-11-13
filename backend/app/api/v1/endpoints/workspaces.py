import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.collaboration import (
    ActivityListResponse,
)
from app.schemas.collaboration import (
    InvitationResponse as CollabInvitationResponse,
)
from app.schemas.common import SuccessEnvelope
from app.schemas.workspace import (
    InvitationResponse,
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.services.collaboration_service import CollaborationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get(
    "",
    response_model=SuccessEnvelope[list[WorkspaceResponse]],
    summary="List Workspaces",
    description="Returns all workspaces the authenticated user belongs to.",
)
async def list_workspaces(
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    workspaces = await WorkspaceService.list_user_workspaces(current_user.id, db)
    return SuccessEnvelope(data=workspaces)


@router.post(
    "",
    response_model=SuccessEnvelope[WorkspaceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
    description="Creates a new workspace and assigns the creator the Owner role.",
)
async def create_workspace(
    req: WorkspaceCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ws = await WorkspaceService.create_workspace(current_user, req, db)
    return SuccessEnvelope(data=ws, message="Workspace created successfully.")


@router.get(
    "/{workspace_id}",
    response_model=SuccessEnvelope[WorkspaceResponse],
    summary="Get Workspace Details",
    description="Fetches workspace details if caller is a member.",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ws, role = await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    return SuccessEnvelope(
        data=WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            current_user_role=role,
            created_at=ws.created_at,
        )
    )


@router.patch(
    "/{workspace_id}",
    response_model=SuccessEnvelope[WorkspaceResponse],
    summary="Update Workspace",
    description="Updates workspace name. Permitted for Owner and Admin roles.",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    req: WorkspaceUpdateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await WorkspaceService.update_workspace(workspace_id, current_user.id, req, db)
    return SuccessEnvelope(data=updated, message="Workspace updated successfully.")


@router.delete(
    "/{workspace_id}",
    response_model=SuccessEnvelope[dict],
    summary="Delete Workspace",
    description="Deletes workspace. Strictly restricted to workspace Owner. Cannot delete user's only workspace.",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.delete_workspace(workspace_id, current_user.id, db)
    return SuccessEnvelope(data={"deleted": True}, message="Workspace deleted successfully.")


# ==========================================
# MEMBERSHIP & INVITATION SUB-ROUTES
# ==========================================

@router.get(
    "/{workspace_id}/members",
    response_model=SuccessEnvelope[list[WorkspaceMemberResponse]],
    summary="List Workspace Members",
    description="Returns all active members and their roles within the workspace.",
)
async def list_workspace_members(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    members = await WorkspaceService.list_members(workspace_id, current_user.id, db)
    return SuccessEnvelope(data=members)


@router.post(
    "/{workspace_id}/invitations",
    response_model=SuccessEnvelope[InvitationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite Member",
    description="Generates an invitation for a new member. Permitted for Owner and Admin roles.",
)
async def invite_member(
    workspace_id: uuid.UUID,
    req: InviteMemberRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    invitation, raw_token = await WorkspaceService.invite_member(workspace_id, current_user, req, db)
    await CollaborationService.log_activity(
        db=db,
        workspace_id=workspace_id,
        actor_id=current_user.id,
        event_type="invitation_sent",
        resource_type="invitation",
        resource_id=invitation.id,
        summary=f"{current_user.full_name} invited {req.email} as {req.role}",
        payload={"email": req.email, "role": req.role},
    )
    invitation_url = f"http://localhost:5173/invitations/accept?token={raw_token}"

    return SuccessEnvelope(
        data=InvitationResponse(
            id=invitation.id,
            workspace_id=invitation.workspace_id,
            email=invitation.email,
            role=invitation.role,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            inviter_id=invitation.inviter_id,
            invitation_url=invitation_url,
        ),
        message=f"Invitation sent to {invitation.email}.",
    )


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=SuccessEnvelope[WorkspaceMemberResponse],
    summary="Update Member Role",
    description="Updates role of an existing member. Prevents demoting the last Owner or promoting directly to Owner.",
)
async def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    req: UpdateMemberRoleRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await WorkspaceService.update_member_role(workspace_id, current_user, user_id, req, db)
    await CollaborationService.log_activity(
        db=db,
        workspace_id=workspace_id,
        actor_id=current_user.id,
        event_type="member_role_changed",
        resource_type="user",
        resource_id=user_id,
        summary=f"{current_user.full_name} updated {updated.full_name}'s role to {updated.role}",
        payload={"target_user_id": str(user_id), "new_role": updated.role},
    )
    return SuccessEnvelope(data=updated, message="Member role updated successfully.")


@router.delete(
    "/{workspace_id}/members/{user_id}",
    response_model=SuccessEnvelope[dict],
    summary="Remove Member / Leave Workspace",
    description="Removes a member from workspace or allows a member to leave. Prevents removing the last Owner.",
)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.remove_member(workspace_id, current_user, user_id, db)
    await CollaborationService.log_activity(
        db=db,
        workspace_id=workspace_id,
        actor_id=current_user.id,
        event_type="member_removed",
        resource_type="user",
        resource_id=user_id,
        summary=f"{current_user.full_name} removed member from workspace",
        payload={"target_user_id": str(user_id)},
    )
    return SuccessEnvelope(data={"removed": True}, message="Member removed from workspace.")


@router.get(
    "/{workspace_id}/invitations",
    response_model=SuccessEnvelope[list[CollabInvitationResponse]],
    summary="List Workspace Invitations",
    description="Lists all pending, accepted, or revoked invitations in workspace.",
)
async def list_workspace_invitations(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    invitations = await CollaborationService.list_workspace_invitations(
        db=db, workspace_id=workspace_id, status_filter=status
    )
    return SuccessEnvelope(data=invitations)


@router.post(
    "/{workspace_id}/invitations/{invitation_id}/resend",
    response_model=SuccessEnvelope[CollabInvitationResponse],
    summary="Resend Invitation",
    description="Resends a pending workspace invitation and refreshes token expiration.",
)
async def resend_workspace_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    res = await CollaborationService.resend_invitation(
        db=db, workspace_id=workspace_id, invitation_id=invitation_id, actor=current_user
    )
    return SuccessEnvelope(data=res, message="Invitation resent successfully.")


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    response_model=SuccessEnvelope[dict],
    summary="Revoke Invitation",
    description="Revokes an active pending workspace invitation.",
)
async def revoke_workspace_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await CollaborationService.revoke_invitation(
        db=db, workspace_id=workspace_id, invitation_id=invitation_id, actor=current_user
    )
    return SuccessEnvelope(data={"revoked": True}, message="Invitation revoked successfully.")


@router.get(
    "/{workspace_id}/activity",
    response_model=SuccessEnvelope[ActivityListResponse],
    summary="Get Workspace Activity Feed",
    description="Lists historical collaboration, access, and modification activities.",
)
async def get_workspace_activity(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    event_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    feed = await CollaborationService.get_workspace_activity(
        db=db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        resource_type=resource_type,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )
    return SuccessEnvelope(data=feed)

