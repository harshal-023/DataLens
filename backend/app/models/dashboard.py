import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.user import User
    from app.models.workspace import Workspace


class Dashboard(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dashboards"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(50), default="workspace", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    layout_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="dashboards")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    widgets: Mapped[list["DashboardWidget"]] = relationship(
        "DashboardWidget",
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="DashboardWidget.grid_y, DashboardWidget.grid_x",
    )
    filters: Mapped[list["DashboardFilter"]] = relationship(
        "DashboardFilter",
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="DashboardFilter.created_at",
    )


class DashboardWidget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dashboard_widgets"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)  # kpi, bar, line, area, pie, donut, scatter, table, text
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 12-column Grid placement
    grid_x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grid_y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grid_w: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    grid_h: Mapped[int] = mapped_column(Integer, default=4, nullable=False)

    # Dynamic Query and Display Configurations
    query_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    display_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="widgets")
    dataset: Mapped[Optional["Dataset"]] = relationship("Dataset")
    dataset_version: Mapped[Optional["DatasetVersion"]] = relationship("DatasetVersion")


class DashboardFilter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dashboard_filters"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    filter_type: Mapped[str] = mapped_column(String(50), nullable=False)  # date_range, dropdown, multi_select, numeric_range, text
    default_operator: Mapped[str] = mapped_column(String(20), default="eq", nullable=False)
    default_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="filters")

