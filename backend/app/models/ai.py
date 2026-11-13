"""SQLAlchemy model for AI Privacy Policies and Provider Configuration."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class AIPrivacyPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workspace-level policy governing AI provider routing and data protection rules."""

    __tablename__ = "ai_privacy_policies"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    routing_mode: Mapped[str] = mapped_column(
        String(50), default="HYBRID", nullable=False
    )  # GEMINI_ONLY, LOCAL_ONLY, HYBRID, DETERMINISTIC_ONLY
    cloud_ai_permitted: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    local_only_enforced: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    allow_sample_values: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # If False, zero raw data values sent to external cloud AI
    min_sensitivity_for_local_only: Mapped[str] = mapped_column(
        String(50), default="CONFIDENTIAL", nullable=False
    )  # INTERNAL, CONFIDENTIAL, RESTRICTED
    default_local_model: Mapped[str] = mapped_column(
        String(100), default="gemma3:4b", nullable=False
    )
    default_cloud_model: Mapped[str] = mapped_column(
        String(100), default="gemini-3.5-flash", nullable=False
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
