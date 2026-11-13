import re
from pathlib import Path
from typing import Any

from app.core.exceptions import DataLensException
from app.services.intelligence.metric_engine import MetricIntelligenceEngine
from app.services.nla.schemas import FilterItem, NLAQueryPlan


class NLASafeQueryCompiler:
    """
    Deterministic query compiler that transforms structured NLA plans into safe,
    parameterized DuckDB SQL without allowing arbitrary code execution or identifier injection.
    """

    ALLOWED_OPERATORS = {
        "eq": "=",
        "neq": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "contains": "ILIKE",
        "not_contains": "NOT ILIKE",
        "is_null": "IS NULL",
        "is_not_null": "IS NOT NULL",
        "between": "BETWEEN",
    }

    @classmethod
    def sanitize_identifier(cls, name: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", name):
            raise DataLensException(f"Invalid column identifier: '{name}'.", code="INVALID_COLUMN")
        return f'"{name}"'

    @classmethod
    def _get_parquet_source_sql(cls, parquet_files: list[Path], alias: str = "") -> str:
        if not parquet_files:
            raise DataLensException("Dataset has no Parquet data files on disk.", code="NOT_FOUND")
        clean_paths = [str(p.resolve()).replace("\\", "/") for p in parquet_files if p.is_file()]
        if not clean_paths:
            raise DataLensException("Parquet data files not found on disk.", code="FILE_NOT_FOUND")
        escaped_paths = ", ".join(f"'{p}'" for p in clean_paths)
        sql = f"read_parquet([{escaped_paths}])"
        return f"{sql} AS {alias}" if alias else sql

    @classmethod
    def build_where_clause(
        cls,
        filters: list[FilterItem] | None,
        table_alias: str = "",
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []
        prefix = f"{table_alias}." if table_alias else ""

        for cond in filters:
            col_sql = f"{prefix}{cls.sanitize_identifier(cond.column)}"
            op = cond.operator.lower()
            if op not in cls.ALLOWED_OPERATORS:
                raise DataLensException(f"Unsupported filter operator '{op}'.", code="INVALID_FILTER")

            if op == "is_null":
                clauses.append(f"{col_sql} IS NULL")
            elif op == "is_not_null":
                clauses.append(f"{col_sql} IS NOT NULL")
            elif op == "between":
                clauses.append(f"{col_sql} BETWEEN ? AND ?")
                params.append(cond.value)
                params.append(cond.second_value)
            elif op in ("contains", "not_contains"):
                pattern = f"%{cond.value}%"
                sql_op = cls.ALLOWED_OPERATORS[op]
                clauses.append(f"CAST({col_sql} AS VARCHAR) {sql_op} ?")
                params.append(pattern)
            else:
                sql_op = cls.ALLOWED_OPERATORS[op]
                clauses.append(f"{col_sql} {sql_op} ?")
                params.append(cond.value)

        where_str = " WHERE " + " AND ".join(clauses) if clauses else ""
        return where_str, params

    @classmethod
    def compile_to_duckdb_sql(
        cls,
        plan: NLAQueryPlan,
        primary_parquet_files: list[Path],
        secondary_parquet_files: list[Path] | None = None,
        metric_formula: str | None = None,
    ) -> tuple[str, list[Any]]:
        return cls.compile_plan_to_sql(
            plan=plan,
            primary_parquet_files=primary_parquet_files,
            secondary_parquet_files=secondary_parquet_files,
            metric_formula=metric_formula,
        )

    @classmethod
    def compile_plan_to_sql(
        cls,
        plan: NLAQueryPlan,
        primary_parquet_files: list[Path],
        secondary_parquet_files: list[Path] | None = None,
        metric_formula: str | None = None,
    ) -> tuple[str, list[Any]]:
        """
        Compiles structured plan into safe, parameterized DuckDB SQL.
        Returns: (sql_query, query_parameters)
        """
        has_join = bool(
            plan.secondary_dataset_id
            and secondary_parquet_files
            and plan.join_source_column
            and plan.join_target_column
        )

        p_alias = "s" if has_join else ""
        p_prefix = "s." if has_join else ""
        t_prefix = "t." if has_join else ""

        # Inspect schema of primary Parquet to correctly route table aliases (s vs t)
        primary_cols: set[str] = set()
        if primary_parquet_files and primary_parquet_files[0].is_file():
            try:
                import pyarrow.parquet as pq_engine
                primary_cols = set(pq_engine.read_schema(primary_parquet_files[0]).names)
            except Exception:
                pass

        # 1. FROM clause
        from_clause = cls._get_parquet_source_sql(primary_parquet_files, alias=p_alias)
        if has_join and secondary_parquet_files:
            t_source = cls._get_parquet_source_sql(secondary_parquet_files, alias="t")
            s_join_col = f"s.{cls.sanitize_identifier(plan.join_source_column)}" if plan.join_source_column else "s.id"
            t_join_col = f"t.{cls.sanitize_identifier(plan.join_target_column)}" if plan.join_target_column else "t.id"
            from_clause = f"{from_clause} LEFT JOIN {t_source} ON {s_join_col} = {t_join_col}"

        # 2. WHERE clause
        where_clause, params = cls.build_where_clause(plan.filters, table_alias=p_alias)

        # 3. SELECT Metric Expression
        if metric_formula:
            # Safe formula compilation with division-by-zero protection
            metric_expr = MetricIntelligenceEngine.compile_formula_to_sql(metric_formula)
        elif plan.metric_column:
            clean_mcol = cls.sanitize_identifier(plan.metric_column)
            m_prefix = p_prefix if (not has_join or not primary_cols or plan.metric_column in primary_cols) else t_prefix
            agg = plan.aggregation.upper()
            if agg == "COUNT_DISTINCT":
                metric_expr = f"COUNT(DISTINCT {m_prefix}{clean_mcol})"
            elif agg in ("SUM", "AVG", "MIN", "MAX", "COUNT"):
                metric_expr = f"{agg}({m_prefix}{clean_mcol})"
            else:
                metric_expr = f"SUM({m_prefix}{clean_mcol})"
        else:
            metric_expr = "COUNT(*)"

        # 4. Handle Specific Intents
        limit_val = max(1, min(plan.limit, 1000))
        sort_dir = "ASC" if plan.sort_direction.lower() == "asc" else "DESC"

        # Time Series Intent
        if plan.intent == "time_series" and plan.date_column:
            clean_date = cls.sanitize_identifier(plan.date_column)
            granularity = plan.time_granularity.lower()
            date_bucket_map = {
                "daily": "day",
                "weekly": "week",
                "monthly": "month",
                "quarterly": "quarter",
                "yearly": "year",
            }
            bucket = date_bucket_map.get(granularity, "month")
            time_expr = f"date_trunc('{bucket}', CAST({p_prefix}{clean_date} AS DATE))"

            sql = f"""
                SELECT
                    CAST({time_expr} AS VARCHAR) AS period,
                    {metric_expr} AS metric_value,
                    COUNT(*) AS count
                FROM {from_clause}
                {where_clause}
                GROUP BY 1
                ORDER BY 1 ASC
                LIMIT {limit_val}
            """
            return sql.strip(), params

        # Group By / Ranking / Contribution / Diagnostic Intent
        if plan.group_by_columns:
            group_selects: list[str] = []
            group_clauses: list[str] = []
            for col in plan.group_by_columns:
                # Check if group col belongs to target table in join
                col_prefix = t_prefix if (has_join and primary_cols and col not in primary_cols) else p_prefix
                clean_col = f"{col_prefix}{cls.sanitize_identifier(col)}"
                group_selects.append(f"CAST({clean_col} AS VARCHAR) AS {cls.sanitize_identifier(col)}")
                group_clauses.append(clean_col)

            select_str = ", ".join(group_selects)
            group_str = ", ".join(group_clauses)

            if plan.intent == "contribution":
                # Window function for percentage share of total
                sql = f"""
                    WITH agg AS (
                        SELECT
                            {select_str},
                            {metric_expr} AS metric_value,
                            COUNT(*) AS record_count
                        FROM {from_clause}
                        {where_clause}
                        GROUP BY {group_str}
                    )
                    SELECT
                        *,
                        ROUND(metric_value / NULLIF(SUM(metric_value) OVER (), 0) * 100, 2) AS share_of_total
                    FROM agg
                    ORDER BY metric_value {sort_dir}
                    LIMIT {limit_val}
                """
            else:
                sql = f"""
                    SELECT
                        {select_str},
                        {metric_expr} AS metric_value,
                        COUNT(*) AS record_count
                    FROM {from_clause}
                    {where_clause}
                    GROUP BY {group_str}
                    ORDER BY metric_value {sort_dir}
                    LIMIT {limit_val}
                """
            return sql.strip(), params

        # Scalar Performance / Summary Intent (No Group By)
        sql = f"""
            SELECT
                {metric_expr} AS metric_value,
                COUNT(*) AS record_count
            FROM {from_clause}
            {where_clause}
        """
        return sql.strip(), params
