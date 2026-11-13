import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnSemanticResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_version_id: uuid.UUID
    dataset_id: uuid.UUID
    column_name: str
    business_name: str
    description: str | None = None
    semantic_type: str
    logical_type: str
    physical_type: str
    aggregation_method: str
    format_string: str | None = None
    is_dimension: bool
    is_measure: bool
    is_primary_key: bool
    is_foreign_key: bool
    mapping_status: str
    confidence_score: float
    confirmed_by_user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ColumnSemanticUpdateRequest(BaseModel):
    business_name: str | None = None
    description: str | None = None
    semantic_type: str | None = None
    aggregation_method: str | None = None
    format_string: str | None = None
    is_dimension: bool | None = None
    is_measure: bool | None = None
    mapping_status: str | None = "USER_CONFIRMED"


class DatasetProfileDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_version_id: uuid.UUID
    dataset_id: uuid.UUID
    row_count: int
    column_count: int
    duplicate_rows: int
    quality_score: int
    profile_metadata: dict[str, Any]
    warnings: list[dict[str, Any]]
    created_at: datetime


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    source_dataset_id: uuid.UUID
    source_version_id: uuid.UUID | None = None
    source_column: str
    target_dataset_id: uuid.UUID
    target_version_id: uuid.UUID | None = None
    target_column: str
    relationship_type: str
    confidence_score: float
    status: str
    evidence: dict[str, Any]
    join_warning: str | None = None
    confirmed_by_user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class RelationshipCreateRequest(BaseModel):
    source_dataset_id: uuid.UUID
    source_column: str
    target_dataset_id: uuid.UUID
    target_column: str
    relationship_type: str = "MANY_TO_ONE"
    status: str = "CONFIRMED"


class RelationshipUpdateRequest(BaseModel):
    status: str  # CONFIRMED, REJECTED, SUGGESTED
    relationship_type: str | None = None


class BusinessContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_version_id: uuid.UUID
    dataset_id: uuid.UUID
    business_domain: str
    purpose: str
    important_entities: list[str]
    key_dimensions: list[str]
    important_measures: list[str]
    suggested_kpis: list[dict[str, Any]]
    data_quality_limitations: list[str]
    business_assumptions: list[str]
    is_user_confirmed: bool
    confirmed_by_user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class BusinessContextUpdateRequest(BaseModel):
    business_domain: str | None = None
    purpose: str | None = None
    important_entities: list[str] | None = None
    key_dimensions: list[str] | None = None
    important_measures: list[str] | None = None
    suggested_kpis: list[dict[str, Any]] | None = None
    is_user_confirmed: bool = True


class MetricVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    metric_id: uuid.UUID
    version_number: int
    formula: str
    source_columns: list[str]
    aggregation: str
    formatting: str
    change_summary: str | None = None
    created_by_user_id: uuid.UUID | None = None
    created_at: datetime


class MetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    formula: str
    source_columns: list[str]
    aggregation: str
    filters: list[dict[str, Any]]
    formatting: str
    applicable_dimensions: list[str]
    validation_status: str
    validation_error: str | None = None
    version: int
    approval_status: str
    owner_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class MetricCreateRequest(BaseModel):
    dataset_id: uuid.UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    formula: str = Field(..., min_length=1, max_length=1000)
    aggregation: str = "SUM"
    formatting: str = "CURRENCY"
    source_columns: list[str] = Field(default_factory=list)


class MetricUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    formula: str | None = None
    aggregation: str | None = None
    formatting: str | None = None
    approval_status: str | None = None
    change_summary: str | None = None


class MetricValidateRequest(BaseModel):
    formula: str
    available_columns: list[str] | None = None


class MetricValidateResponse(BaseModel):
    is_valid: bool
    referenced_columns: list[str]
    errors: list[str]
    compiled_sql: str | None = None


class MetricCalculateRequest(BaseModel):
    dataset_id: uuid.UUID
    formula: str
    aggregation: str = "SUM"


class MetricCalculateResponse(BaseModel):
    metric_value: float | None
    is_null: bool
    formula: str
    compiled_sql: str


class DatasetIntelligenceBundleResponse(BaseModel):
    dataset_id: uuid.UUID
    version_id: uuid.UUID
    version_number: str
    profile: DatasetProfileDetailResponse | None
    columns: list[ColumnSemanticResponse]
    relationships: list[RelationshipResponse]
    business_context: BusinessContextResponse | None
    metrics: list[MetricResponse]

