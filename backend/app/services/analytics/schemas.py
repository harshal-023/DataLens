import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FilterCondition(BaseModel):
    column: str
    operator: str  # eq, neq, gt, gte, lt, lte, contains, not_contains, starts_with, ends_with, is_null, is_not_null, between
    value: Any = None
    second_value: Any = None


class AggregationRequest(BaseModel):
    group_by_columns: list[str]
    metric_column: str | None = None
    aggregation: str = "count"  # sum, avg, min, max, count, distinct_count
    sort_order: str = "desc"  # asc, desc
    limit: int | None = 50
    filters: list[FilterCondition] | None = None
    version_id: uuid.UUID | None = None


class AggregationItem(BaseModel):
    key: str
    value: float
    count: int
    share_of_total: float | None = None
    formatted_value: str | None = None


class AggregationResponse(BaseModel):
    group_by_columns: list[str]
    metric_column: str
    aggregation: str
    items: list[AggregationItem]
    total: float
    row_count_analyzed: int
    version_id: str


class DescriptiveStatsRequest(BaseModel):
    columns: list[str] | None = None
    filters: list[FilterCondition] | None = None
    version_id: uuid.UUID | None = None


class ColumnDescriptiveStats(BaseModel):
    column: str
    count: int
    missing_count: int
    unique_count: int
    sum: float | None = None
    mean: float | None = None
    median: float | None = None
    min: float | None = None
    max: float | None = None
    range: float | None = None
    variance: float | None = None
    standard_deviation: float | None = None
    q1: float | None = None
    q3: float | None = None
    iqr: float | None = None


class DescriptiveStatsResponse(BaseModel):
    columns: dict[str, ColumnDescriptiveStats]
    row_count_analyzed: int
    version_id: str


class TimeSeriesRequest(BaseModel):
    date_column: str
    value_column: str
    interval: str = "monthly"  # daily, weekly, monthly, quarterly, yearly
    aggregation: str = "sum"  # sum, avg, count, min, max
    filters: list[FilterCondition] | None = None
    version_id: uuid.UUID | None = None


class TimeSeriesPoint(BaseModel):
    period: str
    timestamp: int
    value: float
    growth_rate_pct: float | None = None
    count: int = 0


class TimeSeriesResponse(BaseModel):
    date_column: str
    value_column: str
    interval: str
    aggregation: str
    points: list[TimeSeriesPoint]
    trend_summary: str
    total: float
    row_count_analyzed: int
    version_id: str


class QualityIssue(BaseModel):
    id: str
    column: str | None = None
    type: str  # missing_values, duplicate_rows, suspicious_negative, outlier
    title: str
    description: str
    affected_count: int
    severity: str  # high, medium, low, info
    suggested_action: str


class QualityReportResponse(BaseModel):
    quality_score: int
    issues: list[QualityIssue]
    row_count_analyzed: int
    version_id: str


class ComparisonRequest(BaseModel):
    baseline_version_id: uuid.UUID
    compare_version_id: uuid.UUID
    metric_columns: list[str] | None = None


class ComparisonMetricDiff(BaseModel):
    column: str
    metric: str
    baseline_value: float
    compare_value: float
    diff: float
    pct_change: float


class ComparisonResponse(BaseModel):
    baseline_version: str
    compare_version: str
    row_count_diff: int
    row_count_pct_change: float
    added_columns: list[str]
    removed_columns: list[str]
    metric_diffs: list[ComparisonMetricDiff]
    quality_score_diff: int


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    total_count: int
    null_count: int
    null_pct: float
    unique_count: int
    sample_values: list[str] = Field(default_factory=list)
    min: Any = None
    max: Any = None
    mean: float | None = None
    median: float | None = None
    top_categories: list[dict[str, Any]] = Field(default_factory=list)


class DatasetProfileResponse(BaseModel):
    dataset_id: uuid.UUID
    version_id: str
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: list[ColumnProfile]
    quality_score: int


class AnalysisRunCreateRequest(BaseModel):
    analysis_type: str  # profile, summary, aggregate, time_series, quality, compare
    parameters: dict[str, Any] = Field(default_factory=dict)
    version_id: uuid.UUID | None = None


class AnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    analysis_type: str
    parameters: dict[str, Any]
    result_summary: dict[str, Any]
    status: str
    execution_time_ms: int
    created_at: datetime

