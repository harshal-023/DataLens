# DataLens — Analytical Plan Schema Specification

## 1. Overview

The `AnalyticalPlan` schema is the structured contract between the AI natural language parser and the deterministic DuckDB analytics engine. It models analytical intent without executing arbitrary code.

---

## 2. Pydantic Schema Model

```python
class PlanFilterCondition(BaseModel):
    column: str
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "contains", "in"]
    value: Any

class AnalyticalPlan(BaseModel):
    intent: Literal[
        "group_by",
        "time_series",
        "ranking",
        "descriptive_statistics",
        "data_quality",
    ] = "group_by"
    
    metric_column: str | None = None
    aggregation: Literal["sum", "avg", "min", "max", "count", "median"] = "sum"
    group_by_columns: list[str] = Field(default_factory=list)
    filters: list[PlanFilterCondition] = Field(default_factory=list)
    
    # Time Series Specific
    date_column: str | None = None
    time_granularity: Literal["daily", "monthly", "quarterly", "yearly"] = "monthly"
    
    # Ordering & Limits
    sort_direction: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=10, ge=1, le=1000)
    
    # Clarification Flags
    needs_clarification: bool = False
    clarification_message: str | None = None
```

---

## 3. Supported Intents

| Intent | Purpose | Required Engine Call |
| :--- | :--- | :--- |
| `group_by` | Aggregate metric grouped by categorical column | `AnalyticsEngine.compute_aggregation()` |
| `ranking` | Top/Bottom N ranking by metric | `AnalyticsEngine.compute_aggregation()` |
| `time_series` | Trend analysis over date/time dimension | `AnalyticsEngine.compute_time_series()` |
| `descriptive_statistics` | Mean, median, IQR, stddev, percentiles | `AnalyticsEngine.compute_descriptive_stats()` |
| `data_quality` | Missing values, outliers, duplicate detection | `AnalyticsEngine.compute_data_quality()` |

---

## 4. Schema Validation Defense-in-Depth

The `PlanValidator` enforces five validation rules before any plan reaches DuckDB:

1. **Metric Column Verification:** Ensures `metric_column` exists in the dataset schema.
2. **Numeric Type Enforcement:** Ensures `sum`, `avg`, and `median` aggregations are applied ONLY to numeric columns (`integer`, `float`, `number`, `numeric`, `double`, `int64`, `decimal`).
3. **Categorical Dimension Verification:** Ensures every column in `group_by_columns` exists in the dataset.
4. **Date Dimension Verification:** Ensures `date_column` is present for `time_series` plans, or infers the first date column.
5. **Filter Operator Whitelist:** Ensures only permitted operators (`eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains`, `in`) are accepted, preventing SQL injection.

