import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class ReportTemplate(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "report_templates"

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="custom", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    default_sections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    workspace: Mapped[Optional["Workspace"]] = relationship("Workspace")
    creator: Mapped[Optional["User"]] = relationship("User")
    reports: Mapped[list["BusinessReport"]] = relationship("BusinessReport", back_populates="template")

    def __repr__(self) -> str:
        return f"<ReportTemplate id={self.id} name={self.name} category={self.category}>"


class BusinessReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "business_reports"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), default="custom", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="published", nullable=False)  # draft, published, archived
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    source_dashboard_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    source_dataset_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    source_model_run_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
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
    workspace: Mapped["Workspace"] = relationship("Workspace")
    template: Mapped[Optional["ReportTemplate"]] = relationship("ReportTemplate", back_populates="reports")
    owner: Mapped[Optional["User"]] = relationship("User")
    runs: Mapped[list["ReportRun"]] = relationship("ReportRun", back_populates="report", cascade="all, delete-orphan", lazy="selectin")
    schedules: Mapped[list["ReportSchedule"]] = relationship("ReportSchedule", back_populates="report", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<BusinessReport id={self.id} title={self.title} type={self.report_type}>"


class ReportRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "report_runs"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_reports.id", ondelete="CASCADE"),
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
    )
    trigger_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual, scheduled, api
    execution_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, running, completed, failed
    report_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    applied_filters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    source_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    generated_files: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    execution_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    report: Mapped["BusinessReport"] = relationship("BusinessReport", back_populates="runs")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<ReportRun id={self.id} report_id={self.report_id} status={self.execution_status}>"


class ReportSchedule(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "report_schedules"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    frequency: Mapped[str] = mapped_column(String(50), default="weekly", nullable=False)  # daily, weekly, monthly
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Monday, 6=Sunday
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-31
    hour: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    next_execution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_execution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_execution_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    delivery_configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    report: Mapped["BusinessReport"] = relationship("BusinessReport", back_populates="schedules")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<ReportSchedule id={self.id} report_id={self.report_id} freq={self.frequency} enabled={self.is_enabled}>"
