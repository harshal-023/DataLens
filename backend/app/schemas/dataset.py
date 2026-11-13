import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatasetColumnSchema(BaseModel):
    name: str
    inferred_type: str
    null_count: int = 0
    sample_values: list[str] = Field(default_factory=list)


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    original_filename: str
    file_type: str
    row_count: int
    column_count: int
    status: str
    is_archived: bool = False
    current_version_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    version_number: str
    file_size: int
    row_count: int
    column_count: int
    checksum: str
    status: str
    error_message: str | None = None
    schema_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DatasetDetailResponse(DatasetResponse):
    current_version: DatasetVersionResponse | None = None
    versions: list[DatasetVersionResponse] = Field(default_factory=list)
    schema_metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetStatusResponse(BaseModel):
    dataset_id: uuid.UUID
    status: str
    processing_stage: str
    rows_processed: int
    total_rows: int
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None


class PaginatedDatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedRowsResponse(BaseModel):
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    columns: list[dict[str, Any]] = Field(default_factory=list)

