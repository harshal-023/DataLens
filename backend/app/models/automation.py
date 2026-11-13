"""SQLAlchemy models for Phase 5D: Automated Data Refresh, Pipeline Orchestration & Background Job Management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class BackgroundJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core background job entity supporting atomic claiming, retries, and lifecycle tracking."""

    __tablename__ = "background_jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # data_import, dataset_refresh, incremental_refresh, pipeline_execution, data_validation, dataset_materialization, dashboard_refresh, report_generation, report_delivery
    status: Mapped[str] = mapped_column(
        String(50), default="QUEUED", nullable=False, index=True
    )  # QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED
    priority: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, index=True
    )  # Higher runs first
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    progress_pct: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    progress_message: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )
    retry_delay_seconds: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    error_classification: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # TRANSIENT, PERMANENT, AUTHENTICATION, VALIDATION, TIMEOUT
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=600, nullable=False
    )
    source_dataset_version_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    output_dataset_version_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    creator: Mapped[User | None] = relationship("User", foreign_keys=[created_by])
    executions: Mapped[list[JobExecution]] = relationship(
        "JobExecution",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobExecution.attempt_number",
        lazy="selectin",
    )
    schedule: Mapped[JobSchedule | None] = relationship(
        "JobSchedule", back_populates="jobs"
    )


class JobExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detailed record of an individual execution attempt for a background job."""

    __tablename__ = "job_executions"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("background_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # RUNNING, SUCCESS, FAILED, CANCELLED
    worker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_classification: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )

    # Relationships
    job: Mapped[BackgroundJob] = relationship(
        "BackgroundJob", back_populates="executions"
    )


class JobSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Timezone-aware recurring or one-time schedule definition."""

    __tablename__ = "job_schedules"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # data_import, dataset_refresh, incremental_refresh, pipeline_execution, workflow, report_generation
    target_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    target_resource_type: Mapped[str] = mapped_column(
        String(50), default="connection", nullable=False
    )  # connection, pipeline, report, workflow
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    frequency: Mapped[str] = mapped_column(
        String(50), default="daily", nullable=False
    )  # one_time, hourly, daily, weekly, monthly, cron
    cron_expression: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    timezone: Mapped[str] = mapped_column(
        String(100), default="UTC", nullable=False
    )
    hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 0=Monday .. 6=Sunday
    day_of_month: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 1..31
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    creator: Mapped[User | None] = relationship("User", foreign_keys=[created_by])
    jobs: Mapped[list[BackgroundJob]] = relationship(
        "BackgroundJob", back_populates="schedule"
    )


class Workflow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Directed Acyclic Graph (DAG) workflow container."""

    __tablename__ = "workflows"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    failure_policy: Mapped[str] = mapped_column(
        String(50), default="STOP_IMMEDIATELY", nullable=False
    )  # STOP_IMMEDIATELY, RETRY_FAILED_STEP, CONTINUE_INDEPENDENT_BRANCHES, REQUIRE_MANUAL_INTERVENTION
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    creator: Mapped[User | None] = relationship("User", foreign_keys=[created_by])
    steps: Mapped[list[WorkflowStep]] = relationship(
        "WorkflowStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
    )
    executions: Mapped[list[WorkflowExecution]] = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="desc(WorkflowExecution.created_at)",
    )


class WorkflowStep(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An individual task node in a workflow DAG."""

    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SOURCE_REFRESH, DATA_VALIDATION, TRANSFORMATION, REPORT_GENERATION
    target_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    depends_on_step_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )  # Array of UUID strings representing ancestor steps
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=600, nullable=False
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False
    )

    # Relationships
    workflow: Mapped[Workflow] = relationship(
        "Workflow", back_populates="steps"
    )
    step_executions: Mapped[list[WorkflowStepExecution]] = relationship(
        "WorkflowStepExecution",
        back_populates="step",
        cascade="all, delete-orphan",
    )


class WorkflowExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single execution run of an entire workflow DAG."""

    __tablename__ = "workflow_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
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
    trigger_type: Mapped[str] = mapped_column(
        String(50), default="manual", nullable=False
    )  # manual, scheduled, api
    status: Mapped[str] = mapped_column(
        String(50), default="QUEUED", nullable=False, index=True
    )  # QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    workflow: Mapped[Workflow] = relationship(
        "Workflow", back_populates="executions"
    )
    workspace: Mapped[Workspace] = relationship("Workspace")
    step_executions: Mapped[list[WorkflowStepExecution]] = relationship(
        "WorkflowStepExecution",
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        order_by="WorkflowStepExecution.created_at",
    )


class WorkflowStepExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution status and output metrics for an individual step in a workflow run."""

    __tablename__ = "workflow_step_executions"

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False
    )  # PENDING, RUNNING, SUCCESS, FAILED, SKIPPED, CANCELLED
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("background_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_version_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    output_version_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )

    # Relationships
    workflow_execution: Mapped[WorkflowExecution] = relationship(
        "WorkflowExecution", back_populates="step_executions"
    )
    step: Mapped[WorkflowStep] = relationship(
        "WorkflowStep", back_populates="step_executions"
    )
    job: Mapped[BackgroundJob | None] = relationship("BackgroundJob")
