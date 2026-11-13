"""SQLAlchemy models for Phase 5C Enterprise Governance, Advanced RBAC, and Security Audit."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class CustomRole(Base, UUIDPrimaryKeyMixin):
    """Custom administrative or operational roles defined within a workspace."""

    __tablename__ = "custom_roles"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_custom_roles_workspace_name"),
    )


class ResourceAccessPolicy(Base, UUIDPrimaryKeyMixin):
    """Granular resource-level access grants and explicit denies (RLAC)."""

    __tablename__ = "resource_access_policies"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'dataset' | 'dashboard' | 'report' | 'datasource' | 'pipeline'
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_roles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    permission: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False)
    is_denied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class DatasetGovernance(Base, UUIDPrimaryKeyMixin):
    """Data classification, sensitive column masking, and export governance."""

    __tablename__ = "dataset_governance"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    sensitivity_level: Mapped[str] = mapped_column(
        String(30), default="INTERNAL", nullable=False, index=True
    )  # 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'
    export_restricted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    column_masks: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # { col_name: { "type": "redact"|"hash"|"partial", "clearance_roles": [...] } }
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class EnterpriseAuditLog(Base, UUIDPrimaryKeyMixin):
    """Tamper-evident, chained enterprise audit event record."""

    __tablename__ = "enterprise_audit_logs"

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(
        String(20), default="SUCCESS", nullable=False, index=True
    )  # 'SUCCESS' | 'FAILURE' | 'DENIED'
    metadata_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chained_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class SecurityEvent(Base, UUIDPrimaryKeyMixin):
    """Security monitoring incidents, anomaly detection, and investigative logs."""

    __tablename__ = "security_events"

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(20), default="MEDIUM", nullable=False, index=True
    )  # 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="OPEN", nullable=False, index=True
    )  # 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'FALSE_POSITIVE'
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )


class UserSession(Base, UUIDPrimaryKeyMixin):
    """Active user authentication sessions and device activity tracking."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)


class WorkspaceSecurityPolicy(Base, UUIDPrimaryKeyMixin):
    """Configurable security boundaries, sharing restrictions, and retention policies."""

    __tablename__ = "workspace_security_policies"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    allow_public_share_links: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_share_link_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    restrict_external_sharing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restrict_report_downloads: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restrict_dataset_exports: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_session_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    allowed_invitation_domains: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    custom_roles_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    audit_retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
