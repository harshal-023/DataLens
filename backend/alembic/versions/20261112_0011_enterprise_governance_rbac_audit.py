"""Enterprise Governance, Advanced RBAC, and Security Audit (Phase 5C)

Revision ID: 20261112_0011
Revises: 20261112_0010
Create Date: 2026-11-12 14:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261112_0011"
down_revision: Union[str, None] = "20261112_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Custom Roles Table
    op.create_table(
        "custom_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "name", name="uq_custom_roles_workspace_name"),
    )
    op.create_index("ix_custom_roles_workspace_id", "custom_roles", ["workspace_id"])

    # 2. Add custom_role_id to workspace_memberships
    op.add_column(
        "workspace_memberships",
        sa.Column("custom_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("custom_roles.id", ondelete="SET NULL"), nullable=True),
    )

    # 3. Resource Access Policies Table
    op.create_table(
        "resource_access_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("custom_roles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("permission", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_denied", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_resource_access_policies_ws", "resource_access_policies", ["workspace_id"])
    op.create_index("ix_resource_access_policies_res", "resource_access_policies", ["resource_type", "resource_id"])
    op.create_index("ix_resource_access_policies_user", "resource_access_policies", ["user_id"])

    # 4. Dataset Governance Table
    op.create_table(
        "dataset_governance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sensitivity_level", sa.String(30), nullable=False, server_default="INTERNAL"),
        sa.Column("export_restricted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("column_masks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dataset_governance_ws", "dataset_governance", ["workspace_id"])
    op.create_index("ix_dataset_governance_dataset", "dataset_governance", ["dataset_id"])

    # 5. Enterprise Audit Logs Table
    op.create_table(
        "enterprise_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False, server_default="SUCCESS"),
        sa.Column("metadata_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("chained_hash", sa.String(64), nullable=False),
    )
    op.create_index("ix_audit_logs_ws", "enterprise_audit_logs", ["workspace_id"])
    op.create_index("ix_audit_logs_actor", "enterprise_audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "enterprise_audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "enterprise_audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_chained_hash", "enterprise_audit_logs", ["chained_hash"])

    # 6. Security Events Table
    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_security_events_ws", "security_events", ["workspace_id"])
    op.create_index("ix_security_events_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])
    op.create_index("ix_security_events_status", "security_events", ["status"])

    # 7. User Sessions Table
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("device_label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["session_token_hash"])

    # 8. Workspace Security Policies Table
    op.create_table(
        "workspace_security_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("allow_public_share_links", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_share_link_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("restrict_external_sharing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("restrict_report_downloads", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("restrict_dataset_exports", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_session_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("allowed_invitation_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("custom_roles_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("audit_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ws_sec_policies_ws", "workspace_security_policies", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("workspace_security_policies")
    op.drop_table("user_sessions")
    op.drop_table("security_events")
    op.drop_table("enterprise_audit_logs")
    op.drop_table("dataset_governance")
    op.drop_table("resource_access_policies")
    op.drop_column("workspace_memberships", "custom_role_id")
    op.drop_table("custom_roles")

