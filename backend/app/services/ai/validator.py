from typing import Any

from app.core.exceptions import DataLensException
from app.services.ai.schemas import AnalyticalPlan


class PlanValidator:
    """
    Validates structured analytical plans against physical Parquet dataset schemas.
    Guarantees that LLMs cannot reference non-existent columns, incompatible types,
    or invalid aggregations.
    """

    NUMERIC_TYPES = {"integer", "float", "number", "numeric", "double", "int64", "float64", "decimal"}
    DATE_TYPES = {"date", "datetime", "timestamp"}

    @classmethod
    def validate_plan(
        cls,
        plan: AnalyticalPlan,
        columns_meta: list[dict[str, Any]],
    ) -> AnalyticalPlan:
        return cls.validate_and_normalize_plan(plan, columns_meta)

    @classmethod
    def validate_and_normalize_plan(
        cls,
        plan: AnalyticalPlan,
        columns_meta: list[dict[str, Any]],
    ) -> AnalyticalPlan:
        # Build schema lookup maps (case-insensitive for robust mapping)
        cols_by_exact = {c["name"]: c for c in columns_meta}
        cols_by_lower = {c["name"].lower(): c for c in columns_meta}

        def resolve_column(name: str | None) -> str | None:
            if not name or name == "*":
                return name
            if name in cols_by_exact:
                return name
            if name.lower() in cols_by_lower:
                return cols_by_lower[name.lower()]["name"]
            available = ", ".join(cols_by_exact.keys())
            raise DataLensException(
                f"Requested column '{name}' does not exist in dataset. Available columns: {available}",
                code="INVALID_PLAN_COLUMN",
            )

        # 1. Resolve & normalize metric column
        if plan.metric_column:
            plan.metric_column = resolve_column(plan.metric_column)
            if plan.metric_column and plan.metric_column != "*":
                col_meta = cols_by_exact[plan.metric_column]
                col_type = col_meta.get("inferred_type", "string").lower()
                if plan.aggregation in ("sum", "avg", "median") and col_type not in cls.NUMERIC_TYPES:
                    raise DataLensException(
                        f"Aggregation '{plan.aggregation}' cannot be applied to non-numeric column '{plan.metric_column}' (type: {col_type}).",
                        code="INCOMPATIBLE_AGGREGATION",
                    )

        # 2. Resolve & normalize group-by columns
        normalized_group_by: list[str] = []
        for g_col in plan.group_by_columns:
            norm_col = resolve_column(g_col)
            if norm_col:
                normalized_group_by.append(norm_col)
        plan.group_by_columns = normalized_group_by

        # If intent is group_by or ranking, ensure at least one grouping column
        if plan.intent in ("group_by", "ranking") and not plan.group_by_columns:
            # Fallback to first categorical or string column
            cat_cols = [c["name"] for c in columns_meta if c.get("inferred_type") in ("string", "category")]
            plan.group_by_columns = [cat_cols[0]] if cat_cols else [columns_meta[0]["name"]]

        # 3. Resolve & normalize date column for time_series
        if plan.intent == "time_series":
            if plan.date_column:
                plan.date_column = resolve_column(plan.date_column)
            else:
                date_cols = [c["name"] for c in columns_meta if c.get("inferred_type") in cls.DATE_TYPES or "date" in c["name"].lower()]
                if date_cols:
                    plan.date_column = date_cols[0]
                else:
                    raise DataLensException(
                        "Time series analysis requires a valid date or timestamp column.",
                        code="MISSING_DATE_COLUMN",
                    )

        # 4. Resolve & normalize filter columns
        for f in plan.filters:
            f.column = resolve_column(f.column) or f.column

        # 5. Cap limit safely
        plan.limit = max(1, min(plan.limit, 100))

        return plan
