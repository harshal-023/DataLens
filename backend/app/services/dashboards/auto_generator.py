"""DataLens AI Auto Dashboard Generator Service.

End-to-end autonomous dashboard planning, deterministic DuckDB execution,
and layout generation reusing existing DataLens intelligence and analytics architecture.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.dashboard import Dashboard, DashboardFilter, DashboardWidget
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.schemas.auto_dashboard import (
    AutoDashboardPreviewResponse,
    AutoDashboardRequest,
    AutoDashboardSaveRequest,
    AutoDashboardStage,
    AutoDashboardStatusResponse,
    GeneratedChartItem,
    GeneratedFilterItem,
    GeneratedInsightItem,
    GeneratedKPIItem,
)
from app.schemas.dashboard import (
    DashboardDetailResponse,
    DashboardFilterResponse,
    DashboardWidgetResponse,
)
from app.services.ai.factory import AIProviderFactory
from app.services.analytics.engine import AnalyticsEngine
from app.services.intelligence.profiler import DatasetIntelligenceProfiler


def normalize_profile_columns(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalizes dataset profiling columns whether represented as dict or list of dicts/names."""
    raw = profile.get("columns", [])
    result: list[dict[str, Any]] = []

    if isinstance(raw, dict):
        for col_key, col_val in raw.items():
            if isinstance(col_val, dict):
                c = dict(col_val)
                name = c.get("name") or c.get("column_name") or str(col_key)
                c["name"] = name
                if "candidate_pk" not in c and "is_primary_key" in c:
                    c["candidate_pk"] = c["is_primary_key"]
                result.append(c)
            else:
                result.append({"name": str(col_key)})
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                c = dict(item)
                name = c.get("name") or c.get("column_name") or "unnamed"
                c["name"] = name
                if "candidate_pk" not in c and "is_primary_key" in c:
                    c["candidate_pk"] = c["is_primary_key"]
                result.append(c)
            elif isinstance(item, str):
                result.append({"name": item})

    return result


class DatasetIntelligenceResolver:
    """Resolves dataset files, profiles column metadata, and detects business domain."""

    @classmethod
    async def resolve_dataset_and_files(
        cls,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[Dataset, DatasetVersion, list[Path]]:
        stmt = (
            select(Dataset)
            .where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id)
        )
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise DataLensException("Dataset not found in workspace.", code="NOT_FOUND")

        v_stmt = select(DatasetVersion).where(DatasetVersion.dataset_id == dataset.id)
        if version_id:
            v_stmt = v_stmt.where(DatasetVersion.id == version_id)
        else:
            v_stmt = v_stmt.order_by(desc(DatasetVersion.created_at))

        v_res = await db.execute(v_stmt)
        version = v_res.scalars().first()
        if not version:
            raise DataLensException("No valid version available for this dataset.", code="NO_VERSION")

        storage_root = Path(settings.STORAGE_ROOT).resolve()
        parquet_files: list[Path] = []

        if getattr(version, "storage_key", None):
            cleaned_key = str(version.storage_key).strip().replace("\\", "/")
            manifest_or_parquet = Path(cleaned_key) if Path(cleaned_key).is_file() else (storage_root / cleaned_key)
            if manifest_or_parquet.is_file():
                if cleaned_key.endswith(".json"):
                    try:
                        manifest = json.loads(manifest_or_parquet.read_text(encoding="utf-8"))
                        for p in manifest.get("parts", []):
                            part_clean = str(p).strip().replace("\\", "/")
                            part_path = Path(part_clean) if Path(part_clean).is_file() else (storage_root / part_clean)
                            if part_path.is_file():
                                parquet_files.append(part_path)
                    except Exception as e:
                        logger.warning(f"Failed parsing manifest: {e}")
                elif cleaned_key.endswith(".parquet"):
                    parquet_files = [manifest_or_parquet]

        if not parquet_files:
            for p in (getattr(version, "storage_paths", None) or []):
                p_clean = str(p).strip().replace("\\", "/")
                cand = Path(p_clean) if Path(p_clean).is_file() else (storage_root / p_clean)
                if cand.is_file():
                    parquet_files.append(cand)

        if not parquet_files:
            candidate = storage_root / "datasets" / str(dataset.id) / f"{version.id}.parquet"
            if candidate.is_file():
                parquet_files = [candidate]

        if not parquet_files:
            dataset_dir = storage_root / "datasets" / str(dataset.id)
            if dataset_dir.is_dir():
                found_parquets = list(dataset_dir.glob("*.parquet"))
                if found_parquets:
                    parquet_files = [found_parquets[0]]

        if not parquet_files:
            raise DataLensException(
                f"No analytical data files (parquet) found on storage for dataset version {version.id}.",
                code="STORAGE_FILE_MISSING",
            )

        return dataset, version, parquet_files

    @classmethod
    def detect_business_domain(cls, profile: dict[str, Any], requested_domain: str | None) -> str:
        if requested_domain and requested_domain.lower() != "automatic":
            return requested_domain.lower()

        cols = normalize_profile_columns(profile)
        col_names = [c["name"].lower() for c in cols if "name" in c]
        joined = " ".join(col_names)

        if any(k in joined for k in ("sales", "revenue", "order", "price", "mrp", "discount", "customer")):
            return "sales"
        if any(k in joined for k in ("salary", "employee", "dept", "department", "hire_date", "payroll")):
            return "hr"
        if any(k in joined for k in ("stock", "inventory", "sku", "warehouse", "quantity", "supplier")):
            return "inventory"
        if any(k in joined for k in ("profit", "margin", "expense", "budget", "tax", "cost")):
            return "finance"
        if any(k in joined for k in ("campaign", "clicks", "impressions", "leads", "ad_spend")):
            return "marketing"
        if any(k in joined for k in ("shipment", "carrier", "delivery", "transit", "freight")):
            return "logistics"

        return "general"


class DeterministicDashboardPlanner:
    """Builds robust, analytically sound dashboard layout specifications without external AI dependencies."""

    @classmethod
    def plan_dashboard(
        cls,
        profile: dict[str, Any],
        business_domain: str,
        user_objective: str | None,
        theme: str,
        dataset_name: str,
    ) -> dict[str, Any]:
        columns = normalize_profile_columns(profile)
        num_cols = [c["name"] for c in columns if c.get("is_measure") or any(t in c.get("physical_type", "").lower() for t in ("int", "double", "float", "decimal", "numeric"))]
        date_cols = [c["name"] for c in columns if any(t in c.get("logical_type", "").lower() or t in c.get("physical_type", "").lower() or t in c.get("semantic_type", "").lower() for t in ("date", "time", "timestamp"))]
        cat_cols = [c["name"] for c in columns if c.get("is_dimension") or any(t in c.get("physical_type", "").lower() for t in ("varchar", "string", "text"))]
        id_cols = [c["name"] for c in columns if c.get("candidate_pk") or any(k in c["name"].lower() for k in ("_id", "id", "code", "key"))]

        # Filter out id columns from measures
        real_measures = [m for m in num_cols if not any(k in m.lower() for k in ("_id", "id", "zip", "code", "year"))]
        if not real_measures and num_cols:
            real_measures = num_cols

        # Filter out ids from categories
        real_categories = [c for c in cat_cols if not any(k in c.lower() for k in ("_id", "id", "guid", "uuid", "hash"))]
        if not real_categories and cat_cols:
            real_categories = cat_cols

        primary_date = date_cols[0] if date_cols else None
        primary_measure = real_measures[0] if real_measures else None
        secondary_measure = real_measures[1] if len(real_measures) > 1 else None
        primary_cat = real_categories[0] if real_categories else None
        secondary_cat = real_categories[1] if len(real_categories) > 1 else None
        id_col = id_cols[0] if id_cols else None

        # Title formatting
        domain_titles = {
            "sales": f"{dataset_name} – Sales & Revenue Performance",
            "finance": f"{dataset_name} – Financial Analysis & Margins",
            "hr": f"{dataset_name} – Workforce & Headcount Overview",
            "inventory": f"{dataset_name} – Inventory & Stock Intelligence",
            "marketing": f"{dataset_name} – Marketing Performance & Campaign ROI",
            "logistics": f"{dataset_name} – Logistics & Distribution Operations",
            "customer": f"{dataset_name} – Customer Analytics & Retention",
            "general": f"{dataset_name} – Executive Intelligence Dashboard",
        }
        dash_title = domain_titles.get(business_domain, f"{dataset_name} Analytics Dashboard")
        row_count = profile.get("row_count") or profile.get("total_rows") or 0
        dash_desc = (
            f"Autonomous executive business dashboard generated from verified DuckDB calculations across "
            f"{row_count:,} records."
        )

        # Plan KPIs (3 to 4 items)
        kpi_specs: list[dict[str, Any]] = []
        if primary_measure:
            kpi_specs.append({
                "title": f"Total {primary_measure.replace('_', ' ').title()}",
                "metric_column": primary_measure,
                "aggregation": "sum",
            })
            kpi_specs.append({
                "title": f"Average {primary_measure.replace('_', ' ').title()}",
                "metric_column": primary_measure,
                "aggregation": "avg",
            })
        if secondary_measure:
            kpi_specs.append({
                "title": f"Total {secondary_measure.replace('_', ' ').title()}",
                "metric_column": secondary_measure,
                "aggregation": "sum",
            })
        if id_col:
            kpi_specs.append({
                "title": f"Unique {id_col.replace('_', ' ').replace('id', '').strip().title() or 'Entities'}",
                "metric_column": id_col,
                "aggregation": "distinct_count",
            })
        else:
            kpi_specs.append({
                "title": "Total Records",
                "metric_column": "*",
                "aggregation": "count",
            })

        # Ensure max 4 KPIs
        kpi_specs = kpi_specs[:4]

        # Plan Charts
        chart_specs: list[dict[str, Any]] = []

        # Chart 1: Time Series Trend (if date exists)
        if primary_date and primary_measure:
            chart_specs.append({
                "widget_type": "line",
                "title": f"Monthly {primary_measure.replace('_', ' ').title()} Trend",
                "description": "Historical time-series trajectory aggregated by month",
                "grid_x": 0,
                "grid_y": 3,
                "grid_w": 7 if primary_cat else 12,
                "grid_h": 6,
                "query_config": {
                    "time_column": primary_date,
                    "metric_column": primary_measure,
                    "granularity": "month",
                    "aggregation": "sum",
                },
            })

        # Chart 2: Categorical Breakdown (Donut or Horizontal Bar)
        if primary_cat:
            m_col = primary_measure or "*"
            m_agg = "sum" if primary_measure else "count"
            chart_specs.append({
                "widget_type": "donut",
                "title": f"{m_col.replace('_', ' ').title()} by {primary_cat.replace('_', ' ').title()}",
                "description": f"Proportional composition by {primary_cat}",
                "grid_x": 7 if primary_date and primary_measure else 0,
                "grid_y": 3,
                "grid_w": 5 if primary_date and primary_measure else 6,
                "grid_h": 6,
                "query_config": {
                    "group_by_column": primary_cat,
                    "metric_column": m_col,
                    "aggregation": m_agg,
                    "limit": 8,
                },
            })

        # Chart 3: Secondary Comparison or Multi-Bar
        comp_cat = secondary_cat or primary_cat
        if comp_cat:
            chart_specs.append({
                "widget_type": "bar",
                "title": f"Distribution by {comp_cat.replace('_', ' ').title()}",
                "description": "Ranked breakdown across segments",
                "grid_x": 0,
                "grid_y": 9,
                "grid_w": 6,
                "grid_h": 6,
                "query_config": {
                    "group_by_column": comp_cat,
                    "metric_column": secondary_measure or primary_measure or "*",
                    "aggregation": "sum" if (secondary_measure or primary_measure) else "count",
                    "limit": 10,
                    "sort_direction": "desc",
                },
            })

        # Chart 4: Detailed Summary Table
        table_cols = [c["name"] for c in columns[:6]]
        chart_specs.append({
            "widget_type": "table",
            "title": "Detailed Records Summary",
            "description": "Granular record-level sample with verified column values",
            "grid_x": 6 if comp_cat else 0,
            "grid_y": 9,
            "grid_w": 6 if comp_cat else 12,
            "grid_h": 6,
            "query_config": {
                "columns": table_cols,
                "limit": 10,
            },
        })

        # Plan Filters
        filter_specs: list[dict[str, Any]] = []
        if primary_date:
            filter_specs.append({
                "name": f"Date Range ({primary_date})",
                "column_name": primary_date,
                "filter_type": "date_range",
                "default_operator": "between",
            })
        if primary_cat:
            filter_specs.append({
                "name": primary_cat.replace("_", " ").title(),
                "column_name": primary_cat,
                "filter_type": "dropdown",
                "default_operator": "eq",
            })
        if secondary_cat:
            filter_specs.append({
                "name": secondary_cat.replace("_", " ").title(),
                "column_name": secondary_cat,
                "filter_type": "dropdown",
                "default_operator": "eq",
            })

        return {
            "title": dash_title,
            "description": dash_desc,
            "business_domain": business_domain,
            "theme": theme or "ocean",
            "kpis": kpi_specs,
            "charts": chart_specs,
            "filters": filter_specs,
        }


class AIDashboardPlanner:
    """Uses LLM when available to formulate context-aware dashboard plans with strict schema validation."""

    @classmethod
    async def generate_plan(
        cls,
        profile: dict[str, Any],
        business_domain: str,
        user_objective: str | None,
        theme: str,
        dataset_name: str,
    ) -> dict[str, Any]:
        # Always obtain the deterministic plan first as guaranteed baseline
        base_plan = DeterministicDashboardPlanner.plan_dashboard(
            profile=profile,
            business_domain=business_domain,
            user_objective=user_objective,
            theme=theme,
            dataset_name=dataset_name,
        )

        # Attempt AI enhancement if provider available
        try:
            provider = AIProviderFactory.get_gemini_provider()
            if not provider or provider.name == "deterministic":
                return base_plan

            columns = normalize_profile_columns(profile)
            row_count = profile.get("row_count") or profile.get("total_rows") or 0
            col_summary = [
                {
                    "name": c["name"],
                    "type": c.get("physical_type", "string"),
                    "semantic": c.get("semantic_type", "unknown"),
                    "distinct": c.get("distinct_count", 0),
                }
                for c in columns[:25]
            ]

            prompt = (
                f"You are a Principal Business Intelligence Architect designing an executive dashboard.\n"
                f"Dataset: '{dataset_name}' ({row_count} rows)\n"
                f"Domain: {business_domain}\n"
                f"User Goal: {user_objective or 'Provide actionable executive business visibility'}\n"
                f"Available Columns:\n{json.dumps(col_summary, indent=2)}\n\n"
                f"Provide a JSON response with:\n"
                f"- 'title': concise executive dashboard title\n"
                f"- 'description': 1-sentence analytical overview\n"
                f"- 'kpis': array of up to 4 objects with 'title', 'metric_column', 'aggregation' (sum, avg, count, distinct_count)\n"
                f"Only select existing columns. Return strictly JSON."
            )

            resp = await provider.generate_text(prompt, temperature=0.1)
            raw_text = resp.get("text", "") if isinstance(resp, dict) else str(resp or "")

            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group(0))
                existing_cols = {c["name"] for c in columns}
                if ai_data.get("title"):
                    base_plan["title"] = str(ai_data["title"])[:100]
                if ai_data.get("description"):
                    base_plan["description"] = str(ai_data["description"])[:255]

                # Validate AI suggested KPIs
                valid_kpis = []
                for k in ai_data.get("kpis", []):
                    col = k.get("metric_column")
                    if col and (col in existing_cols or col == "*"):
                        valid_kpis.append({
                            "title": str(k.get("title", col.title()))[:50],
                            "metric_column": col,
                            "aggregation": k.get("aggregation", "sum").lower(),
                        })
                if valid_kpis:
                    base_plan["kpis"] = valid_kpis[:4]

        except Exception as e:
            logger.info(f"AI planner fallback to deterministic: {e}")

        return base_plan


class DashboardAnalyticsExecutor:
    """Executes verified analytical queries via DuckDB for all planned dashboard widgets."""

    @classmethod
    def execute_plan_metrics(
        cls,
        plan: dict[str, Any],
        parquet_files: list[Path],
    ) -> tuple[list[GeneratedKPIItem], list[GeneratedChartItem], list[GeneratedFilterItem], list[GeneratedInsightItem]]:
        source_sql = AnalyticsEngine._get_parquet_source_sql(parquet_files)
        con = duckdb.connect(":memory:")

        kpis_out: list[GeneratedKPIItem] = []
        charts_out: list[GeneratedChartItem] = []
        filters_out: list[GeneratedFilterItem] = []
        insights_out: list[GeneratedInsightItem] = []

        try:
            # 1. Execute KPIs
            kpi_specs = plan.get("kpis", [])
            kpi_count = len(kpi_specs)
            grid_w = 12 // max(1, kpi_count) if kpi_count > 0 else 3

            for idx, kpi in enumerate(kpi_specs):
                m_col = kpi.get("metric_column")
                agg = kpi.get("aggregation", "sum").lower()

                if m_col and m_col != "*":
                    m_safe = AnalyticsEngine._sanitize_identifier(m_col)
                    if agg in ("sum", "total"):
                        expr = f"ROUND(COALESCE(SUM({m_safe}), 0), 2)"
                    elif agg in ("avg", "average"):
                        expr = f"ROUND(COALESCE(AVG({m_safe}), 0), 2)"
                    elif agg in ("distinct_count", "unique_count"):
                        expr = f"COUNT(DISTINCT {m_safe})"
                    elif agg == "max":
                        expr = f"ROUND(COALESCE(MAX({m_safe}), 0), 2)"
                    elif agg == "min":
                        expr = f"ROUND(COALESCE(MIN({m_safe}), 0), 2)"
                    else:
                        expr = f"COUNT({m_safe})"
                else:
                    expr = "COUNT(*)"

                val = 0.0
                try:
                    res = con.execute(f"SELECT {expr} FROM {source_sql}").fetchone()
                    if res and res[0] is not None:
                        val = float(res[0])
                except Exception as e:
                    logger.warning(f"KPI query error for {m_col}: {e}")

                if val >= 1_000_000:
                    formatted = f"{val / 1_000_000:.2f}M"
                elif val >= 1_000:
                    formatted = f"{val / 1_000:.2f}K"
                elif val == int(val):
                    formatted = f"{int(val):,}"
                else:
                    formatted = f"{val:,.2f}"

                kpis_out.append(
                    GeneratedKPIItem(
                        title=kpi.get("title", "KPI"),
                        metric_column=m_col,
                        aggregation=agg,
                        formatted_value=formatted,
                        numeric_value=val,
                        grid_x=idx * grid_w,
                        grid_y=0,
                        grid_w=grid_w,
                        grid_h=3,
                        display_settings={"color_palette": plan.get("theme", "ocean")},
                    )
                )

            # 2. Execute Charts
            for chart in plan.get("charts", []):
                w_type = chart.get("widget_type", "bar")
                q_cfg = chart.get("query_config", {})
                calculated_data: Any = None

                try:
                    if w_type in ("line", "area"):
                        time_col = q_cfg.get("time_column")
                        m_col = q_cfg.get("metric_column")
                        granularity = q_cfg.get("granularity", "month")
                        t_safe = AnalyticsEngine._sanitize_identifier(time_col)
                        m_safe = AnalyticsEngine._sanitize_identifier(m_col) if m_col and m_col != "*" else "*"
                        agg_fn = "SUM" if q_cfg.get("aggregation") == "sum" else "AVG"
                        m_expr = f"ROUND({agg_fn}({m_safe}), 2)" if m_safe != "*" else "COUNT(*)"

                        query = f"""
                        SELECT strftime(date_trunc('{granularity}', TRY_CAST({t_safe} AS TIMESTAMP)), '%Y-%m') as period, {m_expr} as val
                        FROM {source_sql}
                        WHERE {t_safe} IS NOT NULL AND TRY_CAST({t_safe} AS TIMESTAMP) IS NOT NULL
                        GROUP BY 1
                        ORDER BY 1
                        LIMIT 36
                        """
                        rows = con.execute(query).fetchall()
                        calculated_data = {
                            "labels": [str(r[0]) for r in rows],
                            "values": [float(r[1] or 0) for r in rows],
                            "metric": m_col or "Count",
                            "granularity": granularity,
                        }

                    elif w_type in ("bar", "horizontal_bar", "donut", "pie"):
                        grp_col = q_cfg.get("group_by_column")
                        m_col = q_cfg.get("metric_column")
                        limit = q_cfg.get("limit", 8)
                        g_safe = AnalyticsEngine._sanitize_identifier(grp_col)
                        m_safe = AnalyticsEngine._sanitize_identifier(m_col) if m_col and m_col != "*" else "*"
                        agg_fn = "SUM" if q_cfg.get("aggregation") == "sum" else "COUNT"
                        m_expr = f"ROUND({agg_fn}({m_safe}), 2)" if m_safe != "*" else "COUNT(*)"

                        query = f"""
                        SELECT COALESCE(CAST({g_safe} AS VARCHAR), 'Unknown') as label, {m_expr} as val
                        FROM {source_sql}
                        GROUP BY 1
                        ORDER BY 2 DESC
                        LIMIT {limit}
                        """
                        rows = con.execute(query).fetchall()
                        items = [{"label": str(r[0]), "value": float(r[1] or 0)} for r in rows]
                        calculated_data = {
                            "categories": [i["label"] for i in items],
                            "values": [i["value"] for i in items],
                            "items": items,
                            "metric": m_col or "Count",
                            "group_by": grp_col,
                            "total": sum(i["value"] for i in items),
                        }

                    elif w_type == "table":
                        cols = q_cfg.get("columns", [])
                        sanitized_cols = [AnalyticsEngine._sanitize_identifier(c) for c in cols]
                        select_clause = ", ".join(sanitized_cols) if sanitized_cols else "*"
                        query = f"SELECT {select_clause} FROM {source_sql} LIMIT {q_cfg.get('limit', 10)}"
                        cursor = con.execute(query)
                        cols_names = [d[0] for d in (cursor.description or [])]
                        raw_rows = cursor.fetchall()
                        rows_list = [dict(zip(cols_names, r, strict=False)) for r in raw_rows]
                        calculated_data = {
                            "columns": cols_names,
                            "rows": rows_list,
                            "row_count": len(rows_list),
                        }

                except Exception as e:
                    logger.warning(f"Error calculating chart {chart.get('title')}: {e}")
                    calculated_data = {"error": str(e), "categories": [], "values": []}

                charts_out.append(
                    GeneratedChartItem(
                        widget_type=w_type,
                        title=chart.get("title", "Chart"),
                        description=chart.get("description"),
                        grid_x=chart.get("grid_x", 0),
                        grid_y=chart.get("grid_y", 3),
                        grid_w=chart.get("grid_w", 6),
                        grid_h=chart.get("grid_h", 4),
                        query_config=q_cfg,
                        display_settings={"color_palette": plan.get("theme", "ocean")},
                        calculated_data=calculated_data,
                    )
                )

            # 3. Format Filters
            for f in plan.get("filters", []):
                filters_out.append(
                    GeneratedFilterItem(
                        name=f.get("name", "Filter"),
                        column_name=f.get("column_name"),
                        filter_type=f.get("filter_type", "dropdown"),
                        default_operator=f.get("default_operator", "eq"),
                    )
                )

            # 4. Generate Verified Insights from Calculated Results
            for c in charts_out:
                data = c.calculated_data
                if isinstance(data, dict) and data.get("items") and len(data["items"]) > 0:
                    top_item = data["items"][0]
                    total = data.get("total", 0)
                    pct = round((top_item["value"] / total * 100), 1) if total > 0 else 0
                    insights_out.append(
                        GeneratedInsightItem(
                            title=f"Leading Segment: {top_item['label']}",
                            observation=(
                                f"{top_item['label']} constitutes the largest recorded share of "
                                f"{c.title} with {pct}% of total volume ({top_item['value']:,.2f})."
                            ),
                            evidence=f"Calculated from DuckDB aggregation on column '{c.query_config.get('group_by_column')}'.",
                            category="distribution",
                            recommendation=f"Prioritize operational focus on high-performing segment '{top_item['label']}'.",
                        )
                    )
                    break

            if kpis_out:
                primary_kpi = kpis_out[0]
                insights_out.append(
                    GeneratedInsightItem(
                        title=f"Baseline Milestone: {primary_kpi.title}",
                        observation=f"{primary_kpi.title} stands at {primary_kpi.formatted_value} across all verified dataset records.",
                        evidence=f"Calculated via {primary_kpi.aggregation.upper()} on column '{primary_kpi.metric_column}'.",
                        category="milestone",
                    )
                )

        finally:
            con.close()

        return kpis_out, charts_out, filters_out, insights_out


class AutoDashboardSessionManager:
    """Manages generation jobs in-memory and persists the final dashboard to PostgreSQL."""

    _active_sessions: dict[uuid.UUID, dict[str, Any]] = {}

    @classmethod
    def create_session(
        cls,
        workspace_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_name: str,
    ) -> uuid.UUID:
        gen_id = uuid.uuid4()
        now = datetime.now(UTC)
        cls._active_sessions[gen_id] = {
            "generation_id": gen_id,
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "status": "running",
            "stage": AutoDashboardStage.READING_STRUCTURE.value,
            "progress_pct": 10,
            "message": "Reading dataset structure...",
            "preview_ready": False,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "preview": None,
        }
        return gen_id

    @classmethod
    def update_session(
        cls,
        gen_id: uuid.UUID,
        stage: AutoDashboardStage,
        progress_pct: int,
        message: str,
        preview: AutoDashboardPreviewResponse | None = None,
        error: str | None = None,
    ) -> None:
        if gen_id not in cls._active_sessions:
            return
        sess = cls._active_sessions[gen_id]
        sess["stage"] = stage.value
        sess["progress_pct"] = progress_pct
        sess["message"] = message
        sess["updated_at"] = datetime.now(UTC)
        if error:
            sess["status"] = "failed"
            sess["error"] = error
        elif stage == AutoDashboardStage.COMPLETED:
            sess["status"] = "completed"
            sess["preview_ready"] = True
            sess["preview"] = preview

    @classmethod
    def get_status(cls, gen_id: uuid.UUID, workspace_id: uuid.UUID) -> AutoDashboardStatusResponse:
        sess = cls._active_sessions.get(gen_id)
        if not sess or sess["workspace_id"] != workspace_id:
            raise DataLensException("Generation session not found.", code="NOT_FOUND")
        return AutoDashboardStatusResponse(
            generation_id=sess["generation_id"],
            status=sess["status"],
            stage=sess["stage"],
            progress_pct=sess["progress_pct"],
            message=sess["message"],
            dataset_id=sess["dataset_id"],
            dataset_name=sess["dataset_name"],
            preview_ready=sess["preview_ready"],
            error=sess["error"],
            created_at=sess["created_at"],
            updated_at=sess["updated_at"],
        )

    @classmethod
    def get_preview(cls, gen_id: uuid.UUID, workspace_id: uuid.UUID) -> AutoDashboardPreviewResponse:
        sess = cls._active_sessions.get(gen_id)
        if not sess or sess["workspace_id"] != workspace_id:
            raise DataLensException("Generation session not found.", code="NOT_FOUND")
        if not sess["preview_ready"] or not sess.get("preview"):
            raise DataLensException("Dashboard preview is not ready yet.", code="PREVIEW_NOT_READY")
        return sess["preview"]

    @classmethod
    def cancel_session(cls, gen_id: uuid.UUID, workspace_id: uuid.UUID) -> dict[str, bool]:
        sess = cls._active_sessions.get(gen_id)
        if not sess or sess["workspace_id"] != workspace_id:
            raise DataLensException("Generation session not found.", code="NOT_FOUND")
        sess["status"] = "cancelled"
        sess["stage"] = AutoDashboardStage.CANCELLED.value
        sess["message"] = "Dashboard generation was cancelled by user."
        return {"cancelled": True}

    @classmethod
    async def run_pipeline(
        cls,
        gen_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: AutoDashboardRequest,
        db: AsyncSession,
    ) -> AutoDashboardPreviewResponse:
        try:
            # Stage 1: Resolve dataset and storage files
            cls.update_session(gen_id, AutoDashboardStage.READING_STRUCTURE, 15, "Reading dataset structure & storage files...")
            dataset, version, parquet_files = await DatasetIntelligenceResolver.resolve_dataset_and_files(
                dataset_id=req.dataset_id,
                version_id=req.dataset_version_id,
                workspace_id=workspace_id,
                db=db,
            )

            # Stage 2: Profile columns and data types
            cls.update_session(gen_id, AutoDashboardStage.UNDERSTANDING_COLUMNS, 30, "Analyzing data types, nulls, and distributions...")
            profile = DatasetIntelligenceProfiler.profile_parquet_dataset(parquet_files)

            # Stage 3: Identify business domain and candidate metrics
            cls.update_session(gen_id, AutoDashboardStage.IDENTIFYING_METRICS, 45, "Identifying business domain and measures...")
            detected_domain = DatasetIntelligenceResolver.detect_business_domain(profile, req.business_domain)

            # Stage 4: Formulate structured dashboard plan (AI + Deterministic Fallback)
            cls.update_session(gen_id, AutoDashboardStage.SELECTING_VISUALIZATIONS, 60, "Selecting optimal KPIs and visualization layouts...")
            plan = await AIDashboardPlanner.generate_plan(
                profile=profile,
                business_domain=detected_domain,
                user_objective=req.user_objective,
                theme=req.visual_style or "ocean",
                dataset_name=dataset.name,
            )

            # Stage 5: Calculate verified results via DuckDB
            cls.update_session(gen_id, AutoDashboardStage.CALCULATING_RESULTS, 75, "Executing DuckDB analytical queries...")
            kpis, charts, filters, insights = DashboardAnalyticsExecutor.execute_plan_metrics(
                plan=plan,
                parquet_files=parquet_files,
            )

            # Stage 6: Layout design and preview preparation
            cls.update_session(gen_id, AutoDashboardStage.PREPARING_INSIGHTS, 90, "Synthesizing business observations and preview...")
            preview = AutoDashboardPreviewResponse(
                generation_id=gen_id,
                dataset_id=dataset.id,
                dataset_name=dataset.name,
                dataset_version_id=version.id,
                title=plan["title"],
                description=plan["description"],
                business_domain=detected_domain,
                theme=plan["theme"],
                kpis=kpis,
                charts=charts,
                filters=filters,
                insights=insights,
                total_widgets=len(kpis) + len(charts) + len(insights),
                created_at=datetime.now(UTC),
            )

            cls.update_session(gen_id, AutoDashboardStage.COMPLETED, 100, "Dashboard generated successfully!", preview=preview)
            return preview

        except DataLensException:
            raise
        except Exception as e:
            logger.error(f"Auto dashboard pipeline failed: {e}", exc_info=True)
            cls.update_session(gen_id, AutoDashboardStage.FAILED, 0, "Generation failed.", error=str(e))
            raise DataLensException(f"Dashboard generation failed: {str(e)}", code="GENERATION_FAILED")

    @classmethod
    async def save_dashboard_to_database(
        cls,
        gen_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        save_req: AutoDashboardSaveRequest,
        db: AsyncSession,
    ) -> DashboardDetailResponse:
        sess = cls._active_sessions.get(gen_id)
        if not sess or sess["workspace_id"] != workspace_id:
            raise DataLensException("Generation session not found.", code="NOT_FOUND")

        preview: AutoDashboardPreviewResponse | None = sess.get("preview")
        if not preview:
            raise DataLensException("No preview available to save.", code="BAD_REQUEST")

        title = save_req.title or preview.title
        description = save_req.description or preview.description
        theme = save_req.theme or preview.theme

        # 1. Create Dashboard Entity
        dashboard = Dashboard(
            workspace_id=workspace_id,
            created_by=user_id,
            title=title,
            description=description,
            visibility="workspace",
            layout_config={
                "theme": theme,
                "auto_generated": True,
                "generation_id": str(gen_id),
                "business_domain": preview.business_domain,
            },
        )
        db.add(dashboard)
        await db.flush()

        # 2. Persist KPI Widgets
        kpis = save_req.kpis if save_req.kpis is not None else preview.kpis
        for k in kpis:
            w = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=preview.dataset_id,
                dataset_version_id=preview.dataset_version_id,
                widget_type="kpi",
                title=k.title,
                grid_x=k.grid_x,
                grid_y=k.grid_y,
                grid_w=k.grid_w,
                grid_h=k.grid_h,
                query_config={
                    "metric_column": k.metric_column,
                    "aggregation": k.aggregation,
                },
                display_settings={
                    "formatted_value": k.formatted_value,
                    "theme": theme,
                    **k.display_settings,
                },
            )
            db.add(w)

        # 3. Persist Chart Widgets
        charts = save_req.charts if save_req.charts is not None else preview.charts
        for c in charts:
            w = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=preview.dataset_id,
                dataset_version_id=preview.dataset_version_id,
                widget_type=c.widget_type,
                title=c.title,
                description=c.description,
                grid_x=c.grid_x,
                grid_y=c.grid_y,
                grid_w=c.grid_w,
                grid_h=c.grid_h,
                query_config=c.query_config,
                display_settings={
                    "theme": theme,
                    **c.display_settings,
                },
            )
            db.add(w)

        # 4. Persist AI Insight Cards as Text Widgets
        for ins in preview.insights:
            text_body = f"**{ins.title}**\n\n{ins.observation}\n\n*Evidence: {ins.evidence}*"
            if ins.recommendation:
                text_body += f"\n\n**Recommendation:** {ins.recommendation}"
            w = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=preview.dataset_id,
                dataset_version_id=preview.dataset_version_id,
                widget_type="text",
                title=f"AI Insight: {ins.title}",
                grid_x=0,
                grid_y=15,
                grid_w=12,
                grid_h=3,
                query_config={"text_content": text_body},
                display_settings={"theme": theme, "card_style": "callout"},
            )
            db.add(w)

        # 5. Persist Filters
        filters = save_req.filters if save_req.filters is not None else preview.filters
        for f in filters:
            d_filter = DashboardFilter(
                dashboard_id=dashboard.id,
                name=f.name,
                column_name=f.column_name,
                filter_type=f.filter_type,
                default_operator=f.default_operator,
                default_value=f.default_value,
                config=f.config,
            )
            db.add(d_filter)

        await db.commit()
        await db.refresh(dashboard)

        # Load populated relations and return detail
        stmt = (
            select(Dashboard)
            .where(Dashboard.id == dashboard.id)
        )
        res = await db.execute(stmt)
        saved_dashboard = res.scalar_one()

        # Query all widgets and filters for response
        w_stmt = select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard.id).order_by(DashboardWidget.grid_y, DashboardWidget.grid_x)
        f_stmt = select(DashboardFilter).where(DashboardFilter.dashboard_id == dashboard.id)
        w_res = await db.execute(w_stmt)
        f_res = await db.execute(f_stmt)

        all_widgets = w_res.scalars().all()
        all_filters = f_res.scalars().all()

        return DashboardDetailResponse(
            id=saved_dashboard.id,
            workspace_id=saved_dashboard.workspace_id,
            created_by=saved_dashboard.created_by,
            title=saved_dashboard.title,
            description=saved_dashboard.description,
            visibility=saved_dashboard.visibility,
            is_archived=saved_dashboard.is_archived,
            layout_config=saved_dashboard.layout_config,
            created_at=saved_dashboard.created_at,
            updated_at=saved_dashboard.updated_at,
            widgets=[DashboardWidgetResponse.model_validate(w) for w in all_widgets],
            filters=[DashboardFilterResponse.model_validate(f) for f in all_filters],
        )
