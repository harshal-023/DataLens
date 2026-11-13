from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.auth import UpdateUserRequest, UserProfileResponse
from app.schemas.common import SuccessEnvelope
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch(
    "/me",
    response_model=SuccessEnvelope[UserProfileResponse],
    summary="Update Profile",
    description="Updates permitted user profile fields (e.g. full_name). Cannot modify email, status, or roles.",
)
async def update_profile(
    req: UpdateUserRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user.full_name = req.full_name.strip()
    await db.commit()
    await db.refresh(current_user)

    workspaces = await WorkspaceService.list_user_workspaces(current_user.id, db)
    default_ws_id = workspaces[0].id if workspaces else None

    return SuccessEnvelope(
        data=UserProfileResponse(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            default_workspace_id=default_ws_id,
        ),
        message="Profile updated successfully.",
    )
