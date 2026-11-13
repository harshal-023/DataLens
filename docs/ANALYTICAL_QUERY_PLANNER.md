# Analytical Query Planner (`NLAQueryPlanner`)

## Core Purpose
The `NLAQueryPlanner` translates unconstrained natural-language prompts into structured, strongly-typed analytical specifications represented by `NLAQueryPlan`. The planner never generates raw SQL directly; it emits an intermediate plan that is validated against enterprise governance policies before compilation.

## Plan Schema (`NLAQueryPlan`)
```python
class NLAQueryPlan(BaseModel):
    intent: AnalyticalIntent = "performance"
    metric_name: str | None = None
    metric_column: str | None = None
    aggregation: str = "SUM"
    group_by_columns: list[str] = Field(default_factory=list)
    filters: list[FilterItem] = Field(default_factory=list)
    date_column: str | None = None
    time_granularity: str = "monthly"
    comparison_period: str | None = None
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
```

## Disambiguation Heuristic
When questions are broad (e.g. "Show me performance" or "How did we do?"), the planner stops query execution and sets `needs_clarification = True`, returning specific options (e.g., "Total Revenue", "Order Volume", "Average Order Value"). Users pick a targeted pill to proceed with determinism.

## Semantic Layer Integration
The planner performs multi-stage matching:
1. **Metric Registry**: Exact match or token overlap against approved `MetricDefinition` records.
2. **Column Semantics**: Matches measures and dimensions from `ColumnSemanticMapping`.
3. **Conversational Memory**: Inherits active metrics and filters from previous turns in the session.

