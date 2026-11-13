"""Dataset-Aware AI Intelligence & Business Semantic Layer (Phase 6B)

Revision ID: 20261112_0014
Revises: 20261112_0013
Create Date: 2026-11-12 15:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261112_0014"
down_revision: Union[str, None] = "20261112_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dataset Profiles
    op.create_table(
        "dataset_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("profile_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dataset_profiles_dataset_version_id", "dataset_profiles", ["dataset_version_id"])
    op.create_index("ix_dataset_profiles_dataset_id", "dataset_profiles", ["dataset_id"])

    # 2. Column Semantic Mappings
    op.create_table(
        "column_semantic_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("column_name", sa.String(255), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("semantic_type", sa.String(50), nullable=False, server_default="text"),
        sa.Column("logical_type", sa.String(50), nullable=False, server_default="string"),
        sa.Column("physical_type", sa.String(50), nullable=False, server_default="VARCHAR"),
        sa.Column("aggregation_method", sa.String(50), nullable=False, server_default="NONE"),
        sa.Column("format_string", sa.String(50), nullable=True),
        sa.Column("is_dimension", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_measure", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_primary_key", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_foreign_key", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mapping_status", sa.String(50), nullable=False, server_default="SYSTEM_INFERRED"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "confirmed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dataset_version_id", "column_name", name="uq_version_column_semantic"),
    )
    op.create_index("ix_column_semantic_mappings_dataset_version_id", "column_semantic_mappings", ["dataset_version_id"])
    op.create_index("ix_column_semantic_mappings_dataset_id", "column_semantic_mappings", ["dataset_id"])

    # 3. Business Entities
    op.create_table(
        "business_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=False, server_default="STANDARD"),
        sa.Column("identifying_column_pattern", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "name", name="uq_workspace_entity_name"),
    )
    op.create_index("ix_business_entities_workspace_id", "business_entities", ["workspace_id"])

    # 4. Dataset Relationships
    op.create_table(
        "dataset_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_column", sa.String(255), nullable=False),
        sa.Column(
            "target_dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_column", sa.String(255), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False, server_default="MANY_TO_ONE"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("status", sa.String(50), nullable=False, server_default="SUGGESTED"),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("join_warning", sa.Text(), nullable=True),
        sa.Column(
            "confirmed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dataset_relationships_workspace_id", "dataset_relationships", ["workspace_id"])
    op.create_index("ix_dataset_relationships_source_dataset_id", "dataset_relationships", ["source_dataset_id"])
    op.create_index("ix_dataset_relationships_target_dataset_id", "dataset_relationships", ["target_dataset_id"])

    # 5. Business Contexts
    op.create_table(
        "business_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("business_domain", sa.String(100), nullable=False, server_default="GENERAL_BUSINESS"),
        sa.Column("purpose", sa.Text(), nullable=False, server_default=""),
        sa.Column("important_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("key_dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("important_measures", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("suggested_kpis", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("data_quality_limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("business_assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_user_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "confirmed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_business_contexts_dataset_version_id", "business_contexts", ["dataset_version_id"])
    op.create_index("ix_business_contexts_dataset_id", "business_contexts", ["dataset_id"])

    # 6. Metric Definitions
    op.create_table(
        "metric_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("formula", sa.String(1000), nullable=False),
        sa.Column("source_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("aggregation", sa.String(50), nullable=False, server_default="SUM"),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("formatting", sa.String(50), nullable=False, server_default="CURRENCY"),
        sa.Column("applicable_dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("validation_status", sa.String(50), nullable=False, server_default="VALID"),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approval_status", sa.String(50), nullable=False, server_default="APPROVED"),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_metric_definitions_workspace_id", "metric_definitions", ["workspace_id"])
    op.create_index("ix_metric_definitions_dataset_id", "metric_definitions", ["dataset_id"])

    # 7. Metric Versions
    op.create_table(
        "metric_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "metric_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("metric_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("formula", sa.String(1000), nullable=False),
        sa.Column("source_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("aggregation", sa.String(50), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("formatting", sa.String(50), nullable=False),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("metric_id", "version_number", name="uq_metric_version_number"),
    )
    op.create_index("ix_metric_versions_metric_id", "metric_versions", ["metric_id"])


def downgrade() -> None:
    op.drop_table("metric_versions")
    op.drop_table("metric_definitions")
    op.drop_table("business_contexts")
    op.drop_table("dataset_relationships")
    op.drop_table("business_entities")
    op.drop_table("column_semantic_mappings")
    op.drop_table("dataset_profiles")

