import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AnalyticalIntent = Literal[
    "performance",
    "ranking",
    "comparison",
    "trend",
    "contribution",
    "diagnostic",
    "multi_dataset_join",
    "group_by",
    "time_series",
    "dataset_summary",
    "filtered_aggregation",
]


class FilterItem(BaseModel):
    column: str
    operator: str = "eq"  # eq, neq, gt, gte, lt, lte, contains, between, is_null, is_not_null
    value: Any = None
    second_value: Any | None = None


class NLAQueryPlan(BaseModel):
    intent: AnalyticalIntent = "performance"
    metric_name: str | None = None
    metric_column: str | None = None
    aggregation: str = "SUM"  # SUM, AVG, COUNT, COUNT_DISTINCT, MIN, MAX, CALCULATED
    group_by_columns: list[str] = Field(default_factory=list)
    filters: list[FilterItem] = Field(default_factory=list)
    date_column: str | None = None
    time_granularity: str = "monthly"  # daily, weekly, monthly, quarterly, yearly
    comparison_period: str | None = None  # mom, yoy, qoq
    sort_direction: str = "desc"
    limit: int = 20
    target_dataset_id: uuid.UUID | None = None
    secondary_dataset_id: uuid.UUID | None = None
    join_source_column: str | None = None
    join_target_column: str | None = None
    join_cardinality: str | None = None
    needs_clarification: bool = False
    clarification_options: list[str] = Field(default_factory=list)
    clarification_message: str | None = None
    clarification_prompt: str | None = None


class NLAQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    dataset_id: uuid.UUID
    session_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    filters: list[FilterItem] | None = None


class NLAClarifyRequest(BaseModel):
    session_id: uuid.UUID
    chosen_option: str = Field(..., min_length=1)
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None


class NLAFollowUpRequest(BaseModel):
    session_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)
    dataset_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None


class NLAMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    sender: str
    content: str
    direct_answer: str | None = None
    intent: str | None = None
    plan_json: dict[str, Any] | None = None
    results_summary: dict[str, Any] | None = None
    metric_cards: list[dict[str, Any]] = Field(default_factory=list)
    chart_data: dict[str, Any] | None = None
    table_data: dict[str, Any] | None = None
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)
    suggested_follow_ups: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_options: list[str] = Field(default_factory=list)
    provider_used: str = "deterministic"
    execution_duration_ms: int = 0
    created_at: datetime


class NLASessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    dataset_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    active_context: dict[str, Any] = Field(default_factory=dict)
    messages: list[NLAMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SavedAnalysisCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    question: str
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID | None = None
    plan_json: dict[str, Any]
    results_summary: dict[str, Any]
    chart_config: dict[str, Any]
    tags: list[str] = Field(default_factory=list)


class SavedAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    question: str
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID | None = None
    plan_json: dict[str, Any]
    results_summary: dict[str, Any]
    chart_config: dict[str, Any]
    tags: list[str]
    created_at: datetime
    updated_at: datetime
