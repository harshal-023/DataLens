import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Legacy Phase 1/2 Report Schemas (Preserved for backwards compatibility)
# ---------------------------------------------------------------------------

class ReportCreateRequest(BaseModel):
    dataset_id: uuid.UUID
    title: str = "Business Intelligence Report"
    format: str = "pdf"  # pdf, docx, xlsx, csv
    version_id: uuid.UUID | None = None
    report_config: dict[str, Any] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    title: str
    format: str
    status: str
    file_size: int
    report_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PaginatedReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Phase 4D Business Reporting Schemas
# ---------------------------------------------------------------------------

class ReportTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str
    is_system: bool = False
    template_config: dict[str, Any] = Field(default_factory=dict)
    default_sections: list[dict[str, Any]] = Field(default_factory=list)


class BusinessReportCreate(BaseModel):
    title: str
    description: str | None = None
    report_type: str = "custom"
    template_id: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    source_dashboard_ids: list[str] = Field(default_factory=list)
    source_dataset_refs: list[dict[str, Any]] = Field(default_factory=list)
    source_model_run_refs: list[dict[str, Any]] = Field(default_factory=list)


class BusinessReportUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    report_type: str | None = None
    status: str | None = None
    configuration: dict[str, Any] | None = None
    source_dashboard_ids: list[str] | None = None
    source_dataset_refs: list[dict[str, Any]] | None = None
    source_model_run_refs: list[dict[str, Any]] | None = None


class ReportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    workspace_id: uuid.UUID
    triggered_by: uuid.UUID | None = None
    trigger_type: str
    execution_status: str
    report_period: str | None = None
    applied_filters: list[dict[str, Any]] = Field(default_factory=list)
    source_provenance: Any = Field(default_factory=dict)
    generated_files: dict[str, Any] = Field(default_factory=dict)
    execution_duration_ms: int
    error_details: str | None = None
    ai_generated: bool
    created_at: datetime


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    workspace_id: uuid.UUID
    frequency: str
    day_of_week: int | None = None
    day_of_month: int | None = None
    hour: int
    minute: int
    timezone: str
    next_execution_time: datetime | None = None
    last_execution_time: datetime | None = None
    last_execution_status: str | None = None
    is_enabled: bool
    delivery_configuration: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class BusinessReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    template_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    report_type: str
    status: str
    configuration: dict[str, Any] = Field(default_factory=dict)
    source_dashboard_ids: list[str] = Field(default_factory=list)
    source_dataset_refs: list[dict[str, Any]] = Field(default_factory=list)
    source_model_run_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    runs: list[ReportRunResponse] = Field(default_factory=list)
    schedules: list[ReportScheduleResponse] = Field(default_factory=list)


class PaginatedBusinessReportListResponse(BaseModel):
    items: list[BusinessReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportRunTriggerRequest(BaseModel):
    period: str | None = None
    formats: list[str] = Field(default_factory=lambda: ["pdf", "docx", "xlsx", "csv"])
    applied_filters: list[dict[str, Any]] = Field(default_factory=list)


class ReportScheduleCreate(BaseModel):
    frequency: str = "weekly"  # daily, weekly, monthly
    hour: int = 8
    minute: int = 0
    day_of_week: int | None = None  # 0=Monday..6=Sunday
    day_of_month: int | None = None  # 1..31
    timezone: str = "UTC"
    delivery_configuration: dict[str, Any] = Field(default_factory=dict)


class ReportScheduleUpdate(BaseModel):
    frequency: str | None = None
    hour: int | None = None
    minute: int | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    timezone: str | None = None
    is_enabled: bool | None = None
    delivery_configuration: dict[str, Any] | None = None


class ReportPreviewRequest(BaseModel):
    configuration: dict[str, Any]
    source_dataset_refs: list[dict[str, Any]] = Field(default_factory=list)
    period: str | None = None
    applied_filters: list[dict[str, Any]] = Field(default_factory=list)
