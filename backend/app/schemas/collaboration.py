"""Pydantic schemas for Phase 5B Team Collaboration, Sharing, Discussions, and Notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Workspace Members & Invitations
# ---------------------------------------------------------------------------

class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role: str = Field("viewer", description="viewer, editor, admin")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., description="viewer, editor, admin, owner")


class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    email: str
    role: str
    joined_at: datetime


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    resend_count: int
    created_at: datetime
    inviter_id: uuid.UUID | None = None
    inviter_name: str | None = None
    invitation_url: str | None = None


class InvitationDetailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    inviter_name: str
    email: str
    role: str
    status: str
    expires_at: datetime
    is_valid: bool


InvitationPublicDetailResponse = InvitationDetailResponse


class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=16)


class DeclineInvitationRequest(BaseModel):
    token: str = Field(..., min_length=16)


# ---------------------------------------------------------------------------
# Resource Shares (Member-Level)
# ---------------------------------------------------------------------------

class MemberShareCreate(BaseModel):
    user_id: uuid.UUID | None = None
    target_user_id: uuid.UUID | None = None
    permission: str = Field("viewer", description="viewer or editor")

    @property
    def recipient_id(self) -> uuid.UUID:
        return self.target_user_id or self.user_id or uuid.uuid4()


CreateMemberShareRequest = MemberShareCreate


class MemberShareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    shared_with_user_id: uuid.UUID
    shared_with_name: str
    shared_with_email: str
    shared_by_user_id: uuid.UUID | None = None
    permission: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Controlled / Public Share Links
# ---------------------------------------------------------------------------

class ShareLinkCreate(BaseModel):
    permission: str = Field("viewer", description="viewer or editor")
    allow_download: bool = True
    expires_in_days: int | None = Field(None, ge=1, le=365)
    expires_at: datetime | None = None
    password: str | None = Field(None, min_length=4, max_length=100)


CreateShareLinkRequest = ShareLinkCreate


class ShareLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    permission: str
    allow_download: bool
    has_password: bool
    expires_at: datetime | None = None
    is_revoked: bool
    access_count: int
    last_accessed_at: datetime | None = None
    share_url: str
    created_at: datetime


ShareAccessTokenResponse = ShareLinkResponse


class DashboardDuplicateRequest(BaseModel):
    target_workspace_id: uuid.UUID | None = None
    new_title: str | None = None


class PublicDashboardAccessRequest(BaseModel):
    password: str | None = None


class PublicReportAccessRequest(BaseModel):
    password: str | None = None



class ShareLinkVerifyRequest(BaseModel):
    password: str | None = None


class PublicDashboardResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    layout_config: dict[str, Any]
    widgets: list[dict[str, Any]]
    filters: list[dict[str, Any]]
    allow_download: bool
    permission: str


# ---------------------------------------------------------------------------
# Comments & Discussions
# ---------------------------------------------------------------------------

class CommentCreate(BaseModel):
    workspace_id: uuid.UUID
    resource_type: str = Field(..., description="dashboard or report")
    resource_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=10000)
    parent_id: uuid.UUID | None = None
    mentions: list[str] = Field(default_factory=list)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


CreateCommentRequest = CommentCreate
UpdateCommentRequest = CommentUpdate


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    author_id: uuid.UUID
    author_name: str
    author_email: str
    content: str
    mentions: list[str]
    is_resolved: bool
    resolved_by_id: uuid.UUID | None = None
    resolved_by_name: str | None = None
    resolved_at: datetime | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    replies: list[CommentResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    actor_name: str | None = None
    event_type: str
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    title: str
    message: str
    data: dict[str, Any]
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    workspace_id: uuid.UUID
    email_notifications: bool
    in_app_notifications: bool
    mention_notifications: bool
    share_notifications: bool


class NotificationPreferenceUpdate(BaseModel):
    email_notifications: bool | None = None
    in_app_notifications: bool | None = None
    mention_notifications: bool | None = None
    share_notifications: bool | None = None


# ---------------------------------------------------------------------------
# Workspace Activity Feed
# ---------------------------------------------------------------------------

class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    actor_name: str | None = None
    event_type: str
    resource_type: str
    resource_id: uuid.UUID | None = None
    summary: str
    metadata_snapshot: dict[str, Any]
    created_at: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int

