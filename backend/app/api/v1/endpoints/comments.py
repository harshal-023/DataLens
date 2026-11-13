import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.collaboration import (
    CommentResponse,
    CreateCommentRequest,
    UpdateCommentRequest,
)
from app.schemas.common import SuccessEnvelope
from app.services.collaboration_service import CollaborationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/comments", tags=["Comments & Discussions"])


@router.get(
    "",
    response_model=SuccessEnvelope[list[CommentResponse]],
    summary="List Resource Comments",
    description="Lists threaded comments and replies for a dashboard or report.",
)
async def list_comments(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    resource_type: Annotated[str, Query(...)],
    resource_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    comments = await CollaborationService.list_comments(
        db=db,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return SuccessEnvelope(data=comments)


@router.post(
    "",
    response_model=SuccessEnvelope[CommentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Post Comment or Reply",
    description="Creates a threaded comment or reply and dispatches mention/reply notifications.",
)
async def create_comment(
    req: CreateCommentRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(req.workspace_id, current_user.id, db)
    comment = await CollaborationService.create_comment(
        db=db,
        workspace_id=req.workspace_id,
        actor=current_user,
        resource_type=req.resource_type,
        resource_id=req.resource_id,
        content=req.content,
        parent_id=req.parent_id,
    )
    return SuccessEnvelope(data=comment, message="Comment posted successfully.")


@router.patch(
    "/{comment_id}",
    response_model=SuccessEnvelope[CommentResponse],
    summary="Edit Comment",
    description="Updates the content of an existing comment by its author.",
)
async def update_comment(
    comment_id: uuid.UUID,
    req: UpdateCommentRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await CollaborationService.update_comment(
        db=db, comment_id=comment_id, actor=current_user, content=req.content
    )
    return SuccessEnvelope(data=updated, message="Comment updated successfully.")


@router.delete(
    "/{comment_id}",
    response_model=SuccessEnvelope[dict],
    summary="Delete Comment",
    description="Soft-deletes a comment.",
)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await CollaborationService.delete_comment(db=db, comment_id=comment_id, actor=current_user)
    return SuccessEnvelope(data={"deleted": True}, message="Comment deleted.")


@router.post(
    "/{comment_id}/resolve",
    response_model=SuccessEnvelope[CommentResponse],
    summary="Resolve Discussion",
    description="Marks a root discussion thread as resolved.",
)
async def resolve_discussion(
    comment_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await CollaborationService.resolve_discussion(
        db=db, comment_id=comment_id, actor=current_user
    )
    return SuccessEnvelope(data=res, message="Discussion thread marked as resolved.")


@router.post(
    "/{comment_id}/reopen",
    response_model=SuccessEnvelope[CommentResponse],
    summary="Reopen Discussion",
    description="Reopens a previously resolved discussion thread.",
)
async def reopen_discussion(
    comment_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await CollaborationService.reopen_discussion(
        db=db, comment_id=comment_id, actor=current_user
    )
    return SuccessEnvelope(data=res, message="Discussion thread reopened.")

