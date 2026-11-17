import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AutoDashboardStage(StrEnum):
    QUEUED = "queued"
    READING_STRUCTURE = "reading_structure"
    UNDERSTANDING_COLUMNS = "understanding_columns"
    IDENTIFYING_METRICS = "identifying_metrics"
    DISCOVERING_RELATIONSHIPS = "discovering_relationships"
    SELECTING_VISUALIZATIONS = "selecting_visualizations"
    CALCULATING_RESULTS = "calculating_results"
    DESIGNING_LAYOUT = "designing_layout"
    PREPARING_INSIGHTS = "preparing_insights"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutoDashboardRequest(BaseModel):
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID | None = None
    business_domain: str | None = Field(
        default="automatic",
        description="automatic, sales, finance, marketing, customer, operations, inventory, hr, logistics, custom",
    )
    user_objective: str | None = Field(
        default=None,
        description="Optional business questions or focus description from the user",
    )
    visual_style: str | None = Field(
        default="ocean",
        description="ocean, business_blue, sunset, forest, royal, vibrant, monochrome",
    )


class AutoDashboardStatusResponse(BaseModel):
    generation_id: uuid.UUID
    status: str  # queued, running, completed, failed, cancelled
    stage: str
    progress_pct: int
    message: str
    dataset_id: uuid.UUID
    dataset_name: str
    preview_ready: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class GeneratedKPIItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    metric_column: str | None = None
    aggregation: str = "sum"  # sum, avg, count, distinct_count, min, max
    formatted_value: str
    numeric_value: float
    change_pct: float | None = None
    change_direction: str | None = None  # up, down, flat
    target_value: float | None = None
    grid_x: int = 0
    grid_y: int = 0
    grid_w: int = 3
    grid_h: int = 3
    display_settings: dict[str, Any] = Field(default_factory=dict)


class GeneratedChartItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    widget_type: str  # bar, horizontal_bar, line, area, pie, donut, stacked_bar, table, heatmap
    title: str
    description: str | None = None
    grid_x: int = 0
    grid_y: int = 3
    grid_w: int = 6
    grid_h: int = 4
    query_config: dict[str, Any] = Field(default_factory=dict)
    display_settings: dict[str, Any] = Field(default_factory=dict)
    calculated_data: Any | None = None


class GeneratedFilterItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    column_name: str
    filter_type: str = "dropdown"  # date_range, dropdown, multi_select, numeric_range
    default_operator: str = "eq"
    default_value: Any | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class GeneratedInsightItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    observation: str
    evidence: str
    category: str = "observation"  # trend, distribution, leader, risk, opportunity
    recommendation: str | None = None


class AutoDashboardPreviewResponse(BaseModel):
    generation_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    dataset_version_id: uuid.UUID
    title: str
    description: str
    business_domain: str
    theme: str
    kpis: list[GeneratedKPIItem]
    charts: list[GeneratedChartItem]
    filters: list[GeneratedFilterItem]
    insights: list[GeneratedInsightItem]
    total_widgets: int
    created_at: datetime


class AutoDashboardSaveRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    theme: str | None = None
    kpis: list[GeneratedKPIItem] | None = None
    charts: list[GeneratedChartItem] | None = None
    filters: list[GeneratedFilterItem] | None = None
