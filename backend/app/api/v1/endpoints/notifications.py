import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.collaboration import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
)
from app.schemas.common import SuccessEnvelope
from app.services.collaboration_service import CollaborationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=SuccessEnvelope[list[NotificationResponse]],
    summary="List User Notifications",
)
async def list_notifications(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    notifications = await CollaborationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return SuccessEnvelope(data=notifications)


@router.get(
    "/unread-count",
    response_model=SuccessEnvelope[dict],
    summary="Get Unread Notification Count",
)
async def get_unread_count(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    count = await CollaborationService.get_unread_count(
        db=db, user_id=current_user.id, workspace_id=workspace_id
    )
    return SuccessEnvelope(data={"unread_count": count})


@router.patch(
    "/{notification_id}/read",
    response_model=SuccessEnvelope[NotificationResponse],
    summary="Mark Notification as Read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    notif = await CollaborationService.mark_notification_as_read(
        db=db, notification_id=notification_id, user_id=current_user.id
    )
    return SuccessEnvelope(data=notif, message="Notification marked as read.")


@router.post(
    "/mark-all-read",
    response_model=SuccessEnvelope[dict],
    summary="Mark All Notifications as Read",
)
async def mark_all_notifications_read(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await CollaborationService.mark_all_read(
        db=db, user_id=current_user.id, workspace_id=workspace_id
    )
    return SuccessEnvelope(data={"marked": True}, message="All notifications marked as read.")


@router.delete(
    "/{notification_id}",
    response_model=SuccessEnvelope[dict],
    summary="Dismiss Notification",
)
async def dismiss_notification(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await CollaborationService.dismiss_notification(
        db=db, notification_id=notification_id, user_id=current_user.id
    )
    return SuccessEnvelope(data={"dismissed": True}, message="Notification dismissed.")


@router.get(
    "/preferences",
    response_model=SuccessEnvelope[NotificationPreferenceResponse],
    summary="Get Notification Preferences",
)
async def get_notification_preferences(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    pref = await CollaborationService.get_or_create_preferences(
        db=db, user_id=current_user.id, workspace_id=workspace_id
    )
    return SuccessEnvelope(data=NotificationPreferenceResponse.model_validate(pref))


@router.put(
    "/preferences",
    response_model=SuccessEnvelope[NotificationPreferenceResponse],
    summary="Update Notification Preferences",
)
async def update_notification_preferences(
    req: NotificationPreferenceUpdate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    updated = await CollaborationService.update_preferences(
        db=db, user_id=current_user.id, workspace_id=workspace_id, req=req
    )
    return SuccessEnvelope(data=updated, message="Preferences updated successfully.")


@router.get(
    "/stream",
    summary="Real-time Notification SSE Stream",
)
async def stream_notifications(
    current_user: Annotated[User, Depends(require_active_user)],
):
    queue = CollaborationService.subscribe_notifications(current_user.id)

    async def event_generator():
        try:
            # Yield initial connection message
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'user_id': str(current_user.id)})}\n\n"
            while True:
                try:
                    # Wait for next event or send heartbeat every 15 seconds
                    notification = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: notification\ndata: {json.dumps(notification)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            CollaborationService.unsubscribe_notifications(current_user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
