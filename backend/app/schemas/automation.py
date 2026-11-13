"""Pydantic schemas for Phase 5D: Automated Data Refresh, Pipeline Orchestration & Background Job Management."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobType(StrEnum):
    DATA_IMPORT = "data_import"
    DATASET_REFRESH = "dataset_refresh"
    INCREMENTAL_REFRESH = "incremental_refresh"
    PIPELINE_EXECUTION = "pipeline_execution"
    DATA_VALIDATION = "data_validation"
    DATASET_MATERIALIZATION = "dataset_materialization"
    DASHBOARD_REFRESH = "dashboard_refresh"
    REPORT_GENERATION = "report_generation"
    REPORT_DELIVERY = "report_delivery"
    WORKFLOW = "workflow"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowFailurePolicy(StrEnum):
    STOP_IMMEDIATELY = "STOP_IMMEDIATELY"
    RETRY_FAILED_STEP = "RETRY_FAILED_STEP"
    CONTINUE_INDEPENDENT_BRANCHES = "CONTINUE_INDEPENDENT_BRANCHES"
    REQUIRE_MANUAL_INTERVENTION = "REQUIRE_MANUAL_INTERVENTION"


class WorkflowStepType(StrEnum):
    SOURCE_REFRESH = "SOURCE_REFRESH"
    DATA_VALIDATION = "DATA_VALIDATION"
    TRANSFORMATION = "TRANSFORMATION"
    REPORT_GENERATION = "REPORT_GENERATION"


class ValidationAction(StrEnum):
    BLOCK = "BLOCK"
    WARN = "WARN"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ErrorClassification(StrEnum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    AUTHENTICATION = "AUTHENTICATION"
    VALIDATION = "VALIDATION"
    TIMEOUT = "TIMEOUT"


# ---------------------------------------------------------------------------
# Background Job Schemas
# ---------------------------------------------------------------------------


class BackgroundJobCreate(BaseModel):
    job_type: str = Field(..., description="Job type, e.g. data_import, dataset_refresh, pipeline_execution")
    priority: int = Field(0, description="Priority level (higher executed first)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Execution parameters without sensitive credentials")
    idempotency_key: str | None = Field(None, description="Optional idempotency key to prevent duplicate creation")
    scheduled_at: datetime | None = Field(None, description="Deferred execution time in UTC")
    max_retries: int = Field(3, ge=0, le=10)
    retry_delay_seconds: int = Field(30, ge=1, le=3600)
    timeout_seconds: int = Field(600, ge=30, le=86400)


class JobExecutionLogEntry(BaseModel):
    timestamp: str
    level: str = "INFO"
    message: str


class JobExecutionResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    attempt_number: int
    status: str
    worker_id: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int = 0
    error_classification: str | None = None
    error_details: str | None = None
    logs: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class BackgroundJobResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    job_type: str
    status: str
    priority: int
    payload: dict[str, Any]
    idempotency_key: str | None = None
    scheduled_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress_pct: int = 0
    progress_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_seconds: int = 30
    error_classification: str | None = None
    error_details: str | None = None
    worker_id: str | None = None
    heartbeat_at: datetime | None = None
    timeout_seconds: int = 600
    source_dataset_version_ids: list[str] = Field(default_factory=list)
    output_dataset_version_ids: list[str] = Field(default_factory=list)
    created_by: uuid.UUID | None = None
    schedule_id: uuid.UUID | None = None
    workflow_execution_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    executions: list[JobExecutionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BackgroundJobListResponse(BaseModel):
    jobs: list[BackgroundJobResponse]
    total: int


# ---------------------------------------------------------------------------
# Job Schedule Schemas
# ---------------------------------------------------------------------------


class JobScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    job_type: str = Field(..., description="Target job type: data_import, dataset_refresh, pipeline_execution, workflow, report_generation")
    target_resource_id: uuid.UUID | None = None
    target_resource_type: str = Field("connection", description="connection, pipeline, report, workflow")
    payload: dict[str, Any] = Field(default_factory=dict)
    frequency: str = Field("daily", description="one_time, hourly, daily, weekly, monthly, cron")
    cron_expression: str | None = None
    timezone: str = Field("UTC", description="IANA timezone name, e.g. America/New_York, Asia/Kolkata, UTC")
    hour: int = Field(0, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    day_of_week: int | None = Field(None, ge=0, le=6, description="0=Monday .. 6=Sunday")
    day_of_month: int | None = Field(None, ge=1, le=31)


class JobScheduleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    payload: dict[str, Any] | None = None
    frequency: str | None = None
    cron_expression: str | None = None
    timezone: str | None = None
    hour: int | None = Field(None, ge=0, le=23)
    minute: int | None = Field(None, ge=0, le=59)
    day_of_week: int | None = Field(None, ge=0, le=6)
    day_of_month: int | None = Field(None, ge=1, le=31)
    is_active: bool | None = None


class JobScheduleResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    job_type: str
    target_resource_id: uuid.UUID | None = None
    target_resource_type: str
    payload: dict[str, Any]
    frequency: str
    cron_expression: str | None = None
    timezone: str
    hour: int
    minute: int
    day_of_week: int | None = None
    day_of_month: int | None = None
    is_active: bool
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    next_run_at: datetime | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobScheduleListResponse(BaseModel):
    schedules: list[JobScheduleResponse]
    total: int


# ---------------------------------------------------------------------------
# Workflow Schemas (DAG Orchestrator)
# ---------------------------------------------------------------------------


class WorkflowStepCreate(BaseModel):
    step_name: str = Field(..., min_length=1, max_length=255)
    step_order: int = Field(0, ge=0)
    step_type: str = Field(..., description="SOURCE_REFRESH, DATA_VALIDATION, TRANSFORMATION, REPORT_GENERATION")
    target_resource_id: uuid.UUID | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    depends_on_step_ids: list[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    timeout_seconds: int = Field(600, ge=30, le=86400)
    max_retries: int = Field(2, ge=0, le=5)


class WorkflowStepResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    step_name: str
    step_order: int
    step_type: str
    target_resource_id: uuid.UUID | None = None
    configuration: dict[str, Any]
    depends_on_step_ids: list[str]
    timeout_seconds: int
    max_retries: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    failure_policy: str = Field("STOP_IMMEDIATELY", description="STOP_IMMEDIATELY, RETRY_FAILED_STEP, CONTINUE_INDEPENDENT_BRANCHES, REQUIRE_MANUAL_INTERVENTION")
    steps: list[WorkflowStepCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    failure_policy: str | None = None
    steps: list[WorkflowStepCreate] | None = None


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    is_active: bool
    failure_policy: str
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowResponse]
    total: int


class WorkflowValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    topological_order: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow Execution Schemas
# ---------------------------------------------------------------------------


class WorkflowStepExecutionResponse(BaseModel):
    id: uuid.UUID
    workflow_execution_id: uuid.UUID
    step_id: uuid.UUID
    status: str
    job_id: uuid.UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    error_details: str | None = None
    input_version_ids: list[str] = Field(default_factory=list)
    output_version_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    step_name: str | None = None
    step_type: str | None = None

    model_config = {"from_attributes": True}


class WorkflowExecutionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    triggered_by: uuid.UUID | None = None
    trigger_type: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    error_details: str | None = None
    created_at: datetime
    updated_at: datetime
    step_executions: list[WorkflowStepExecutionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WorkflowExecutionListResponse(BaseModel):
    executions: list[WorkflowExecutionResponse]
    total: int


# ---------------------------------------------------------------------------
# Data Quality Validation Schemas
# ---------------------------------------------------------------------------


class DataQualityRuleConfig(BaseModel):
    required_columns: list[str] = Field(default_factory=list)
    expected_column_types: dict[str, str] = Field(default_factory=dict)  # col -> expected type
    max_null_pct: float = Field(20.0, ge=0.0, le=100.0)
    max_duplicate_pct: float = Field(10.0, ge=0.0, le=100.0)
    min_row_count: int = Field(1, ge=0)
    max_row_count: int | None = Field(None, ge=1)
    on_failure: str = Field("BLOCK", description="BLOCK, WARN, REQUIRE_APPROVAL")


class DataQualityValidationResult(BaseModel):
    passed: bool
    action: str  # BLOCK, WARN, REQUIRE_APPROVAL
    issues: list[str] = Field(default_factory=list)
    row_count: int
    column_count: int
    null_percentages: dict[str, float] = Field(default_factory=dict)
    duplicate_rows_detected: int = 0


# ---------------------------------------------------------------------------
# Automation Overview Schemas
# ---------------------------------------------------------------------------


class AutomationOverviewResponse(BaseModel):
    active_schedules_count: int = 0
    running_jobs_count: int = 0
    queued_jobs_count: int = 0
    failed_jobs_count: int = 0
    successful_jobs_count: int = 0
    active_workflows_count: int = 0
    recent_jobs: list[BackgroundJobResponse] = Field(default_factory=list)
    recent_workflows: list[WorkflowExecutionResponse] = Field(default_factory=list)
