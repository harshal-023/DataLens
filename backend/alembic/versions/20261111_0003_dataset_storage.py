"""Dataset versioning enhancements and soft archival

Revision ID: 20261111_0003
Revises: 20261111_0002
Create Date: 2026-11-11 13:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261111_0003"
down_revision: str | None = "20261111_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_archived column to datasets
    op.add_column(
        "datasets",
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # Add columns to dataset_versions
    op.add_column(
        "dataset_versions",
        sa.Column("original_storage_key", sa.String(length=255), server_default="", nullable=False),
    )
    op.add_column(
        "dataset_versions",
        sa.Column("column_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "dataset_versions",
        sa.Column("checksum", sa.String(length=64), server_default="", nullable=False),
    )
    op.add_column(
        "dataset_versions",
        sa.Column("status", sa.String(length=50), server_default="ready", nullable=False),
    )
    op.add_column(
        "dataset_versions",
        sa.Column("error_message", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dataset_versions", "error_message")
    op.drop_column("dataset_versions", "status")
    op.drop_column("dataset_versions", "checksum")
    op.drop_column("dataset_versions", "column_count")
    op.drop_column("dataset_versions", "original_storage_key")
    op.drop_column("datasets", "is_archived")

