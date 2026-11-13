import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Step Schemas
# ---------------------------------------------------------------------------

class TransformationStepCreate(BaseModel):
    step_order: int = Field(default=0, ge=0)
    operation_type: str = Field(..., description="join, append, clean_nulls, clean_duplicates, type_cast, string_op, formula, filter, select_columns")
    configuration: dict[str, Any] = Field(default_factory=dict)
    input_references: dict[str, Any] = Field(default_factory=dict)
    output_schema: list[dict[str, Any]] = Field(default_factory=list)


class TransformationStepUpdate(BaseModel):
    step_order: int | None = Field(default=None, ge=0)
    operation_type: str | None = None
    configuration: dict[str, Any] | None = None
    input_references: dict[str, Any] | None = None
    output_schema: list[dict[str, Any]] | None = None


class TransformationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pipeline_id: uuid.UUID
    step_order: int
    operation_type: str
    configuration: dict[str, Any]
    input_references: dict[str, Any]
    output_schema: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Pipeline Schemas
# ---------------------------------------------------------------------------

class TransformationPipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_dataset_ids: list[str] = Field(default_factory=list)
    status: str = Field(default="draft", description="draft, active, archived")


class TransformationPipelineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    source_dataset_ids: list[str] | None = None
    status: str | None = None


class TransformationPipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID | None = None
    name: str
    description: str | None = None
    source_dataset_ids: list[str]
    status: str
    steps: list[TransformationStepResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TransformationPipelineSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID | None = None
    name: str
    description: str | None = None
    source_dataset_ids: list[str]
    status: str
    step_count: int = 0
    last_run_status: str | None = None
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Run Schemas
# ---------------------------------------------------------------------------

class TransformationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pipeline_id: uuid.UUID
    workspace_id: uuid.UUID
    triggered_by: uuid.UUID | None = None
    source_dataset_versions: dict[str, Any]
    output_dataset_id: uuid.UUID | None = None
    output_dataset_version_id: uuid.UUID | None = None
    status: str
    error_details: str | None = None
    execution_duration_ms: int
    row_count: int
    created_at: datetime
    updated_at: datetime


class RunPipelineRequest(BaseModel):
    output_dataset_name: str | None = None
    output_dataset_description: str | None = None


# ---------------------------------------------------------------------------
# Preview & Validation Schemas
# ---------------------------------------------------------------------------

class PreviewRequest(BaseModel):
    step_id: uuid.UUID | None = None
    step_index: int | None = None
    limit: int = Field(default=20, ge=1, le=100)


class PreviewColumn(BaseModel):
    name: str
    data_type: str


class PreviewResponse(BaseModel):
    columns: list[PreviewColumn]
    rows: list[dict[str, Any]]
    total_rows_sampled: int
    step_executed: int
    execution_duration_ms: int


class ValidateFormulaRequest(BaseModel):
    expression: str
    columns: list[dict[str, Any]] = Field(default_factory=list, description="Available column definitions {name, type}")


class ValidateFormulaResponse(BaseModel):
    valid: bool
    ast_summary: str | None = None
    referenced_columns: list[str] = Field(default_factory=list)
    sql_expression: str | None = None
    error: str | None = None


class ReorderStepsRequest(BaseModel):
    step_ids: list[uuid.UUID]
