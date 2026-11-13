import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.analytics.schemas import FilterCondition

# ---------------------------------------------------------------------------
# Widget Schemas
# ---------------------------------------------------------------------------

class DashboardWidgetCreate(BaseModel):
    widget_type: str = Field(
        ...,
        description=(
            "kpi, bar, stacked_bar, grouped_bar, horizontal_bar, percent_bar, top_n, "
            "line, multi_line, area, stacked_area, combo, heatmap, histogram, box_plot, "
            "correlation, treemap, waterfall, funnel, gauge, pareto, pie, donut, scatter, table, text"
        ),
    )
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    dataset_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    grid_x: int = Field(default=0, ge=0)
    grid_y: int = Field(default=0, ge=0)
    grid_w: int = Field(default=6, ge=1, le=12)
    grid_h: int = Field(default=4, ge=1, le=24)
    query_config: dict[str, Any] = Field(default_factory=dict)
    display_settings: dict[str, Any] = Field(default_factory=dict)


class DashboardWidgetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    dataset_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    grid_x: int | None = Field(default=None, ge=0)
    grid_y: int | None = Field(default=None, ge=0)
    grid_w: int | None = Field(default=None, ge=1, le=12)
    grid_h: int | None = Field(default=None, ge=1, le=24)
    query_config: dict[str, Any] | None = None
    display_settings: dict[str, Any] | None = None


class DashboardWidgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dashboard_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    widget_type: str
    title: str
    description: str | None = None
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int
    query_config: dict[str, Any] = Field(default_factory=dict)
    display_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Filter Schemas
# ---------------------------------------------------------------------------

class DashboardFilterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    column_name: str = Field(..., min_length=1, max_length=100)
    filter_type: str = Field(default="dropdown", description="date_range, dropdown, multi_select, numeric_range, text")
    default_operator: str = Field(default="eq")
    default_value: Any | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class DashboardFilterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    column_name: str | None = Field(default=None, min_length=1, max_length=100)
    filter_type: str | None = None
    default_operator: str | None = None
    default_value: Any | None = None
    config: dict[str, Any] | None = None


class DashboardFilterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dashboard_id: uuid.UUID
    name: str
    column_name: str
    filter_type: str
    default_operator: str
    default_value: Any | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Layout Schemas
# ---------------------------------------------------------------------------

class DashboardLayoutItem(BaseModel):
    id: uuid.UUID
    grid_x: int = Field(ge=0)
    grid_y: int = Field(ge=0)
    grid_w: int = Field(ge=1, le=12)
    grid_h: int = Field(ge=1, le=24)


class DashboardLayoutUpdate(BaseModel):
    widgets: list[DashboardLayoutItem]


# ---------------------------------------------------------------------------
# Dashboard Schemas
# ---------------------------------------------------------------------------

class DashboardCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    visibility: str = Field(default="workspace")
    layout_config: dict[str, Any] = Field(default_factory=dict)


class DashboardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    visibility: str | None = None
    is_archived: bool | None = None
    layout_config: dict[str, Any] | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID | None = None
    title: str
    description: str | None = None
    visibility: str
    is_archived: bool
    layout_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    widget_count: int = 0
    filter_count: int = 0


class DashboardDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID | None = None
    title: str
    description: str | None = None
    visibility: str
    is_archived: bool
    layout_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    widgets: list[DashboardWidgetResponse] = Field(default_factory=list)
    filters: list[DashboardFilterResponse] = Field(default_factory=list)


class DashboardListResponse(BaseModel):
    items: list[DashboardResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Query & Analytics Execution Schemas
# ---------------------------------------------------------------------------

class WidgetQueryRequest(BaseModel):
    filters: list[FilterCondition] | None = None
    drill_level: int | None = None
    drill_filters: list[FilterCondition] | None = None
    compare_to: str | None = None
    target_value: float | None = None


class WidgetQueryResponse(BaseModel):
    widget_id: uuid.UUID
    widget_type: str
    data: Any
    row_count: int
    execution_time_ms: int
    dataset_version_id: uuid.UUID | None = None
    dataset_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardExportRequest(BaseModel):
    format: str = Field(default="pdf", description="pdf, csv, xlsx")
    filters: list[FilterCondition] | None = None
