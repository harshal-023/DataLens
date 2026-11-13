import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.permissions import normalize_role


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Workspace display name")


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="New workspace display name")


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    current_user_role: str = "member"
    created_at: datetime


class WorkspaceMemberResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: str
    joined_at: datetime


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., description="Target role (admin, editor, viewer)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role_norm = normalize_role(v)
        if role_norm == "owner":
            raise ValueError("Cannot promote to owner via role update. Ownership transfer required.")
        return role_norm


class InviteMemberRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user to invite")
    role: str = Field("viewer", description="Role to assign (admin, editor, viewer)")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role_norm = normalize_role(v)
        if role_norm == "owner":
            raise ValueError("Cannot issue an invitation for the Owner role.")
        return role_norm


class InvitationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    created_at: datetime
    inviter_id: uuid.UUID | None = None
    invitation_url: str | None = None  # Included in development mode for easy testing


class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Invitation token received by email")
