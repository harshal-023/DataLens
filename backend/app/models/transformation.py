import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.user import User
    from app.models.workspace import Workspace


class TransformationPipeline(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transformation_pipelines"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_dataset_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, active, archived

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    steps: Mapped[list["TransformationStep"]] = relationship(
        "TransformationStep",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="TransformationStep.step_order",
    )
    runs: Mapped[list["TransformationRun"]] = relationship(
        "TransformationRun",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="desc(TransformationRun.created_at)",
    )


class TransformationStep(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transformation_steps"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformation_pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # join, append, clean_nulls, clean_duplicates, type_cast, string_op, formula, filter, select_columns
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    input_references: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    pipeline: Mapped["TransformationPipeline"] = relationship("TransformationPipeline", back_populates="steps")


class TransformationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transformation_runs"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformation_pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_dataset_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    output_dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, running, completed, failed
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    pipeline: Mapped["TransformationPipeline"] = relationship("TransformationPipeline", back_populates="runs")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    output_dataset: Mapped[Optional["Dataset"]] = relationship("Dataset")
    output_dataset_version: Mapped[Optional["DatasetVersion"]] = relationship("DatasetVersion")
