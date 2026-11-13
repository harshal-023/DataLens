import re
from pathlib import Path
from typing import Any

import duckdb

from app.core.exceptions import DataLensException
from app.services.analytics.schemas import (
    AggregationItem,
    AggregationResponse,
    ColumnDescriptiveStats,
    ColumnProfile,
    ComparisonMetricDiff,
    ComparisonResponse,
    DatasetProfileResponse,
    DescriptiveStatsResponse,
    FilterCondition,
    QualityIssue,
    QualityReportResponse,
    TimeSeriesPoint,
    TimeSeriesResponse,
)


class AnalyticsEngine:
    """
    High-performance, deterministic analytics engine executing against partitioned Parquet datasets
    using DuckDB in-memory analytical execution.
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
        "starts_with": "ILIKE",
        "ends_with": "ILIKE",
        "is_null": "IS NULL",
        "is_not_null": "IS NOT NULL",
        "between": "BETWEEN",
    }

    @classmethod
    def _sanitize_identifier(cls, name: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", name):
            raise DataLensException(f"Invalid column identifier: '{name}'.", code="INVALID_COLUMN")
        return f'"{name}"'

    @classmethod
    def _build_where_clause(
        cls, filters: list[FilterCondition] | None, params: list[Any]
    ) -> str:
        if not filters:
            return ""

        clauses: list[str] = []
        for cond in filters:
            col_sql = cls._sanitize_identifier(cond.column)
            op = cond.operator.lower()
            if op not in cls.ALLOWED_OPERATORS:
                raise DataLensException(f"Unsupported filter operator: '{op}'.", code="INVALID_FILTER")

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
            elif op == "starts_with":
                pattern = f"{cond.value}%"
                clauses.append(f"CAST({col_sql} AS VARCHAR) ILIKE ?")
                params.append(pattern)
            elif op == "ends_with":
                pattern = f"%{cond.value}"
                clauses.append(f"CAST({col_sql} AS VARCHAR) ILIKE ?")
                params.append(pattern)
            else:
                sql_op = cls.ALLOWED_OPERATORS[op]
                clauses.append(f"{col_sql} {sql_op} ?")
                params.append(cond.value)

        return " WHERE " + " AND ".join(clauses) if clauses else ""

    @classmethod
    def _get_parquet_source_sql(cls, parquet_files: list[Path]) -> str:
        if not parquet_files:
            raise DataLensException("Dataset has no Parquet data parts.", code="NOT_FOUND")
        clean_paths = [str(p.resolve()).replace("\\", "/") for p in parquet_files if p.is_file()]
        if not clean_paths:
            raise DataLensException("Dataset Parquet files do not exist on disk.", code="STORAGE_NOT_FOUND")
        paths_str = ", ".join(f"'{p}'" for p in clean_paths)
        return f"read_parquet([{paths_str}])"

    @classmethod
    def compute_profiling(
        cls,
        parquet_files: list[Path],
        columns_meta: list[dict[str, Any]],
        dataset_id: Any,
        version_id: str,
    ) -> DatasetProfileResponse:
        conn = duckdb.connect(":memory:")
        src = cls._get_parquet_source_sql(parquet_files)

        # Get total row count
        total_rows = conn.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
        if total_rows == 0:
            return DatasetProfileResponse(
                dataset_id=dataset_id,
                version_id=version_id,
                row_count=0,
                column_count=len(columns_meta),
                duplicate_rows=0,
                columns=[],
                quality_score=100,
            )

        # Duplicate row count
        distinct_rows = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {src})").fetchone()[0]
        duplicate_rows = max(0, total_rows - distinct_rows)

        col_profiles: list[ColumnProfile] = []
        for col in columns_meta:
            name = col["name"]
            inferred_type = col.get("inferred_type", "string")
            col_ident = cls._sanitize_identifier(name)

            # Query count, null count, unique count
            stats_query = f"""
                SELECT
                    COUNT({col_ident}),
                    COUNT(*) - COUNT({col_ident}),
                    COUNT(DISTINCT {col_ident})
                FROM {src}
            """
            valid_count, null_count, unique_count = conn.execute(stats_query).fetchone()
            null_pct = round((null_count / total_rows) * 100, 2)

            min_val = None
            max_val = None
            mean_val = None
            median_val = None

            if inferred_type in ("integer", "float", "number") and valid_count > 0:
                num_stats_q = f"""
                    SELECT
                        MIN({col_ident}),
                        MAX({col_ident}),
                        AVG({col_ident}),
                        MEDIAN({col_ident})
                    FROM {src}
                    WHERE {col_ident} IS NOT NULL
                """
                n_min, n_max, n_avg, n_med = conn.execute(num_stats_q).fetchone()
                min_val = round(float(n_min), 2) if n_min is not None else None
                max_val = round(float(n_max), 2) if n_max is not None else None
                mean_val = round(float(n_avg), 2) if n_avg is not None else None
                median_val = round(float(n_med), 2) if n_med is not None else None
            elif inferred_type == "date" and valid_count > 0:
                date_q = f"SELECT MIN({col_ident}), MAX({col_ident}) FROM {src} WHERE {col_ident} IS NOT NULL"
                d_min, d_max = conn.execute(date_q).fetchone()
                min_val = str(d_min) if d_min is not None else None
                max_val = str(d_max) if d_max is not None else None

            # Top categories for low-cardinality or categorical columns
            top_cats: list[dict[str, Any]] = []
            if unique_count <= 20 and valid_count > 0:
                cat_q = f"""
                    SELECT CAST({col_ident} AS VARCHAR), COUNT(*)
                    FROM {src}
                    WHERE {col_ident} IS NOT NULL
                    GROUP BY 1
                    ORDER BY 2 DESC
                    LIMIT 5
                """
                top_cats = [{"category": str(r[0]), "count": int(r[1])} for r in conn.execute(cat_q).fetchall()]

            sample_vals = [str(v) for v in col.get("sample_values", [])[:5]]

            col_profiles.append(
                ColumnProfile(
                    name=name,
                    inferred_type=inferred_type,
                    total_count=total_rows,
                    null_count=null_count,
                    null_pct=null_pct,
                    unique_count=unique_count,
                    sample_values=sample_vals,
                    min=min_val,
                    max=max_val,
                    mean=mean_val,
                    median=median_val,
                    top_categories=top_cats,
                )
            )

        # Compute quality score
        quality_res = cls.compute_data_quality(parquet_files, columns_meta, version_id)

        return DatasetProfileResponse(
            dataset_id=dataset_id,
            version_id=version_id,
            row_count=total_rows,
            column_count=len(columns_meta),
            duplicate_rows=duplicate_rows,
            columns=col_profiles,
            quality_score=quality_res.quality_score,
        )

    @classmethod
    def compute_descriptive_stats(
        cls,
        parquet_files: list[Path],
        columns_meta: list[dict[str, Any]],
        target_columns: list[str] | None,
        filters: list[FilterCondition] | None,
        version_id: str,
    ) -> DescriptiveStatsResponse:
        conn = duckdb.connect(":memory:")
        src = cls._get_parquet_source_sql(parquet_files)
        params: list[Any] = []
        where_clause = cls._build_where_clause(filters, params)

        filtered_count_q = f"SELECT COUNT(*) FROM {src}{where_clause}"
        row_count_analyzed = conn.execute(filtered_count_q, params).fetchone()[0]

        cols_to_compute = (
            [c for c in columns_meta if c["name"] in target_columns]
            if target_columns
            else columns_meta
        )

        result_cols: dict[str, ColumnDescriptiveStats] = {}

        for col in cols_to_compute:
            name = col["name"]
            inferred_type = col.get("inferred_type", "string")
            col_ident = cls._sanitize_identifier(name)

            col_params = list(params)
            base_q = f"""
                SELECT
                    COUNT({col_ident}),
                    COUNT(*) - COUNT({col_ident}),
                    COUNT(DISTINCT {col_ident})
                FROM {src}{where_clause}
            """
            v_count, null_count, unique_count = conn.execute(base_q, col_params).fetchone()

            stats = ColumnDescriptiveStats(
                column=name,
                count=row_count_analyzed,
                missing_count=null_count,
                unique_count=unique_count,
            )

            if inferred_type in ("integer", "float", "number") and v_count > 0:
                num_q = f"""
                    SELECT
                        SUM({col_ident}),
                        AVG({col_ident}),
                        MEDIAN({col_ident}),
                        MIN({col_ident}),
                        MAX({col_ident}),
                        MAX({col_ident}) - MIN({col_ident}),
                        COALESCE(VAR_SAMP({col_ident}), 0),
                        COALESCE(STDDEV_SAMP({col_ident}), 0),
                        QUANTILE_CONT({col_ident}, 0.25),
                        QUANTILE_CONT({col_ident}, 0.75)
                    FROM {src}{where_clause} {"AND" if where_clause else "WHERE"} {col_ident} IS NOT NULL
                """
                row = conn.execute(num_q, params).fetchone()
                if row and row[0] is not None:
                    c_sum, c_avg, c_med, c_min, c_max, c_rng, c_var, c_std, c_q1, c_q3 = row
                    stats.sum = round(float(c_sum), 2)
                    stats.mean = round(float(c_avg), 2)
                    stats.median = round(float(c_med), 2)
                    stats.min = round(float(c_min), 2)
                    stats.max = round(float(c_max), 2)
                    stats.range = round(float(c_rng), 2)
                    stats.variance = round(float(c_var), 2)
                    stats.standard_deviation = round(float(c_std), 2)
                    stats.q1 = round(float(c_q1), 2) if c_q1 is not None else None
                    stats.q3 = round(float(c_q3), 2) if c_q3 is not None else None
                    if stats.q1 is not None and stats.q3 is not None:
                        stats.iqr = round(stats.q3 - stats.q1, 2)

            result_cols[name] = stats

        return DescriptiveStatsResponse(
            columns=result_cols,
            row_count_analyzed=row_count_analyzed,
            version_id=version_id,
        )

    @classmethod
    def compute_aggregation(
        cls,
        parquet_files: list[Path],
        group_by_columns: list[str],
        metric_column: str | None,
        aggregation: str,
        sort_order: str,
        limit: int | None,
        filters: list[FilterCondition] | None,
        version_id: str,
    ) -> AggregationResponse:
        conn = duckdb.connect(":memory:")
        src = cls._get_parquet_source_sql(parquet_files)
        params: list[Any] = []
        where_clause = cls._build_where_clause(filters, params)

        filtered_count = conn.execute(f"SELECT COUNT(*) FROM {src}{where_clause}", params).fetchone()[0]

        # Sanitize group by columns
        grp_cols_sql = [f"COALESCE(CAST({cls._sanitize_identifier(c)} AS VARCHAR), 'null')" for c in group_by_columns]
        grp_expr = " || ' - ' || ".join(grp_cols_sql)

        agg_func = aggregation.lower()
        if metric_column and metric_column != "count":
            m_col = cls._sanitize_identifier(metric_column)
            if agg_func == "sum":
                agg_sql = f"ROUND(COALESCE(SUM({m_col}), 0), 2)"
            elif agg_func in ("avg", "average"):
                agg_sql = f"ROUND(COALESCE(AVG({m_col}), 0), 2)"
            elif agg_func == "min":
                agg_sql = f"ROUND(COALESCE(MIN({m_col}), 0), 2)"
            elif agg_func == "max":
                agg_sql = f"ROUND(COALESCE(MAX({m_col}), 0), 2)"
            elif agg_func in ("distinct_count", "unique_count"):
                agg_sql = f"COUNT(DISTINCT {m_col})"
            else:
                agg_sql = f"COUNT({m_col})"
        else:
            agg_sql = "COUNT(*)"

        order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"
        limit_sql = f"LIMIT {int(limit)}" if limit and limit > 0 else "LIMIT 500"

        query = f"""
            SELECT
                {grp_expr} AS grp_key,
                {agg_sql} AS agg_val,
                COUNT(*) AS item_cnt
            FROM {src}{where_clause}
            GROUP BY {grp_expr}
            ORDER BY agg_val {order_dir}
            {limit_sql}
        """

        rows = conn.execute(query, params).fetchall()

        # Compute grand total of values for percentage share
        grand_total = sum(float(r[1] or 0) for r in rows)
        grand_total = round(grand_total, 2)

        items: list[AggregationItem] = []
        for r in rows:
            val = float(r[1] or 0)
            share = round((val / grand_total) * 100, 1) if grand_total != 0 else 0.0
            formatted = f"{val:,.2f}" if abs(val) >= 1 and not val.is_integer() else f"{int(val):,}" if val.is_integer() else f"{val:.2f}"
            items.append(
                AggregationItem(
                    key=str(r[0]),
                    value=val,
                    count=int(r[2]),
                    share_of_total=share,
                    formatted_value=formatted,
                )
            )

        return AggregationResponse(
            group_by_columns=group_by_columns,
            metric_column=metric_column or "count",
            aggregation=aggregation,
            items=items,
            total=grand_total,
            row_count_analyzed=filtered_count,
            version_id=version_id,
        )

    @classmethod
    def compute_time_series(
        cls,
        parquet_files: list[Path],
        date_column: str,
        value_column: str,
        interval: str,
        aggregation: str,
        filters: list[FilterCondition] | None,
        version_id: str,
    ) -> TimeSeriesResponse:
        conn = duckdb.connect(":memory:")
        src = cls._get_parquet_source_sql(parquet_files)
        params: list[Any] = []
        where_clause = cls._build_where_clause(filters, params)

        filtered_count = conn.execute(f"SELECT COUNT(*) FROM {src}{where_clause}", params).fetchone()[0]

        d_col = cls._sanitize_identifier(date_column)
        v_col = cls._sanitize_identifier(value_column)
        agg_func = aggregation.lower()

        if agg_func == "avg":
            val_expr = f"ROUND(AVG(CAST({v_col} AS DOUBLE)), 2)"
        elif agg_func == "count":
            val_expr = f"COUNT({v_col})"
        elif agg_func == "min":
            val_expr = f"ROUND(MIN(CAST({v_col} AS DOUBLE)), 2)"
        elif agg_func == "max":
            val_expr = f"ROUND(MAX(CAST({v_col} AS DOUBLE)), 2)"
        else:
            val_expr = f"ROUND(SUM(CAST({v_col} AS DOUBLE)), 2)"

        # Date truncation based on interval
        interv = interval.lower()
        if interv == "daily":
            period_expr = f"STRFTIME(TRY_CAST({d_col} AS DATE), '%Y-%m-%d')"
        elif interv == "weekly":
            period_expr = f"STRFTIME(DATE_TRUNC('week', TRY_CAST({d_col} AS DATE)), '%Y-W%W')"
        elif interv == "quarterly":
            period_expr = f"'Q' || QUARTER(TRY_CAST({d_col} AS DATE)) || ' ' || YEAR(TRY_CAST({d_col} AS DATE))"
        elif interv == "yearly":
            period_expr = f"CAST(YEAR(TRY_CAST({d_col} AS DATE)) AS VARCHAR)"
        else:  # monthly default
            period_expr = f"STRFTIME(TRY_CAST({d_col} AS DATE), '%b %Y')"

        ts_where = f"{where_clause} {'AND' if where_clause else 'WHERE'} TRY_CAST({d_col} AS DATE) IS NOT NULL"

        query = f"""
            SELECT
                {period_expr} AS period_label,
                EPOCH(DATE_TRUNC('{interv if interv in ('day', 'week', 'month', 'year') else 'month'}', TRY_CAST({d_col} AS DATE))) * 1000 AS ts,
                {val_expr} AS metric_val,
                COUNT(*) AS cnt
            FROM {src}{ts_where}
            GROUP BY 1, 2
            ORDER BY 2 ASC
        """

        rows = conn.execute(query, params).fetchall()

        points: list[TimeSeriesPoint] = []
        prev_val: float | None = None
        grand_total = 0.0

        for r in rows:
            val = float(r[2] or 0.0)
            grand_total += val
            growth_pct = None
            if prev_val is not None and prev_val != 0:
                growth_pct = round(((val - prev_val) / abs(prev_val)) * 100, 1)

            points.append(
                TimeSeriesPoint(
                    period=str(r[0]),
                    timestamp=int(r[1] or 0),
                    value=val,
                    growth_rate_pct=growth_pct,
                    count=int(r[3]),
                )
            )
            prev_val = val

        # Trend summary description
        if len(points) >= 2:
            first_val = points[0].value
            last_val = points[-1].value
            if first_val > 0:
                net_change_pct = round(((last_val - first_val) / first_val) * 100, 1)
                direction = "upward" if net_change_pct > 0 else "downward"
                trend_summary = f"Net trend is {direction}: shifted by {net_change_pct}% across {len(points)} periods."
            else:
                trend_summary = f"Metric concluded at {last_val} across {len(points)} chronological periods."
        else:
            trend_summary = f"Single snapshot observation of {grand_total} recorded."

        return TimeSeriesResponse(
            date_column=date_column,
            value_column=value_column,
            interval=interval,
            aggregation=aggregation,
            points=points,
            trend_summary=trend_summary,
            total=round(grand_total, 2),
            row_count_analyzed=filtered_count,
            version_id=version_id,
        )

    @classmethod
    def compute_data_quality(
        cls,
        parquet_files: list[Path],
        columns_meta: list[dict[str, Any]],
        version_id: str,
    ) -> QualityReportResponse:
        conn = duckdb.connect(":memory:")
        src = cls._get_parquet_source_sql(parquet_files)

        total_rows = conn.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
        if total_rows == 0:
            return QualityReportResponse(
                quality_score=100,
                issues=[
                    QualityIssue(
                        id="iss-empty-dataset",
                        type="missing_values",
                        title="Empty Dataset",
                        description="The dataset contains zero records.",
                        affected_count=0,
                        severity="info",
                        suggested_action="Upload or populate records to begin analysis.",
                    )
                ],
                row_count_analyzed=0,
                version_id=version_id,
            )

        issues: list[QualityIssue] = []
        penalty_points = 0

        # 1. Missing Values & Empty Columns Check
        for col in columns_meta:
            name = col["name"]
            col_ident = cls._sanitize_identifier(name)
            missing = conn.execute(
                f"SELECT COUNT(*) FROM {src} WHERE {col_ident} IS NULL OR CAST({col_ident} AS VARCHAR) = ''"
            ).fetchone()[0]

            pct = (missing / total_rows) * 100
            if pct == 100:
                issues.append(
                    QualityIssue(
                        id=f"iss-empty-col-{name}",
                        column=name,
                        type="missing_values",
                        title=f"Empty Column: {name}",
                        description=f'Column "{name}" has 100% missing values across all {total_rows} records.',
                        affected_count=total_rows,
                        severity="high",
                        suggested_action="Remove or populate this empty column before using it in calculations.",
                    )
                )
                penalty_points += 15
            elif pct > 25:
                issues.append(
                    QualityIssue(
                        id=f"iss-missing-{name}",
                        column=name,
                        type="missing_values",
                        title=f"High Missing Values in {name}",
                        description=f"{missing} rows ({pct:.1f}%) have empty or null entries in {name}.",
                        affected_count=missing,
                        severity="high",
                        suggested_action="Impute missing values using column median or flag rows in reporting.",
                    )
                )
                penalty_points += 12
            elif pct > 5:
                issues.append(
                    QualityIssue(
                        id=f"iss-missing-{name}",
                        column=name,
                        type="missing_values",
                        title=f"Missing Values in {name}",
                        description=f"{missing} record(s) ({pct:.1f}%) lack a valid {name}.",
                        affected_count=missing,
                        severity="medium",
                        suggested_action="Review source ingest for incomplete data feeds.",
                    )
                )
                penalty_points += 5

        # 2. Duplicate rows check
        distinct_cnt = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {src})").fetchone()[0]
        duplicate_count = max(0, total_rows - distinct_cnt)
        if duplicate_count > 0:
            dup_pct = (duplicate_count / total_rows) * 100
            issues.append(
                QualityIssue(
                    id="iss-duplicates",
                    type="duplicate_rows",
                    title="Duplicate Records Detected",
                    description=f"Found {duplicate_count} identical duplicate row(s) ({dup_pct:.1f}%) that may distort business metrics.",
                    affected_count=duplicate_count,
                    severity="high" if duplicate_count > 10 else "medium",
                    suggested_action="Deduplicate records based on unique transactional identifier.",
                )
            )
            penalty_points += 15 if duplicate_count > 10 else 6

        # 3. Suspicious negative values in commercial columns
        for col in columns_meta:
            name_lower = col["name"].lower()
            if any(k in name_lower for k in ("revenue", "sales", "price", "quantity", "arr")):
                col_ident = cls._sanitize_identifier(col["name"])
                neg_q = f"SELECT COUNT(*) FROM {src} WHERE TRY_CAST({col_ident} AS DOUBLE) < 0"
                neg_count = conn.execute(neg_q).fetchone()[0]
                if neg_count > 0:
                    issues.append(
                        QualityIssue(
                            id=f"iss-negative-{col['name']}",
                            column=col["name"],
                            type="suspicious_negative",
                            title=f"Suspicious Negative Values in {col['name']}",
                            description=f"{neg_count} row(s) contain negative figures in {col['name']}. Typically indicates returns or accounting reversals.",
                            affected_count=neg_count,
                            severity="medium",
                            suggested_action="Confirm if negative entries represent product returns or credit notes.",
                        )
                    )
                    penalty_points += 8

        # 4. Outlier detection using IQR (Tukey's method)
        for col in columns_meta:
            if col.get("inferred_type") in ("integer", "float", "number"):
                col_ident = cls._sanitize_identifier(col["name"])
                iqr_q = f"""
                    SELECT
                        QUANTILE_CONT({col_ident}, 0.25),
                        QUANTILE_CONT({col_ident}, 0.75),
                        COUNT({col_ident})
                    FROM {src}
                    WHERE {col_ident} IS NOT NULL
                """
                row = conn.execute(iqr_q).fetchone()
                if row and row[2] >= 20 and row[0] is not None and row[1] is not None:
                    q1, q3, valid_cnt = float(row[0]), float(row[1]), int(row[2])
                    iqr = q3 - q1
                    if iqr > 0:
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        outlier_q = f"""
                            SELECT COUNT(*)
                            FROM {src}
                            WHERE {col_ident} < {lower_bound} OR {col_ident} > {upper_bound}
                        """
                        outliers = conn.execute(outlier_q).fetchone()[0]
                        if 0 < outliers < valid_cnt * 0.1:
                            issues.append(
                                QualityIssue(
                                    id=f"iss-outlier-{col['name']}",
                                    column=col["name"],
                                    type="outlier",
                                    title=f"Statistical Outliers in {col['name']}",
                                    description=f"Detected {outliers} statistical outlier(s) outside range [{lower_bound:.0f}, {upper_bound:.0f}] using Tukey's IQR rule.",
                                    affected_count=outliers,
                                    severity="low",
                                    suggested_action="Verify whether extreme values represent data entry errors or legitimate high-value transactions.",
                                )
                            )
                            penalty_points += 4

        final_score = max(0, min(100, round(100 - penalty_points)))
        return QualityReportResponse(
            quality_score=final_score,
            issues=issues,
            row_count_analyzed=total_rows,
            version_id=version_id,
        )

    @classmethod
    def compare_versions(
        cls,
        baseline_files: list[Path],
        compare_files: list[Path],
        baseline_ver_num: str,
        compare_ver_num: str,
        metric_columns: list[str] | None,
    ) -> ComparisonResponse:
        conn = duckdb.connect(":memory:")
        base_src = cls._get_parquet_source_sql(baseline_files)
        comp_src = cls._get_parquet_source_sql(compare_files)

        base_rows = conn.execute(f"SELECT COUNT(*) FROM {base_src}").fetchone()[0]
        comp_rows = conn.execute(f"SELECT COUNT(*) FROM {comp_src}").fetchone()[0]
        row_diff = comp_rows - base_rows
        row_pct_change = round((row_diff / base_rows) * 100, 2) if base_rows > 0 else 0.0

        cur_base = conn.execute(f"SELECT * FROM {base_src} LIMIT 0")
        base_cols = set(desc[0] for desc in cur_base.description) if cur_base.description else set()
        cur_comp = conn.execute(f"SELECT * FROM {comp_src} LIMIT 0")
        comp_cols = set(desc[0] for desc in cur_comp.description) if cur_comp.description else set()

        added_cols = sorted(list(comp_cols - base_cols))
        removed_cols = sorted(list(base_cols - comp_cols))

        metric_diffs: list[ComparisonMetricDiff] = []
        if metric_columns:
            for col in metric_columns:
                if col in base_cols and col in comp_cols:
                    c_id = cls._sanitize_identifier(col)
                    b_val = conn.execute(f"SELECT COALESCE(SUM({c_id}), 0) FROM {base_src}").fetchone()[0]
                    c_val = conn.execute(f"SELECT COALESCE(SUM({c_id}), 0) FROM {comp_src}").fetchone()[0]
                    diff = float(c_val) - float(b_val)
                    pct = round((diff / float(b_val)) * 100, 2) if float(b_val) != 0 else 0.0
                    metric_diffs.append(
                        ComparisonMetricDiff(
                            column=col,
                            metric="sum",
                            baseline_value=round(float(b_val), 2),
                            compare_value=round(float(c_val), 2),
                            diff=round(diff, 2),
                            pct_change=pct,
                        )
                    )

        return ComparisonResponse(
            baseline_version=baseline_ver_num,
            compare_version=compare_ver_num,
            row_count_diff=row_diff,
            row_count_pct_change=row_pct_change,
            added_columns=added_cols,
            removed_columns=removed_cols,
            metric_diffs=metric_diffs,
            quality_score_diff=0,
        )
