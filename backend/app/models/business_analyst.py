import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class BusinessInsight(Base):
    __tablename__ = "business_insights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    generation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insight_generation_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # performance, trend, anomaly, risk, opportunity
    severity: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    status: Mapped[str] = mapped_column(String(50), index=True, default="NEW", nullable=False)  # NEW, REVIEWED, ACKNOWLEDGED, INVESTIGATING, RESOLVED, DISMISSED
    
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    affected_metric: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    affected_dimension: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_segment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    priority_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_investigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    
    ai_provider: Mapped[str] = mapped_column(String(50), default="deterministic", nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    evidence_items: Mapped[list["InsightEvidence"]] = relationship(
        "InsightEvidence", back_populates="insight", cascade="all, delete-orphan"
    )
    comments: Mapped[list["InsightComment"]] = relationship(
        "InsightComment", back_populates="insight", cascade="all, delete-orphan", order_by="InsightComment.created_at.asc()"
    )
    assessments: Mapped[list["InsightAssessment"]] = relationship(
        "InsightAssessment", back_populates="insight", cascade="all, delete-orphan", order_by="InsightAssessment.created_at.asc()"
    )
    assignments: Mapped[list["InsightAssignment"]] = relationship(
        "InsightAssignment", back_populates="insight", cascade="all, delete-orphan", order_by="InsightAssignment.created_at.asc()"
    )


class InsightEvidence(Base):
    __tablename__ = "insight_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_insights.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)  # kpi, trend_metric, anomaly_point, concentration_ratio, contribution_share, sql_query
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    baseline_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_value: Mapped[str] = mapped_column(String(100), nullable=False)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    supporting_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    calculation_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    insight: Mapped["BusinessInsight"] = relationship("BusinessInsight", back_populates="evidence_items")


class InsightAssessment(Base):
    __tablename__ = "insight_assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_insights.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # reassessment_on_refresh, manual_audit, ai_validation
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status_change: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    insight: Mapped["BusinessInsight"] = relationship("BusinessInsight", back_populates="assessments")


class InsightAssignment(Base):
    __tablename__ = "insight_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_insights.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_to_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    previous_assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assignment_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    insight: Mapped["BusinessInsight"] = relationship("BusinessInsight", back_populates="assignments")


class InsightComment(Base):
    __tablename__ = "insight_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_insights.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    insight: Mapped["BusinessInsight"] = relationship("BusinessInsight", back_populates="comments")
    author: Mapped["User"] = relationship("User", lazy="joined")


class InsightGenerationRun(Base):
    __tablename__ = "insight_generation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual, scheduled, on_refresh, on_pipeline
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)  # running, completed, failed
    insights_generated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InsightGenerationSchedule(Base):
    __tablename__ = "insight_generation_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), nullable=False)  # daily, weekly, monthly, on_refresh, on_pipeline
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
