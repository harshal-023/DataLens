import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class PromptTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Prompt template representing a managed prompt in the Prompt Library.
    """
    __tablename__ = "prompt_templates"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="Business Intelligence", nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="PromptVersion.version_number.desc()",
    )
    experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment",
        back_populates="prompt_template",
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate id={self.id} name='{self.name}' category='{self.category}'>"


class PromptVersion(Base, UUIDPrimaryKeyMixin):
    """
    Immutable version of a prompt template.
    Once created, system_prompt, user_prompt_template, and variables cannot be mutated.
    """
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("prompt_id", "version_number", name="uq_prompt_versions_prompt_id_version_number"),
    )

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    model_config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    change_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
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

    # Relationships
    template: Mapped["PromptTemplate"] = relationship("PromptTemplate", back_populates="versions")
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    runs: Mapped[list["ExperimentRun"]] = relationship("ExperimentRun", back_populates="prompt_version")

    def __repr__(self) -> str:
        return f"<PromptVersion id={self.id} prompt_id={self.prompt_id} v={self.version_number}>"


class Experiment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Controlled prompt experiment evaluating one or more prompt versions across test cases.
    """
    __tablename__ = "experiments"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    version_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    model_config_override: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    prompt_template: Mapped["PromptTemplate | None"] = relationship("PromptTemplate", back_populates="experiments")
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="TestCase.created_at.asc()",
    )
    runs: Mapped[list["ExperimentRun"]] = relationship(
        "ExperimentRun",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} name='{self.name}' status='{self.status}'>"


class TestCase(Base, UUIDPrimaryKeyMixin):
    """
    Test case representing an input configuration and expected ground truth.
    """
    __tablename__ = "test_cases"
    __test__ = False

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    variables: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="test_cases")
    runs: Mapped[list["ExperimentRun"]] = relationship(
        "ExperimentRun",
        back_populates="test_case",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TestCase id={self.id} name='{self.name}'>"


class ExperimentRun(Base, UUIDPrimaryKeyMixin):
    """
    Individual execution of a single prompt version against a single test case.
    """
    __tablename__ = "experiment_runs"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rendered_system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rendered_user_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="gpt-4o-mini", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False, index=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="runs")
    prompt_version: Mapped["PromptVersion"] = relationship("PromptVersion", back_populates="runs")
    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="runs")
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ExperimentRun id={self.id} version={self.prompt_version_id} status={self.status}>"


class EvaluationResult(Base, UUIDPrimaryKeyMixin):
    """
    Evaluation score for a specific metric on an experiment run.
    """
    __tablename__ = "evaluation_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evaluation_method: Mapped[str] = mapped_column(String(50), default="deterministic", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_by_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    run: Mapped["ExperimentRun"] = relationship("ExperimentRun", back_populates="evaluation_results")

    def __repr__(self) -> str:
        return f"<EvaluationResult id={self.id} metric='{self.metric_name}' score={self.score}/{self.max_score}>"
