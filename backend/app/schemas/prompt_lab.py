import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Variable regex: detects {{variable_name}}
VARIABLE_PATTERN = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

PROMPT_CATEGORIES = [
    "Business Intelligence",
    "Data Analysis",
    "Summarization",
    "Classification",
    "Information Extraction",
    "Content Generation",
    "Custom",
]


class VariableDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=200)
    required: bool = True
    default: str | None = None

    @field_validator("name")
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^[a-zA-Z0-9_]+$", clean):
            raise ValueError("Variable name must contain only alphanumeric characters and underscores.")
        return clean


class ModelConfigSnapshot(BaseModel):
    provider: str = Field(default="mock", max_length=50)
    model: str = Field(default="gpt-4o-mini", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=8000)


# =========================================================================
# PROMPT TEMPLATE SCHEMAS
# =========================================================================

class PromptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category: str = Field(default="Business Intelligence", max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=20)
    system_prompt: str = Field(default="", max_length=10000)
    user_prompt_template: str = Field(min_length=1, max_length=20000)
    variables: list[VariableDefinition] = Field(default_factory=list)
    model_config_snapshot: ModelConfigSnapshot = Field(default_factory=ModelConfigSnapshot)
    change_description: str | None = Field(default="Initial version", max_length=500)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in PROMPT_CATEGORIES:
            return "Custom"
        return v


class PromptUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in PROMPT_CATEGORIES:
            return "Custom"
        return v


class PromptVersionCreateRequest(BaseModel):
    system_prompt: str = Field(default="", max_length=10000)
    user_prompt_template: str = Field(min_length=1, max_length=20000)
    variables: list[VariableDefinition] = Field(default_factory=list)
    model_config_snapshot: ModelConfigSnapshot = Field(default_factory=ModelConfigSnapshot)
    change_description: str = Field(min_length=1, max_length=500)


class PromptVersionResponse(BaseModel):
    id: uuid.UUID
    prompt_id: uuid.UUID
    version_number: int
    system_prompt: str
    user_prompt_template: str
    variables: list[dict[str, Any]]
    model_config_snapshot: dict[str, Any]
    change_description: str | None
    created_by: uuid.UUID | None
    created_at: datetime


class PromptDetailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    category: str
    tags: list[str]
    created_by: uuid.UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    current_version: PromptVersionResponse | None = None
    versions_count: int = 0


class PromptListItemResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    category: str
    tags: list[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    versions_count: int = 0
    latest_version_number: int = 1


class PromptVersionComparisonResponse(BaseModel):
    prompt_id: uuid.UUID
    version_a: PromptVersionResponse
    version_b: PromptVersionResponse
    system_prompt_diff: bool
    user_prompt_diff: bool
    variables_diff: bool
    model_config_diff: bool


# =========================================================================
# PLAYGROUND & EXECUTION SCHEMAS
# =========================================================================

class PromptExecuteRequest(BaseModel):
    system_prompt: str = Field(default="", max_length=10000)
    user_prompt_template: str = Field(min_length=1, max_length=20000)
    variables: dict[str, Any] = Field(default_factory=dict)
    provider: str = Field(default="mock", max_length=50)
    model: str = Field(default="gpt-4o-mini", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=8000)
    prompt_version_id: uuid.UUID | None = None


class PromptExecuteResponse(BaseModel):
    rendered_system_prompt: str
    rendered_user_prompt: str
    response_text: str
    provider: str
    model: str
    prompt_version: str | None = None
    execution_timestamp: datetime
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    provider_status: str  # live, simulated, disabled
    is_simulated: bool


# =========================================================================
# EXPERIMENT SCHEMAS
# =========================================================================

class TestCaseCreate(BaseModel):
    __test__ = False
    name: str = Field(min_length=1, max_length=150)
    variables: dict[str, Any] = Field(default_factory=dict)
    expected_output: str | None = None
    expected_keywords: list[str] = Field(default_factory=list)


class TestCaseResponse(BaseModel):
    __test__ = False
    id: uuid.UUID
    experiment_id: uuid.UUID
    name: str
    variables: dict[str, Any]
    expected_output: str | None
    expected_keywords: list[str]
    created_at: datetime


class ExperimentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    prompt_id: uuid.UUID | None = None
    version_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    test_cases: list[TestCaseCreate] = Field(min_length=1, max_length=20)
    model_config_override: dict[str, Any] = Field(default_factory=dict)


class ExperimentRunResponse(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    prompt_version_id: uuid.UUID
    test_case_id: uuid.UUID
    rendered_system_prompt: str
    rendered_user_prompt: str
    response_text: str | None
    provider: str
    model: str
    status: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    estimated_cost_usd: float | None
    error_message: str | None
    created_at: datetime
    evaluations: list[dict[str, Any]] = Field(default_factory=list)


class ExperimentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    prompt_id: uuid.UUID | None
    name: str
    description: str | None
    version_ids: list[str]
    model_config_override: dict[str, Any]
    status: str
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    test_cases: list[TestCaseResponse] = Field(default_factory=list)
    runs_count: int = 0
    completed_runs_count: int = 0


# =========================================================================
# EVALUATION SCHEMAS
# =========================================================================

class EvaluationCriterionConfig(BaseModel):
    metric_name: Literal[
        "exact_match",
        "keyword_presence",
        "json_schema_valid",
        "response_length",
        "relevance",
        "instruction_following",
        "factual_consistency",
        "completeness",
        "clarity",
    ]
    max_score: float = Field(default=1.0, gt=0.0)
    weight: float = Field(default=1.0, ge=0.0)
    parameters: dict[str, Any] = Field(default_factory=dict)


class EvaluateExperimentRequest(BaseModel):
    criteria: list[EvaluationCriterionConfig] = Field(min_length=1, max_length=10)


class EvaluationItemResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    metric_name: str
    score: float
    max_score: float
    evaluation_method: str
    explanation: str | None
    evaluated_by_model: str | None
    created_at: datetime


# =========================================================================
# COMPARISON & ANALYTICS SCHEMAS
# =========================================================================

class VersionMetricSummary(BaseModel):
    version_id: str
    version_number: int
    runs_count: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_latency_ms: float
    avg_input_tokens: float | None
    avg_output_tokens: float | None
    total_cost_usd: float | None
    avg_overall_score: float
    metric_scores: dict[str, float]  # metric_name -> avg score


class ExperimentComparisonResponse(BaseModel):
    experiment_id: uuid.UUID
    experiment_name: str
    total_test_cases: int
    versions_compared: list[VersionMetricSummary]
    best_version_id: str | None
    best_version_rationale: str | None
    observations: list[str]
