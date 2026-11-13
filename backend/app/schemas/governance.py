"""Pydantic schemas for Phase 5C Enterprise Governance, Advanced RBAC, and Security Audit."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Granular Permissions
# ---------------------------------------------------------------------------


class PermissionDefinition(BaseModel):
    code: str
    category: str
    name: str
    description: str


class PermissionsCatalogResponse(BaseModel):
    permissions: list[PermissionDefinition]
    categories: list[str]


# ---------------------------------------------------------------------------
# Custom Roles
# ---------------------------------------------------------------------------


class CustomRoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=1000)
    permissions: list[str] = Field(default_factory=list)


class CustomRoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=1000)
    permissions: list[str] | None = None


class CustomRoleDuplicateRequest(BaseModel):
    new_name: str = Field(..., min_length=2, max_length=100)


class CustomRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    permissions: list[str]
    is_system: bool
    assigned_members_count: int = 0
    created_at: datetime
    updated_at: datetime


class AssignCustomRoleRequest(BaseModel):
    custom_role_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Resource-Level Access Control (RLAC)
# ---------------------------------------------------------------------------


class ResourceAccessPolicyCreate(BaseModel):
    resource_type: str = Field(
        ..., description="dataset, dashboard, report, datasource, pipeline"
    )
    resource_id: uuid.UUID
    user_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    permission: str = Field("viewer", description="viewer, editor, admin")
    is_denied: bool = False


class ResourceAccessPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_name: str | None = None
    user_email: str | None = None
    role_id: uuid.UUID | None = None
    role_name: str | None = None
    permission: str
    is_denied: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Data Access Governance & Column Masking
# ---------------------------------------------------------------------------


class ColumnMaskRule(BaseModel):
    type: str = Field("redact", description="redact, hash, partial")
    clearance_roles: list[str] = Field(default_factory=list)


class DatasetGovernanceUpdate(BaseModel):
    sensitivity_level: str = Field(
        "INTERNAL", description="PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED"
    )
    export_restricted: bool = False
    column_masks: dict[str, ColumnMaskRule] = Field(default_factory=dict)


class DatasetGovernanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str | None = None
    sensitivity_level: str
    export_restricted: bool
    column_masks: dict[str, Any]
    approved_by: uuid.UUID | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    updated_at: datetime


# ---------------------------------------------------------------------------
# Enterprise Audit Logs
# ---------------------------------------------------------------------------


class EnterpriseAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    actor_email: str | None = None
    actor_name: str | None = None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None = None
    timestamp: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    correlation_id: str | None = None
    outcome: str
    metadata_snapshot: dict[str, Any]
    previous_hash: str | None = None
    chained_hash: str
    is_chain_valid: bool = True


class AuditLogListResponse(BaseModel):
    items: list[EnterpriseAuditLogResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Security Events & Incidents
# ---------------------------------------------------------------------------


class SecurityEventStatusUpdate(BaseModel):
    status: str = Field(..., description="OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE")
    notes: str | None = None


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    event_type: str
    severity: str
    details: dict[str, Any]
    status: str
    resolved_by: uuid.UUID | None = None
    resolved_by_name: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class SecurityEventListResponse(BaseModel):
    items: list[SecurityEventResponse]
    total: int


# ---------------------------------------------------------------------------
# User Sessions
# ---------------------------------------------------------------------------


class UserSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    ip_address: str | None = None
    user_agent: str | None = None
    device_label: str | None = None
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_current: bool = False
    is_revoked: bool = False


# ---------------------------------------------------------------------------
# Workspace Security Policies
# ---------------------------------------------------------------------------


class WorkspaceSecurityPolicyUpdate(BaseModel):
    allow_public_share_links: bool | None = None
    max_share_link_days: int | None = Field(None, ge=1, le=365)
    restrict_external_sharing: bool | None = None
    restrict_report_downloads: bool | None = None
    restrict_dataset_exports: bool | None = None
    max_session_hours: int | None = Field(None, ge=1, le=168)
    allowed_invitation_domains: list[str] | None = None
    custom_roles_enabled: bool | None = None
    audit_retention_days: int | None = Field(None, ge=7, le=3650)


class WorkspaceSecurityPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    allow_public_share_links: bool
    max_share_link_days: int
    restrict_external_sharing: bool
    restrict_report_downloads: bool
    restrict_dataset_exports: bool
    max_session_hours: int
    allowed_invitation_domains: list[str]
    custom_roles_enabled: bool
    audit_retention_days: int
    created_at: datetime
    updated_at: datetime

