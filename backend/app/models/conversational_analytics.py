import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.user import User
    from app.models.workspace import Workspace


class NLASession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Conversational analytics session maintaining analytical memory, active dataset,
    and cumulative filters across follow-up queries.
    """
    __tablename__ = "nla_sessions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # stores active_metric_name, active_dimensions, active_filters, time_granularity, last_intent

    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")
    dataset: Mapped["Dataset"] = relationship("Dataset")
    dataset_version: Mapped["DatasetVersion"] = relationship("DatasetVersion")
    messages: Mapped[list["NLAMessage"]] = relationship(
        "NLAMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="NLAMessage.created_at.asc()",
    )


class NLAMessage(Base, UUIDPrimaryKeyMixin):
    """
    Individual turn within a conversational analytics session, recording query,
    validated plan, DuckDB execution evidence, and grounded explanation.
    """
    __tablename__ = "nla_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nla_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    direct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plan_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    results_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metric_cards: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    chart_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    table_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evidence_items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    needs_clarification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clarification_options: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), default="deterministic", nullable=False)
    execution_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    session: Mapped["NLASession"] = relationship("NLASession", back_populates="messages")

    @property
    def suggested_follow_ups(self) -> list[str]:
        if self.plan_json and isinstance(self.plan_json, dict):
            return self.plan_json.get("suggested_follow_ups", [])
        return []


class SavedAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Saved analytical inquiry and verified findings for future review and dashboard pin.
    """
    __tablename__ = "saved_analyses"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    results_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    chart_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")
    dataset: Mapped["Dataset"] = relationship("Dataset")
    dataset_version: Mapped["DatasetVersion"] = relationship("DatasetVersion")

