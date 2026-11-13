import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InsightCategory = Literal["performance", "trend", "anomaly", "risk", "opportunity"]
InsightSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
InsightStatus = Literal["NEW", "REVIEWED", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "DISMISSED"]


class EvidenceDataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_type: str
    metric_name: str
    baseline_value: str | None = None
    observed_value: str
    deviation_pct: float | None = None
    supporting_data: dict[str, Any] | None = None
    calculation_formula: str | None = None
    verified: bool = True
    created_at: datetime


class InsightCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    insight_id: uuid.UUID
    user_id: uuid.UUID
    author_name: str | None = None
    content: str
    created_at: datetime
    updated_at: datetime


class InsightAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    insight_id: uuid.UUID
    assigned_by_user_id: uuid.UUID
    assigned_to_user_id: uuid.UUID
    assignment_note: str | None = None
    created_at: datetime


class BusinessInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    title: str
    category: InsightCategory
    severity: InsightSeverity
    status: InsightStatus
    summary: str
    detailed_explanation: str
    affected_metric: str
    affected_dimension: str | None = None
    affected_segment: str | None = None
    score: float
    priority_reason: str | None = None
    recommended_action: str | None = None
    suggested_investigation: str | None = None
    assigned_to_user_id: uuid.UUID | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by_user_id: uuid.UUID | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: uuid.UUID | None = None
    ai_provider: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime
    evidence_items: list[EvidenceDataSchema] = Field(default_factory=list)
    comments: list[InsightCommentResponse] = Field(default_factory=list)


class ExecutiveOverviewResponse(BaseModel):
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    total_insights_count: int
    critical_risks_count: int
    high_opportunities_count: int
    anomalies_count: int
    top_movements: list[dict[str, Any]] = Field(default_factory=list)
    critical_findings: list[BusinessInsightResponse] = Field(default_factory=list)
    positive_opportunities: list[BusinessInsightResponse] = Field(default_factory=list)
    recent_changes: list[dict[str, Any]] = Field(default_factory=list)


class InsightGenerateRequest(BaseModel):
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None
    categories: list[InsightCategory] | None = None
    min_severity: InsightSeverity | None = None
    ai_provider: str | None = None


class InsightStatusUpdateRequest(BaseModel):
    status: InsightStatus
    notes: str | None = None


class InsightCommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class InsightAssignRequest(BaseModel):
    assigned_to_user_id: uuid.UUID
    note: str | None = None


class ScheduleCreateRequest(BaseModel):
    dataset_id: uuid.UUID | None = None
    name: str = Field(..., min_length=2, max_length=255)
    frequency: Literal["daily", "weekly", "monthly", "on_refresh", "on_pipeline"] = "daily"
    cron_expression: str | None = None
    timezone: str = "UTC"
    config: dict[str, Any] | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    name: str
    frequency: str
    cron_expression: str | None = None
    timezone: str
    is_active: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    config: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

