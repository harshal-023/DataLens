import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.user import User
    from app.models.workspace import Workspace


class DataSourceConnection(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "data_source_connections"

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
    connector_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # postgres, mysql, rest_api, google_sheets, mongodb, s3
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="untested", nullable=False, index=True
    )  # untested, connected, error
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", foreign_keys=[workspace_id])
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    imports: Mapped[list["DataSourceImport"]] = relationship(
        "DataSourceImport",
        back_populates="connection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tables_metadata: Mapped[list["DataSourceTableMetadata"]] = relationship(
        "DataSourceTableMetadata",
        back_populates="connection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refresh_configs: Mapped[list["DataSourceRefreshConfig"]] = relationship(
        "DataSourceRefreshConfig",
        back_populates="connection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Synonym and property access
    source_type = synonym("connector_type")

    @property
    def is_active(self) -> bool:
        return self.status != "disabled"

    @is_active.setter
    def is_active(self, val: bool) -> None:
        if not val:
            self.status = "disabled"



class DataSourceImport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "data_source_imports"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_resource: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # table name, endpoint, collection, worksheet, object path
    import_mode: Mapped[str] = mapped_column(String(50), default="full", nullable=False)  # full, incremental
    watermark_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_watermark_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_size: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, running, completed, failed, cancelled
    rows_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_imported: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    connection: Mapped["DataSourceConnection"] = relationship("DataSourceConnection", back_populates="imports")
    workspace: Mapped["Workspace"] = relationship("Workspace", foreign_keys=[workspace_id])
    target_dataset: Mapped["Dataset | None"] = relationship("Dataset", foreign_keys=[target_dataset_id])
    target_version: Mapped["DatasetVersion | None"] = relationship(
        "DatasetVersion", foreign_keys=[target_version_id]
    )

    # Synonyms for field naming flexibility
    dataset_id = synonym("target_dataset_id")
    dataset_version_id = synonym("target_version_id")
    watermark_value = synonym("last_watermark_value")
    triggered_by = synonym("initiated_by")


class DataSourceTableMetadata(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "data_source_table_metadata"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    database_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(
        String(50), default="table", nullable=False
    )  # table, view, collection, worksheet, endpoint, file
    columns_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    row_count_estimate: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    size_bytes_estimate: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    connection: Mapped["DataSourceConnection"] = relationship(
        "DataSourceConnection", back_populates="tables_metadata"
    )

    last_imported_at = synonym("last_discovered_at")


class DataSourceRefreshConfig(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "data_source_refresh_configs"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_source_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    frequency: Mapped[str] = mapped_column(
        String(50), default="daily", nullable=False
    )  # manual, daily, weekly, monthly, custom_cron
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hour: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Monday, 6=Sunday
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-31
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_execution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_execution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    # Relationships
    connection: Mapped["DataSourceConnection"] = relationship(
        "DataSourceConnection", back_populates="refresh_configs"
    )
    import_job: Mapped["DataSourceImport"] = relationship("DataSourceImport")

    is_active = synonym("is_enabled")
    last_run_at = synonym("last_execution_time")
    next_run_at = synonym("next_execution_time")
