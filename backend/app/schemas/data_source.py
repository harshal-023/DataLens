"""Pydantic schemas for external data source connections, imports, and refreshes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(..., description="postgres, mysql, rest_api, google_sheets, mongodb, s3")
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ConnectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    source_type: str
    config: dict[str, Any]
    status: str
    last_tested_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConnectionTestRequest(BaseModel):
    source_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)


class ConnectionTestResponse(BaseModel):
    status: str
    latency_ms: float
    message: str
    server_version: str | None = None


class DiscoveryResponse(BaseModel):
    database: str | None = None
    bucket: str | None = None
    schemas: dict[str, Any] = Field(default_factory=dict)
    available_databases: list[str] | None = None
    total_tables: int = 0


class ColumnMetadataItem(BaseModel):
    name: str
    type: str
    nullable: bool = True
    is_primary_key: bool = False
    default: str | None = None


class TableSchemaResponse(BaseModel):
    resource: str
    columns: list[ColumnMetadataItem]


class PreviewRequest(BaseModel):
    resource_path: str
    limit: int = Field(50, ge=1, le=500)


class PreviewResponse(BaseModel):
    resource: str
    columns: list[ColumnMetadataItem]
    rows: list[dict[str, Any]]
    total_rows: int


class ImportRequest(BaseModel):
    resource_path: str
    import_mode: str = Field("full", description="full or incremental")
    target_dataset_name: str | None = None
    target_dataset_id: uuid.UUID | None = None
    watermark_column: str | None = None


class ImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    source_resource: str
    import_mode: str
    watermark_column: str | None = None
    watermark_value: str | None = None
    status: str
    rows_imported: int
    bytes_imported: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class RefreshConfigCreate(BaseModel):
    frequency: str = Field("daily", description="hourly, daily, weekly, custom_cron")
    refresh_mode: str = Field("full", description="full or incremental")
    target_resource: str
    dataset_id: uuid.UUID | None = None
    watermark_column: str | None = None
    cron_expression: str | None = None
    timezone: str = "UTC"
    is_active: bool = True


class RefreshConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    frequency: str
    cron_expression: str | None = None
    refresh_mode: str
    target_resource: str
    watermark_column: str | None = None
    timezone: str
    is_active: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class GoogleAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None
