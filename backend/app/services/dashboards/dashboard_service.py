import json
import time
import uuid
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.dashboard import Dashboard, DashboardFilter, DashboardWidget
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardDetailResponse,
    DashboardFilterCreate,
    DashboardFilterResponse,
    DashboardFilterUpdate,
    DashboardLayoutUpdate,
    DashboardListResponse,
    DashboardResponse,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
    WidgetQueryResponse,
)
from app.services.analytics.engine import AnalyticsEngine
from app.services.analytics.schemas import (
    FilterCondition,
)


class DashboardService:
    """
    Enterprise analytical dashboard service orchestrating persistence, widget management,
    layout configuration, interactive filtering, and DuckDB analytical query execution.
    """

    # ---------------------------------------------------------------------------
    # Dashboard CRUD & Duplication
    # ---------------------------------------------------------------------------

    @classmethod
    async def create_dashboard(
        cls,
        workspace_id: uuid.UUID,
        creator_id: uuid.UUID,
        req: DashboardCreate,
        db: AsyncSession,
    ) -> DashboardDetailResponse:
        dashboard = Dashboard(
            workspace_id=workspace_id,
            created_by=creator_id,
            title=req.title.strip(),
            description=req.description.strip() if req.description else None,
            visibility=req.visibility,
            layout_config=req.layout_config or {},
            is_archived=False,
        )
        db.add(dashboard)
        await db.commit()
        await db.refresh(dashboard)

        return DashboardDetailResponse(
            id=dashboard.id,
            workspace_id=dashboard.workspace_id,
            created_by=dashboard.created_by,
            title=dashboard.title,
            description=dashboard.description,
            visibility=dashboard.visibility,
            is_archived=dashboard.is_archived,
            layout_config=dashboard.layout_config,
            created_at=dashboard.created_at,
            updated_at=dashboard.updated_at,
            widgets=[],
            filters=[],
        )

    @classmethod
    async def list_dashboards(
        cls,
        workspace_id: uuid.UUID,
        db: AsyncSession,
        search: str | None = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> DashboardListResponse:
        query = select(Dashboard).where(Dashboard.workspace_id == workspace_id)
        if not include_archived:
            query = query.where(Dashboard.is_archived.is_(False))

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                Dashboard.title.ilike(pattern) | Dashboard.description.ilike(pattern)
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Eager load counts
        stmt = (
            query.options(
                selectinload(Dashboard.widgets),
                selectinload(Dashboard.filters),
            )
            .order_by(desc(Dashboard.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        dashboards = result.scalars().all()

        items = [
            DashboardResponse(
                id=d.id,
                workspace_id=d.workspace_id,
                created_by=d.created_by,
                title=d.title,
                description=d.description,
                visibility=d.visibility,
                is_archived=d.is_archived,
                layout_config=d.layout_config,
                created_at=d.created_at,
                updated_at=d.updated_at,
                widget_count=len(d.widgets),
                filter_count=len(d.filters),
            )
            for d in dashboards
        ]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return DashboardListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def get_dashboard_entity(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Dashboard:
        stmt = (
            select(Dashboard)
            .options(
                selectinload(Dashboard.widgets),
                selectinload(Dashboard.filters),
            )
            .where(
                Dashboard.id == dashboard_id,
                Dashboard.workspace_id == workspace_id,
            )
        )
        res = await db.execute(stmt)
        dashboard = res.scalar_one_or_none()
        if not dashboard:
            raise DataLensException("Dashboard not found in this workspace.", code="NOT_FOUND")
        return dashboard

    @classmethod
    async def get_dashboard(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> DashboardDetailResponse:
        dashboard = await cls.get_dashboard_entity(dashboard_id, workspace_id, db)
        return DashboardDetailResponse(
            id=dashboard.id,
            workspace_id=dashboard.workspace_id,
            created_by=dashboard.created_by,
            title=dashboard.title,
            description=dashboard.description,
            visibility=dashboard.visibility,
            is_archived=dashboard.is_archived,
            layout_config=dashboard.layout_config,
            created_at=dashboard.created_at,
            updated_at=dashboard.updated_at,
            widgets=[DashboardWidgetResponse.model_validate(w) for w in dashboard.widgets],
            filters=[DashboardFilterResponse.model_validate(f) for f in dashboard.filters],
        )

    @classmethod
    async def update_dashboard(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: DashboardUpdate,
        db: AsyncSession,
    ) -> DashboardDetailResponse:
        dashboard = await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        if req.title is not None:
            dashboard.title = req.title.strip()
        if req.description is not None:
            dashboard.description = req.description.strip()
        if req.visibility is not None:
            dashboard.visibility = req.visibility
        if req.is_archived is not None:
            dashboard.is_archived = req.is_archived
        if req.layout_config is not None:
            dashboard.layout_config = req.layout_config

        await db.commit()
        await db.refresh(dashboard)
        return await cls.get_dashboard(dashboard_id, workspace_id, db)

    @classmethod
    async def duplicate_dashboard(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        creator_id: uuid.UUID,
        db: AsyncSession,
        target_workspace_id: uuid.UUID | None = None,
        new_title: str | None = None,
    ) -> DashboardDetailResponse:
        original = await cls.get_dashboard_entity(dashboard_id, workspace_id, db)
        target_ws = target_workspace_id or workspace_id
        title = new_title.strip() if new_title else f"{original.title} (Copy)"

        # Create cloned dashboard
        clone = Dashboard(
            workspace_id=target_ws,
            created_by=creator_id,
            title=title,
            description=original.description,
            visibility=original.visibility,
            layout_config=dict(original.layout_config or {}),
            is_archived=False,
        )
        db.add(clone)
        await db.flush()  # Obtain clone.id

        # Clone widgets
        for w in original.widgets:
            cloned_widget = DashboardWidget(
                dashboard_id=clone.id,
                dataset_id=w.dataset_id,
                dataset_version_id=w.dataset_version_id,
                widget_type=w.widget_type,
                title=w.title,
                description=w.description,
                grid_x=w.grid_x,
                grid_y=w.grid_y,
                grid_w=w.grid_w,
                grid_h=w.grid_h,
                query_config=dict(w.query_config or {}),
                display_settings=dict(w.display_settings or {}),
            )
            db.add(cloned_widget)

        # Clone filters
        for f in original.filters:
            cloned_filter = DashboardFilter(
                dashboard_id=clone.id,
                name=f.name,
                column_name=f.column_name,
                filter_type=f.filter_type,
                default_operator=f.default_operator,
                default_value=f.default_value,
                config=dict(f.config or {}),
            )
            db.add(cloned_filter)

        await db.commit()
        return await cls.get_dashboard(clone.id, target_ws, db)

    @classmethod
    async def delete_dashboard(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
        hard_delete: bool = False,
    ) -> None:
        dashboard = await cls.get_dashboard_entity(dashboard_id, workspace_id, db)
        if hard_delete:
            await db.delete(dashboard)
        else:
            dashboard.is_archived = True
        await db.commit()

    # ---------------------------------------------------------------------------
    # Widget Management
    # ---------------------------------------------------------------------------

    @classmethod
    async def validate_dataset_access(
        cls,
        dataset_id: uuid.UUID | None,
        dataset_version_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[Dataset | None, DatasetVersion | None]:
        if not dataset_id:
            return None, None

        stmt = select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.workspace_id == workspace_id,
            Dataset.is_archived.is_(False),
        )
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise DataLensException(
                "Referenced dataset does not exist or does not belong to this workspace.",
                code="FORBIDDEN_DATASET_ACCESS",
            )

        target_version_id = dataset_version_id or dataset.current_version_id
        version = None
        if target_version_id:
            ver_stmt = select(DatasetVersion).where(
                DatasetVersion.id == target_version_id,
                DatasetVersion.dataset_id == dataset.id,
            )
            version = (await db.execute(ver_stmt)).scalar_one_or_none()
            if not version:
                raise DataLensException("Specified dataset version does not exist.", code="NOT_FOUND")

        return dataset, version

    @classmethod
    async def add_widget(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: DashboardWidgetCreate,
        db: AsyncSession,
    ) -> DashboardWidgetResponse:
        # Verify dashboard belongs to workspace
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        # Verify dataset isolation
        dataset, version = await cls.validate_dataset_access(
            req.dataset_id, req.dataset_version_id, workspace_id, db
        )

        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            dataset_id=dataset.id if dataset else None,
            dataset_version_id=version.id if version else None,
            widget_type=req.widget_type,
            title=req.title.strip(),
            description=req.description.strip() if req.description else None,
            grid_x=req.grid_x,
            grid_y=req.grid_y,
            grid_w=req.grid_w,
            grid_h=req.grid_h,
            query_config=req.query_config or {},
            display_settings=req.display_settings or {},
        )
        db.add(widget)
        await db.commit()
        await db.refresh(widget)
        return DashboardWidgetResponse.model_validate(widget)

    @classmethod
    async def update_widget(
        cls,
        dashboard_id: uuid.UUID,
        widget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: DashboardWidgetUpdate,
        db: AsyncSession,
    ) -> DashboardWidgetResponse:
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        stmt = select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
        widget = (await db.execute(stmt)).scalar_one_or_none()
        if not widget:
            raise DataLensException("Widget not found in dashboard.", code="NOT_FOUND")

        if req.dataset_id is not None:
            dataset, version = await cls.validate_dataset_access(
                req.dataset_id, req.dataset_version_id, workspace_id, db
            )
            widget.dataset_id = dataset.id if dataset else None
            widget.dataset_version_id = version.id if version else None
        elif req.dataset_version_id is not None:
            dataset, version = await cls.validate_dataset_access(
                widget.dataset_id, req.dataset_version_id, workspace_id, db
            )
            widget.dataset_version_id = version.id if version else None

        if req.title is not None:
            widget.title = req.title.strip()
        if req.description is not None:
            widget.description = req.description.strip()
        if req.grid_x is not None:
            widget.grid_x = req.grid_x
        if req.grid_y is not None:
            widget.grid_y = req.grid_y
        if req.grid_w is not None:
            widget.grid_w = req.grid_w
        if req.grid_h is not None:
            widget.grid_h = req.grid_h
        if req.query_config is not None:
            widget.query_config = req.query_config
        if req.display_settings is not None:
            widget.display_settings = req.display_settings

        await db.commit()
        await db.refresh(widget)
        return DashboardWidgetResponse.model_validate(widget)

    @classmethod
    async def delete_widget(
        cls,
        dashboard_id: uuid.UUID,
        widget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        stmt = select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
        widget = (await db.execute(stmt)).scalar_one_or_none()
        if not widget:
            raise DataLensException("Widget not found in dashboard.", code="NOT_FOUND")

        await db.delete(widget)
        await db.commit()

    @classmethod
    async def update_layout(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: DashboardLayoutUpdate,
        db: AsyncSession,
    ) -> list[DashboardWidgetResponse]:
        dashboard = await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        layout_map = {item.id: item for item in req.widgets}
        for w in dashboard.widgets:
            if w.id in layout_map:
                item = layout_map[w.id]
                w.grid_x = item.grid_x
                w.grid_y = item.grid_y
                w.grid_w = item.grid_w
                w.grid_h = item.grid_h

        await db.commit()
        await db.refresh(dashboard)
        return [DashboardWidgetResponse.model_validate(w) for w in dashboard.widgets]

    # ---------------------------------------------------------------------------
    # Filter Management
    # ---------------------------------------------------------------------------

    @classmethod
    async def add_filter(
        cls,
        dashboard_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: DashboardFilterCreate,
        db: AsyncSession,
    ) -> DashboardFilterResponse:
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        d_filter = DashboardFilter(
            dashboard_id=dashboard_id,
            name=req.name.strip(),
            column_name=req.column_name.strip(),
            filter_type=req.filter_type,
            default_operator=req.default_operator,
            default_value=req.default_value,
            config=req.config or {},
        )
        db.add(d_filter)
        await db.commit()
        await db.refresh(d_filter)
        return DashboardFilterResponse.model_validate(d_filter)

    @classmethod
    async def update_filter(
        cls,
        dashboard_id: uuid.UUID,
        filter_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: DashboardFilterUpdate,
        db: AsyncSession,
    ) -> DashboardFilterResponse:
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        stmt = select(DashboardFilter).where(
            DashboardFilter.id == filter_id,
            DashboardFilter.dashboard_id == dashboard_id,
        )
        d_filter = (await db.execute(stmt)).scalar_one_or_none()
        if not d_filter:
            raise DataLensException("Filter not found in dashboard.", code="NOT_FOUND")

        if req.name is not None:
            d_filter.name = req.name.strip()
        if req.column_name is not None:
            d_filter.column_name = req.column_name.strip()
        if req.filter_type is not None:
            d_filter.filter_type = req.filter_type
        if req.default_operator is not None:
            d_filter.default_operator = req.default_operator
        if req.default_value is not None:
            d_filter.default_value = req.default_value
        if req.config is not None:
            d_filter.config = req.config

        await db.commit()
        await db.refresh(d_filter)
        return DashboardFilterResponse.model_validate(d_filter)

    @classmethod
    async def delete_filter(
        cls,
        dashboard_id: uuid.UUID,
        filter_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        stmt = select(DashboardFilter).where(
            DashboardFilter.id == filter_id,
            DashboardFilter.dashboard_id == dashboard_id,
        )
        d_filter = (await db.execute(stmt)).scalar_one_or_none()
        if not d_filter:
            raise DataLensException("Filter not found in dashboard.", code="NOT_FOUND")

        await db.delete(d_filter)
        await db.commit()

    # ---------------------------------------------------------------------------
    # Analytics & Query Execution Engine (Stage 3)
    # ---------------------------------------------------------------------------

    @classmethod
    async def _resolve_parquet_files(
        cls,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[Dataset, DatasetVersion, list[Path]]:
        dataset, version = await cls.validate_dataset_access(
            dataset_id, version_id, workspace_id, db
        )
        if not dataset or not version:
            raise DataLensException("Dataset or version missing.", code="NOT_FOUND")

        storage_root = Path(settings.STORAGE_ROOT).resolve()
        manifest_path = storage_root / version.storage_key
        if not manifest_path.is_file():
            raise DataLensException("Dataset storage manifest not found on disk.", code="STORAGE_NOT_FOUND")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parquet_paths = [storage_root / p for p in manifest.get("parts", [])]
        return dataset, version, parquet_paths

    @classmethod
    async def execute_widget_query(
        cls,
        dashboard_id: uuid.UUID,
        widget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        override_filters: list[FilterCondition] | None = None,
        drill_level: int | None = None,
        drill_filters: list[FilterCondition] | None = None,
        compare_to: str | None = None,
        target_value: float | None = None,
        db: AsyncSession = None,
    ) -> WidgetQueryResponse:
        start_time = time.perf_counter()

        # Validate dashboard
        await cls.get_dashboard_entity(dashboard_id, workspace_id, db)

        # Retrieve widget
        stmt = select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
        widget = (await db.execute(stmt)).scalar_one_or_none()
        if not widget:
            raise DataLensException("Widget not found.", code="NOT_FOUND")

        # 1. Handle Text / Insight widget
        if widget.widget_type == "text":
            text_content = widget.query_config.get("text_content", "")
            return WidgetQueryResponse(
                widget_id=widget.id,
                widget_type="text",
                data={"content": text_content},
                row_count=1,
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                dataset_version_id=None,
                dataset_id=None,
            )

        if not widget.dataset_id:
            return WidgetQueryResponse(
                widget_id=widget.id,
                widget_type=widget.widget_type,
                data={"items": [], "message": "No dataset connected to widget."},
                row_count=0,
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                dataset_version_id=None,
                dataset_id=None,
            )

        # 2. Resolve dataset and Parquet parts
        dataset, version, parquet_paths = await cls._resolve_parquet_files(
            widget.dataset_id, widget.dataset_version_id, workspace_id, db
        )

        # 3. Combine widget-saved filters with runtime dashboard-level override filters & drill filters
        saved_raw_filters = widget.query_config.get("filters", [])
        combined_filters: list[FilterCondition] = []

        for f in saved_raw_filters:
            if isinstance(f, dict):
                combined_filters.append(FilterCondition(**f))
            elif isinstance(f, FilterCondition):
                combined_filters.append(f)

        if override_filters:
            combined_filters.extend(override_filters)

        if drill_filters:
            combined_filters.extend(drill_filters)

        q_cfg = widget.query_config or {}
        w_type = widget.widget_type.lower()
        result_data: Any = None
        row_count = 0

        # Resolve hierarchy level for drill-down
        hierarchy_levels = q_cfg.get("hierarchy_levels", [])
        active_group_col = q_cfg.get("group_by_column")
        current_drill_depth = 0
        if hierarchy_levels and isinstance(hierarchy_levels, list) and len(hierarchy_levels) > 0:
            if drill_level is not None and 0 <= drill_level < len(hierarchy_levels):
                active_group_col = hierarchy_levels[drill_level]
                current_drill_depth = drill_level
            else:
                active_group_col = hierarchy_levels[0]
                current_drill_depth = 0

        source_sql = AnalyticsEngine._get_parquet_source_sql(parquet_paths)

        # 4. Route by Widget Type to deterministic DuckDB analytics

        # -------------------------------------------------------------------
        # A. KPI & Comparison
        # -------------------------------------------------------------------
        if w_type in ("kpi", "gauge"):
            metric_col = q_cfg.get("metric_column")
            agg = q_cfg.get("aggregation", "sum").lower()

            params: list[Any] = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)

            if metric_col and metric_col != "*":
                m_safe = AnalyticsEngine._sanitize_identifier(metric_col)
                if agg in ("sum", "total"):
                    agg_sql = f"ROUND(COALESCE(SUM({m_safe}), 0), 2)"
                elif agg in ("avg", "average", "mean"):
                    agg_sql = f"ROUND(COALESCE(AVG({m_safe}), 0), 2)"
                elif agg == "min":
                    agg_sql = f"ROUND(COALESCE(MIN({m_safe}), 0), 2)"
                elif agg == "max":
                    agg_sql = f"ROUND(COALESCE(MAX({m_safe}), 0), 2)"
                elif agg in ("distinct_count", "unique_count"):
                    agg_sql = f"COUNT(DISTINCT {m_safe})"
                else:
                    agg_sql = f"COUNT({m_safe})"
            else:
                agg_sql = "COUNT(*)"

            kpi_query = f"SELECT {agg_sql} FROM {source_sql}{where_sql}"
            con = duckdb.connect(":memory:")
            try:
                raw_val = con.execute(kpi_query, params).fetchone()[0]
                primary_value = float(raw_val) if raw_val is not None else 0.0
            finally:
                con.close()

            row_count = 1

            # Comparative Analytics (Target / Baseline)
            comp_mode = compare_to or q_cfg.get("compare_to") or "target"
            t_val = target_value if target_value is not None else q_cfg.get("target_value")
            comparison_info = None

            if t_val is not None:
                target_f = float(t_val)
                diff = round(primary_value - target_f, 2)
                pct_change = round((diff / target_f) * 100, 2) if target_f != 0 else (100.0 if primary_value > 0 else 0.0)
                direction = "up" if diff > 0 else ("down" if diff < 0 else "flat")
                comparison_info = {
                    "type": comp_mode,
                    "target": target_f,
                    "diff": diff,
                    "pct_change": pct_change,
                    "direction": direction,
                }

            if w_type == "gauge":
                target_f = float(t_val) if t_val is not None else 100.0
                min_f = float(q_cfg.get("min_value", 0.0))
                max_f = float(q_cfg.get("max_value", max(target_f * 1.25, 100.0)))
                pct_of_target = round((primary_value / target_f) * 100, 1) if target_f > 0 else 100.0
                result_data = {
                    "value": primary_value,
                    "target": target_f,
                    "min": min_f,
                    "max": max_f,
                    "percent_of_target": pct_of_target,
                    "metric": metric_col or "Count",
                    "formatted_value": f"{primary_value:,.2f}",
                }
            else:
                result_data = {
                    "value": primary_value,
                    "metric": metric_col or "Count",
                    "aggregation": agg,
                    "formatted_value": f"{primary_value:,.2f}" if isinstance(primary_value, (int, float)) else str(primary_value),
                    "comparison": comparison_info,
                }

        # -------------------------------------------------------------------
        # B. Bar Charts & Top-N
        # -------------------------------------------------------------------
        elif w_type in ("bar", "horizontal_bar", "top_n", "pie", "donut"):
            group_col = active_group_col
            metric_col = q_cfg.get("metric_column")
            agg = q_cfg.get("aggregation", "sum")
            limit = int(q_cfg.get("limit", 15 if w_type != "top_n" else 5))
            sort_dir = q_cfg.get("sort_direction", "desc")

            if not group_col:
                raise DataLensException(
                    f"Widget '{widget.title}' requires a group_by_column in query_config.",
                    code="INVALID_QUERY_CONFIG",
                )

            agg_res = AnalyticsEngine.compute_aggregation(
                parquet_files=parquet_paths,
                group_by_columns=[group_col],
                metric_column=metric_col,
                aggregation=agg if metric_col else "count",
                sort_order=sort_dir,
                limit=limit,
                filters=combined_filters,
                version_id=str(version.id),
            )
            items = [{"label": str(item.key or "Unknown"), "value": item.value} for item in agg_res.items]
            row_count = len(items)
            result_data = {
                "categories": [i["label"] for i in items],
                "values": [i["value"] for i in items],
                "items": items,
                "metric": metric_col or "Count",
                "group_by": group_col,
                "total": agg_res.total,
                "orientation": "horizontal" if w_type == "horizontal_bar" else "vertical",
            }

        # -------------------------------------------------------------------
        # C. Multi-Series Bar Charts (Stacked, Grouped, 100% Percent Stacked)
        # -------------------------------------------------------------------
        elif w_type in ("stacked_bar", "grouped_bar", "percent_bar"):
            group_col = active_group_col
            stack_col = q_cfg.get("sub_group_by_column") or q_cfg.get("stack_column")
            metric_col = q_cfg.get("metric_column")
            agg = q_cfg.get("aggregation", "sum").lower()
            limit = int(q_cfg.get("limit", 20))

            if not group_col or not stack_col:
                raise DataLensException(
                    f"Widget '{widget.title}' requires both group_by_column and sub_group_by_column.",
                    code="INVALID_QUERY_CONFIG",
                )

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)
            g_safe = AnalyticsEngine._sanitize_identifier(group_col)
            s_safe = AnalyticsEngine._sanitize_identifier(stack_col)

            if metric_col and metric_col != "*":
                m_safe = AnalyticsEngine._sanitize_identifier(metric_col)
                agg_func = "SUM" if agg == "sum" else ("AVG" if agg in ("avg", "average") else "COUNT")
                metric_expr = f"ROUND({agg_func}({m_safe}), 2)"
            else:
                metric_expr = "COUNT(*)"

            query = f"""
            SELECT {g_safe} as cat, {s_safe} as series_name, {metric_expr} as val
            FROM {source_sql}{where_sql}
            GROUP BY 1, 2
            ORDER BY 1, 2
            LIMIT 500
            """
            con = duckdb.connect(":memory:")
            try:
                rows = con.execute(query, params).fetchall()
            finally:
                con.close()

            # Pivot rows into { categories: [...], series: [{ name, values }] }
            unique_cats = sorted(list(set(str(r[0]) for r in rows if r[0] is not None)))[:limit]
            unique_series = sorted(list(set(str(r[1]) for r in rows if r[1] is not None)))

            val_map: dict[tuple[str, str], float] = {(str(r[0]), str(r[1])): float(r[2] or 0) for r in rows}

            series_list = []
            for s_name in unique_series:
                vals = [val_map.get((c, s_name), 0.0) for c in unique_cats]
                series_list.append({"name": s_name, "values": vals})

            # For percent_bar: normalize each category to 100%
            if w_type == "percent_bar":
                for c_idx in range(len(unique_cats)):
                    cat_total = sum(s["values"][c_idx] for s in series_list)
                    if cat_total > 0:
                        for s in series_list:
                            s["values"][c_idx] = round((s["values"][c_idx] / cat_total) * 100, 1)

            row_count = len(unique_cats)
            result_data = {
                "categories": unique_cats,
                "series": series_list,
                "group_by": group_col,
                "sub_group_by": stack_col,
                "is_percent": w_type == "percent_bar",
                "is_stacked": w_type in ("stacked_bar", "percent_bar"),
            }

        # -------------------------------------------------------------------
        # D. Time-Series Trends (Line, Area, Multi-Line, Stacked Area, Combo)
        # -------------------------------------------------------------------
        elif w_type in ("line", "area", "multi_line", "stacked_area", "combo"):
            time_col = q_cfg.get("time_column")
            metric_col = q_cfg.get("metric_column")
            granularity = q_cfg.get("granularity", "month")
            agg = q_cfg.get("aggregation", "sum")
            series_col = q_cfg.get("series_column") or q_cfg.get("sub_group_by_column")

            if not time_col:
                raise DataLensException(
                    f"Widget '{widget.title}' requires a time_column in query_config.",
                    code="INVALID_QUERY_CONFIG",
                )

            if w_type in ("multi_line", "stacked_area", "combo") and series_col:
                # Grouped series over time
                params = []
                where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)
                t_safe = AnalyticsEngine._sanitize_identifier(time_col)
                s_safe = AnalyticsEngine._sanitize_identifier(series_col)
                m_safe = AnalyticsEngine._sanitize_identifier(metric_col) if metric_col else "*"
                agg_func = "SUM" if agg == "sum" else ("AVG" if agg in ("avg", "average") else "COUNT")

                query = f"""
                SELECT date_trunc('{granularity}', {t_safe}) as dt, {s_safe} as s_name, {agg_func}({m_safe}) as val
                FROM {source_sql}{where_sql}
                GROUP BY 1, 2
                ORDER BY 1, 2
                LIMIT 500
                """
                con = duckdb.connect(":memory:")
                try:
                    rows = con.execute(query, params).fetchall()
                finally:
                    con.close()

                date_labels = sorted(list(set(str(r[0])[:10] for r in rows if r[0] is not None)))
                s_names = sorted(list(set(str(r[1]) for r in rows if r[1] is not None)))
                val_map = {(str(r[0])[:10], str(r[1])): float(r[2] or 0) for r in rows}

                series_list = []
                for sn in s_names:
                    s_vals = [val_map.get((d, sn), 0.0) for d in date_labels]
                    series_list.append({"name": sn, "values": s_vals})

                row_count = len(date_labels)
                result_data = {
                    "labels": date_labels,
                    "series": series_list,
                    "granularity": granularity,
                    "metric": metric_col or "Count",
                }
            else:
                ts_res = AnalyticsEngine.compute_time_series(
                    parquet_files=parquet_paths,
                    date_column=time_col,
                    value_column=metric_col or time_col,
                    interval=granularity,
                    aggregation=agg,
                    filters=combined_filters,
                    version_id=str(version.id),
                )
                items = [{"timestamp": pt.timestamp, "value": pt.value} for pt in ts_res.points]
                row_count = len(items)
                result_data = {
                    "labels": [i["timestamp"] for i in items],
                    "values": [i["value"] for i in items],
                    "points": items,
                    "granularity": granularity,
                    "metric": metric_col or "Count",
                }

        # -------------------------------------------------------------------
        # E. Statistical Visualizations (Heatmap, Histogram, Box Plot, Correlation)
        # -------------------------------------------------------------------
        elif w_type == "heatmap":
            x_col = q_cfg.get("x_column") or active_group_col
            y_col = q_cfg.get("y_column") or q_cfg.get("sub_group_by_column")
            metric_col = q_cfg.get("metric_column")
            agg = q_cfg.get("aggregation", "count").lower()

            if not x_col or not y_col:
                raise DataLensException("Heatmap requires both x_column and y_column in query_config.", code="INVALID_QUERY_CONFIG")

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)
            x_safe = AnalyticsEngine._sanitize_identifier(x_col)
            y_safe = AnalyticsEngine._sanitize_identifier(y_col)
            m_expr = f"ROUND(AVG({AnalyticsEngine._sanitize_identifier(metric_col)}), 2)" if metric_col else "COUNT(*)"

            query = f"""
            SELECT {x_safe} as x_val, {y_safe} as y_val, {m_expr} as val
            FROM {source_sql}{where_sql}
            GROUP BY 1, 2
            LIMIT 500
            """
            con = duckdb.connect(":memory:")
            try:
                rows = con.execute(query, params).fetchall()
            finally:
                con.close()

            x_cats = sorted(list(set(str(r[0]) for r in rows if r[0] is not None)))[:20]
            y_cats = sorted(list(set(str(r[1]) for r in rows if r[1] is not None)))[:20]
            val_map = {(str(r[0]), str(r[1])): float(r[2] or 0) for r in rows}

            matrix = []
            all_vals = []
            for y in y_cats:
                row_vals = []
                for x in x_cats:
                    v = val_map.get((x, y), 0.0)
                    row_vals.append(v)
                    all_vals.append(v)
                matrix.append(row_vals)

            row_count = len(matrix)
            result_data = {
                "x_categories": x_cats,
                "y_categories": y_cats,
                "matrix": matrix,
                "min_value": min(all_vals) if all_vals else 0,
                "max_value": max(all_vals) if all_vals else 1,
            }

        elif w_type == "histogram":
            metric_col = q_cfg.get("metric_column")
            bins_count = int(q_cfg.get("bins", 10))
            if not metric_col:
                raise DataLensException("Histogram requires a metric_column.", code="INVALID_QUERY_CONFIG")

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)
            m_safe = AnalyticsEngine._sanitize_identifier(metric_col)

            con = duckdb.connect(":memory:")
            try:
                min_max = con.execute(f"SELECT MIN({m_safe}), MAX({m_safe}) FROM {source_sql}{where_sql}", params).fetchone()
                min_val = float(min_max[0] or 0.0)
                max_val = float(min_max[1] or 1.0)
                span = max_val - min_val
                bin_width = max(span / bins_count, 0.01)

                bin_query = f"""
                SELECT CAST(FLOOR(({m_safe} - {min_val}) / {bin_width}) AS INTEGER) as bin_idx, COUNT(*) as cnt
                FROM {source_sql}{where_sql}
                GROUP BY 1
                ORDER BY 1
                """
                bin_rows = con.execute(bin_query, params).fetchall()
            finally:
                con.close()

            bin_dict = {int(r[0]): int(r[1]) for r in bin_rows if r[0] is not None}
            bins_result = []
            for i in range(bins_count):
                b_min = round(min_val + i * bin_width, 2)
                b_max = round(b_min + bin_width, 2)
                bins_result.append({
                    "label": f"{b_min} - {b_max}",
                    "min": b_min,
                    "max": b_max,
                    "count": bin_dict.get(i, 0),
                })

            row_count = len(bins_result)
            result_data = {
                "bins": bins_result,
                "bin_width": round(bin_width, 2),
                "metric": metric_col,
            }

        elif w_type == "box_plot":
            metric_col = q_cfg.get("metric_column")
            group_col = active_group_col
            if not metric_col:
                raise DataLensException("Box plot requires a metric_column.", code="INVALID_QUERY_CONFIG")

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)
            m_safe = AnalyticsEngine._sanitize_identifier(metric_col)

            if group_col:
                g_safe = AnalyticsEngine._sanitize_identifier(group_col)
                query = f"""
                SELECT {g_safe},
                       MIN({m_safe}),
                       QUANTILE_CONT({m_safe}, 0.25),
                       MEDIAN({m_safe}),
                       QUANTILE_CONT({m_safe}, 0.75),
                       MAX({m_safe}),
                       COUNT(*)
                FROM {source_sql}{where_sql}
                GROUP BY 1
                ORDER BY 7 DESC
                LIMIT 15
                """
            else:
                query = f"""
                SELECT 'Overall',
                       MIN({m_safe}),
                       QUANTILE_CONT({m_safe}, 0.25),
                       MEDIAN({m_safe}),
                       QUANTILE_CONT({m_safe}, 0.75),
                       MAX({m_safe}),
                       COUNT(*)
                FROM {source_sql}{where_sql}
                """

            con = duckdb.connect(":memory:")
            try:
                rows = con.execute(query, params).fetchall()
            finally:
                con.close()

            items = [
                {
                    "label": str(r[0] or "Unknown"),
                    "min": round(float(r[1] or 0), 2),
                    "q1": round(float(r[2] or 0), 2),
                    "median": round(float(r[3] or 0), 2),
                    "q3": round(float(r[4] or 0), 2),
                    "max": round(float(r[5] or 0), 2),
                    "count": int(r[6] or 0),
                }
                for r in rows
            ]
            row_count = len(items)
            result_data = {"items": items, "metric": metric_col}

        elif w_type == "correlation":
            cols = q_cfg.get("columns", [])
            if not cols or len(cols) < 2:
                # Fallback to inspecting numerical columns in dataset
                num_cols = [c["name"] for c in version.schema_metadata.get("columns", []) if c.get("inferred_type") in ("integer", "float")][:5]
                cols = num_cols if len(num_cols) >= 2 else ["price", "quantity"]

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)

            con = duckdb.connect(":memory:")
            matrix = []
            try:
                for c1 in cols:
                    row_corr = []
                    for c2 in cols:
                        if c1 == c2:
                            row_corr.append(1.0)
                        else:
                            c1_safe = AnalyticsEngine._sanitize_identifier(c1)
                            c2_safe = AnalyticsEngine._sanitize_identifier(c2)
                            q = f"SELECT ROUND(CORR({c1_safe}, {c2_safe}), 3) FROM {source_sql}{where_sql}"
                            val = con.execute(q, params).fetchone()[0]
                            row_corr.append(float(val) if val is not None else 0.0)
                    matrix.append(row_corr)
            finally:
                con.close()

            row_count = len(matrix)
            result_data = {"columns": cols, "matrix": matrix}

        # -------------------------------------------------------------------
        # F. Business Visualizations (Treemap, Waterfall, Funnel, Pareto)
        # -------------------------------------------------------------------
        elif w_type in ("treemap", "waterfall", "funnel", "pareto"):
            group_col = active_group_col
            metric_col = q_cfg.get("metric_column")
            agg = q_cfg.get("aggregation", "sum").lower()
            limit = int(q_cfg.get("limit", 15))

            if not group_col:
                raise DataLensException(f"Widget '{widget.title}' requires a group_by_column.", code="INVALID_QUERY_CONFIG")

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)
            g_safe = AnalyticsEngine._sanitize_identifier(group_col)
            m_expr = f"ROUND(SUM({AnalyticsEngine._sanitize_identifier(metric_col)}), 2)" if metric_col else "COUNT(*)"

            if w_type == "pareto":
                query = f"""
                SELECT {g_safe} as cat,
                       {m_expr} as val,
                       ROUND(SUM({m_expr}) OVER (ORDER BY {m_expr} DESC) / NULLIF(SUM({m_expr}) OVER (), 0) * 100, 2) as cum_pct
                FROM {source_sql}{where_sql}
                GROUP BY 1
                ORDER BY val DESC
                LIMIT {limit}
                """
                con = duckdb.connect(":memory:")
                try:
                    rows = con.execute(query, params).fetchall()
                finally:
                    con.close()

                items = [
                    {"label": str(r[0] or "Unknown"), "value": float(r[1] or 0), "cumulative_pct": float(r[2] or 0)}
                    for r in rows
                ]
                row_count = len(items)
                result_data = {"items": items, "metric": metric_col or "Count"}

            elif w_type == "funnel":
                query = f"""
                SELECT {g_safe} as stage, {m_expr} as val
                FROM {source_sql}{where_sql}
                GROUP BY 1
                ORDER BY val DESC
                LIMIT {limit}
                """
                con = duckdb.connect(":memory:")
                try:
                    rows = con.execute(query, params).fetchall()
                finally:
                    con.close()

                top_val = float(rows[0][1]) if rows and rows[0][1] else 1.0
                stages = []
                for idx, r in enumerate(rows):
                    v = float(r[1] or 0)
                    prev_v = float(rows[idx - 1][1] or 0) if idx > 0 else v
                    conv_rate = round((v / top_val) * 100, 1) if top_val > 0 else 100.0
                    drop_rate = round(((prev_v - v) / prev_v) * 100, 1) if prev_v > 0 and idx > 0 else 0.0
                    stages.append({
                        "name": str(r[0] or f"Stage {idx + 1}"),
                        "value": v,
                        "conversion_rate": conv_rate,
                        "drop_off_rate": drop_rate,
                    })
                row_count = len(stages)
                result_data = {"stages": stages, "metric": metric_col or "Count"}

            elif w_type == "waterfall":
                query = f"""
                SELECT {g_safe} as label, {m_expr} as val
                FROM {source_sql}{where_sql}
                GROUP BY 1
                LIMIT {limit}
                """
                con = duckdb.connect(":memory:")
                try:
                    rows = con.execute(query, params).fetchall()
                finally:
                    con.close()

                running_total = 0.0
                steps = []
                for r in rows:
                    val = float(r[1] or 0)
                    running_total += val
                    steps.append({
                        "label": str(r[0] or "Item"),
                        "value": val,
                        "running_total": round(running_total, 2),
                        "type": "increase" if val >= 0 else "decrease",
                    })
                row_count = len(steps)
                result_data = {"items": steps, "total": round(running_total, 2)}

            else:  # treemap
                query = f"""
                SELECT {g_safe} as name, {m_expr} as val
                FROM {source_sql}{where_sql}
                GROUP BY 1
                ORDER BY val DESC
                LIMIT {limit}
                """
                con = duckdb.connect(":memory:")
                try:
                    rows = con.execute(query, params).fetchall()
                finally:
                    con.close()

                total_sum = sum(float(r[1] or 0) for r in rows) or 1.0
                nodes = [
                    {
                        "name": str(r[0] or "Unknown"),
                        "value": float(r[1] or 0),
                        "percent": round((float(r[1] or 0) / total_sum) * 100, 1),
                    }
                    for r in rows
                ]
                row_count = len(nodes)
                result_data = {"nodes": nodes, "total": round(total_sum, 2)}

        # -------------------------------------------------------------------
        # G. Scatter Plot & Table
        # -------------------------------------------------------------------
        elif w_type == "scatter":
            x_col = q_cfg.get("x_column")
            y_col = q_cfg.get("y_column")
            label_col = q_cfg.get("label_column")
            limit = int(q_cfg.get("limit", 200))

            if not x_col or not y_col:
                raise DataLensException(
                    f"Scatter plot widget '{widget.title}' requires both x_column and y_column.",
                    code="INVALID_QUERY_CONFIG",
                )

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)

            x_safe = AnalyticsEngine._sanitize_identifier(x_col)
            y_safe = AnalyticsEngine._sanitize_identifier(y_col)
            lbl_safe = AnalyticsEngine._sanitize_identifier(label_col) if label_col else None

            cols_select = f"{x_safe} AS x, {y_safe} AS y"
            if lbl_safe:
                cols_select += f", {lbl_safe} AS label"

            extra_null_filter = f"{x_safe} IS NOT NULL AND {y_safe} IS NOT NULL"
            full_where = f"{where_sql} AND {extra_null_filter}" if where_sql else f" WHERE {extra_null_filter}"

            query_sql = f"SELECT {cols_select} FROM {source_sql}{full_where} LIMIT {limit}"

            con = duckdb.connect(":memory:")
            try:
                cur = con.execute(query_sql, params)
                rows = cur.fetchall()
                points = []
                for r in rows:
                    pt = {"x": r[0], "y": r[1]}
                    if lbl_safe:
                        pt["label"] = str(r[2])
                    points.append(pt)
                row_count = len(points)
                result_data = {
                    "points": points,
                    "x_axis": x_col,
                    "y_axis": y_col,
                }
            finally:
                con.close()

        elif w_type == "table":
            columns = q_cfg.get("columns", [])
            limit = int(q_cfg.get("limit", 50))
            sort_col = q_cfg.get("sort_column")
            sort_dir = q_cfg.get("sort_direction", "asc")

            params = []
            where_sql = AnalyticsEngine._build_where_clause(combined_filters, params)

            safe_cols = ", ".join([AnalyticsEngine._sanitize_identifier(c) for c in columns]) if columns else "*"
            order_sql = ""
            if sort_col:
                safe_sort = AnalyticsEngine._sanitize_identifier(sort_col)
                dir_sql = "DESC" if sort_dir.lower() == "desc" else "ASC"
                order_sql = f" ORDER BY {safe_sort} {dir_sql}"

            query_sql = f"SELECT {safe_cols} FROM {source_sql}{where_sql}{order_sql} LIMIT {limit}"

            con = duckdb.connect(":memory:")
            try:
                cur = con.execute(query_sql, params)
                desc_cols = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                table_rows = [dict(zip(desc_cols, r, strict=False)) for r in rows]
                row_count = len(table_rows)
                result_data = {
                    "columns": desc_cols,
                    "rows": table_rows,
                    "total_returned": row_count,
                }
            finally:
                con.close()
        else:
            raise DataLensException(f"Unsupported widget type '{widget.widget_type}'.", code="INVALID_WIDGET_TYPE")

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return WidgetQueryResponse(
            widget_id=widget.id,
            widget_type=widget.widget_type,
            data=result_data,
            row_count=row_count,
            execution_time_ms=elapsed_ms,
            dataset_version_id=version.id,
            dataset_id=dataset.id,
            metadata={
                "dataset_name": dataset.name,
                "version_number": version.version_number,
                "applied_filters_count": len(combined_filters),
                "current_drill_depth": current_drill_depth,
                "hierarchy_levels": hierarchy_levels,
            },
        )
