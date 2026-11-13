"""Unified AI Architecture – Gemini + Local AI (Ollama) + Hybrid Routing (Phase 6A)

Revision ID: 20261112_0013
Revises: 20261112_0012
Create Date: 2026-11-12 15:28:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261112_0013"
down_revision: Union[str, None] = "20261112_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. AI Privacy Policies Table
    op.create_table(
        "ai_privacy_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("routing_mode", sa.String(50), nullable=False, server_default="HYBRID"),
        sa.Column("cloud_ai_permitted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("local_only_enforced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_sample_values", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_sensitivity_for_local_only", sa.String(50), nullable=False, server_default="CONFIDENTIAL"),
        sa.Column("default_local_model", sa.String(100), nullable=False, server_default="gemma3:4b"),
        sa.Column("default_cloud_model", sa.String(100), nullable=False, server_default="gemini-3.5-flash"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_privacy_policies_workspace_id", "ai_privacy_policies", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("ai_privacy_policies")

