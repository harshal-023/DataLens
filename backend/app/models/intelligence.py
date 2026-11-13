import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.user import User
    from app.models.workspace import Workspace


class DatasetProfile(Base, UUIDPrimaryKeyMixin):
    """
    Persisted statistical and semantic profile for an immutable DatasetVersion.
    """
    __tablename__ = "dataset_profiles"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    dataset_version: Mapped["DatasetVersion"] = relationship("DatasetVersion")
    dataset: Mapped["Dataset"] = relationship("Dataset")


class ColumnSemanticMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Semantic definitions and business mappings for columns of a specific DatasetVersion.
    """
    __tablename__ = "column_semantic_mappings"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    semantic_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="text"
    )  # currency, percentage, quantity, date, timestamp, email, phone, geographic_region, customer_identifier, etc.
    logical_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")
    physical_type: Mapped[str] = mapped_column(String(50), nullable=False, default="VARCHAR")
    aggregation_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NONE"
    )  # SUM, AVG, COUNT, COUNT_DISTINCT, MIN, MAX, NONE
    format_string: Mapped[str | None] = mapped_column(String(50), nullable=True)  # INR, USD, PERCENT, INTEGER, etc.
    is_dimension: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_measure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_foreign_key: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mapping_status: Mapped[str] = mapped_column(
        String(50), default="SYSTEM_INFERRED", nullable=False
    )  # AI_SUGGESTED, USER_CONFIRMED, SYSTEM_INFERRED
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    dataset_version: Mapped["DatasetVersion"] = relationship("DatasetVersion")
    dataset: Mapped["Dataset"] = relationship("Dataset")

    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id", "column_name", name="uq_version_column_semantic"
        ),
    )


class BusinessEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Workspace-level business entities (e.g. Customer, Order, Product, Transaction).
    """
    __tablename__ = "business_entities"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="STANDARD")
    identifying_column_pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace")

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_entity_name"),
    )


class DatasetRelationship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Relationships between two datasets in the same workspace.
    """
    __tablename__ = "dataset_relationships"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_column: Mapped[str] = mapped_column(String(255), nullable=False)

    target_dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_column: Mapped[str] = mapped_column(String(255), nullable=False)

    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MANY_TO_ONE"
    )  # ONE_TO_ONE, ONE_TO_MANY, MANY_TO_ONE, MANY_TO_MANY
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="SUGGESTED", nullable=False
    )  # SUGGESTED, CONFIRMED, REJECTED
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    join_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    source_dataset: Mapped["Dataset"] = relationship(
        "Dataset", foreign_keys=[source_dataset_id]
    )
    target_dataset: Mapped["Dataset"] = relationship(
        "Dataset", foreign_keys=[target_dataset_id]
    )


class BusinessContext(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Business domain context and synthesized analytical guidelines for a DatasetVersion.
    """
    __tablename__ = "business_contexts"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_domain: Mapped[str] = mapped_column(
        String(100), nullable=False, default="GENERAL_BUSINESS"
    )  # SALES, FINANCE, MARKETING, CUSTOMER_ANALYTICS, OPERATIONS, INVENTORY, HUMAN_RESOURCES, LOGISTICS, GENERAL_BUSINESS
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    important_entities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    key_dimensions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    important_measures: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    suggested_kpis: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    data_quality_limitations: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    business_assumptions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    dataset_version: Mapped["DatasetVersion"] = relationship("DatasetVersion")
    dataset: Mapped["Dataset"] = relationship("Dataset")


class MetricDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Reusable, validated business metric definitions with versioning and safe formula expressions.
    """
    __tablename__ = "metric_definitions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_columns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    aggregation: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SUM"
    )  # SUM, AVG, COUNT, COUNT_DISTINCT, MIN, MAX, CALCULATED
    filters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    formatting: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CURRENCY"
    )  # CURRENCY, PERCENTAGE, INTEGER, DECIMAL, INR, USD, EUR
    applicable_dimensions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(50), default="VALID", nullable=False
    )  # VALID, INVALID, DRAFT
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    approval_status: Mapped[str] = mapped_column(
        String(50), default="APPROVED", nullable=False
    )  # DRAFT, APPROVED, DEPRECATED
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    dataset: Mapped["Dataset"] = relationship("Dataset")
    owner: Mapped["User"] = relationship("User")
    versions: Mapped[list["MetricVersion"]] = relationship(
        "MetricVersion",
        back_populates="metric",
        cascade="all, delete-orphan",
        order_by="desc(MetricVersion.version_number)",
    )


class MetricVersion(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit history of changes to a MetricDefinition.
    """
    __tablename__ = "metric_versions"

    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    formula: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_columns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    aggregation: Mapped[str] = mapped_column(String(50), nullable=False)
    filters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    formatting: Mapped[str] = mapped_column(String(50), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    metric: Mapped["MetricDefinition"] = relationship(
        "MetricDefinition", back_populates="versions"
    )

    __table_args__ = (
        UniqueConstraint("metric_id", "version_number", name="uq_metric_version_number"),
    )

