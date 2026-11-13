"""Data Transformation Service for DataLens.

Coordinates pipeline definitions, step execution using DuckDB,
preview generation, and derived dataset materialization with full lineage.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.transformation import (
    TransformationPipeline,
    TransformationRun,
    TransformationStep,
)
from app.schemas.transformation import (
    PreviewColumn,
    PreviewResponse,
    TransformationPipelineCreate,
    TransformationPipelineSummary,
    TransformationPipelineUpdate,
    TransformationStepCreate,
    TransformationStepUpdate,
    ValidateFormulaResponse,
)
from app.services.transformation.formula_engine import FormulaEngine, FormulaError

logger = logging.getLogger(__name__)


class TransformationService:
    @staticmethod
    def _sanitize_ident(name: str) -> str:
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    @classmethod
    def _map_duckdb_type(cls, type_str: str) -> str:
        t = type_str.upper()
        if any(k in t for k in ("INT", "LONG", "SHORT", "BYTE")):
            return "integer"
        elif any(k in t for k in ("FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL")):
            return "float"
        elif "BOOL" in t:
            return "boolean"
        elif "DATE" in t and "TIME" not in t:
            return "date"
        elif any(k in t for k in ("TIME", "TIMESTAMP")):
            return "datetime"
        return "string"

    # -----------------------------------------------------------------------
    # Workspace & Dataset Resolution
    # -----------------------------------------------------------------------

    @classmethod
    async def _resolve_dataset(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[Dataset, DatasetVersion, list[Path], list[dict[str, Any]]]:
        stmt = (
            select(Dataset)
            .options(selectinload(Dataset.current_version))
            .where(
                Dataset.id == dataset_id,
                Dataset.workspace_id == workspace_id,
                Dataset.is_archived.is_(False),
            )
        )
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset or not dataset.current_version:
            raise DataLensException(f"Dataset {dataset_id} not found or has no active version.", code="NOT_FOUND")

        version = dataset.current_version
        storage_root = Path(settings.STORAGE_ROOT).resolve()
        manifest_path = storage_root / version.storage_key
        if not manifest_path.is_file():
            raise DataLensException(f"Dataset {dataset_id} manifest missing on disk.", code="STORAGE_NOT_FOUND")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parquet_paths = [storage_root / p for p in manifest.get("parts", [])]
        columns_meta = manifest.get("columns", [])
        return dataset, version, parquet_paths, columns_meta

    # -----------------------------------------------------------------------
    # Pipeline CRUD
    # -----------------------------------------------------------------------

    @classmethod
    async def create_pipeline(
        cls,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: TransformationPipelineCreate,
        db: AsyncSession,
    ) -> TransformationPipeline:
        pipeline = TransformationPipeline(
            workspace_id=workspace_id,
            created_by=user_id,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            source_dataset_ids=data.source_dataset_ids,
            status=data.status,
        )
        db.add(pipeline)
        await db.commit()
        return await cls.get_pipeline(pipeline.id, workspace_id, db)

    @classmethod
    async def list_pipelines(
        cls,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[TransformationPipelineSummary]:
        stmt = (
            select(TransformationPipeline)
            .options(
                selectinload(TransformationPipeline.steps),
                selectinload(TransformationPipeline.runs),
            )
            .where(TransformationPipeline.workspace_id == workspace_id)
            .order_by(desc(TransformationPipeline.created_at))
        )
        res = await db.execute(stmt)
        pipelines = res.scalars().all()

        summaries: list[TransformationPipelineSummary] = []
        for p in pipelines:
            last_run = p.runs[0] if p.runs else None
            summaries.append(
                TransformationPipelineSummary(
                    id=p.id,
                    workspace_id=p.workspace_id,
                    created_by=p.created_by,
                    name=p.name,
                    description=p.description,
                    source_dataset_ids=p.source_dataset_ids,
                    status=p.status,
                    step_count=len(p.steps),
                    last_run_status=last_run.status if last_run else None,
                    last_run_at=last_run.created_at if last_run else None,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )
        return summaries

    @classmethod
    async def get_pipeline(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> TransformationPipeline:
        stmt = (
            select(TransformationPipeline)
            .options(
                selectinload(TransformationPipeline.steps),
                selectinload(TransformationPipeline.runs),
            )
            .where(
                TransformationPipeline.id == pipeline_id,
                TransformationPipeline.workspace_id == workspace_id,
            )
        )
        res = await db.execute(stmt)
        pipeline = res.scalar_one_or_none()
        if not pipeline:
            raise DataLensException("Transformation pipeline not found.", code="NOT_FOUND")
        return pipeline

    @classmethod
    async def update_pipeline(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        data: TransformationPipelineUpdate,
        db: AsyncSession,
    ) -> TransformationPipeline:
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        if data.name is not None:
            pipeline.name = data.name.strip()
        if data.description is not None:
            pipeline.description = data.description.strip() if data.description else None
        if data.source_dataset_ids is not None:
            pipeline.source_dataset_ids = data.source_dataset_ids
        if data.status is not None:
            pipeline.status = data.status
        await db.commit()
        return await cls.get_pipeline(pipeline.id, workspace_id, db)

    @classmethod
    async def delete_pipeline(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        await db.delete(pipeline)
        await db.commit()

    # -----------------------------------------------------------------------
    # Step CRUD
    # -----------------------------------------------------------------------

    @classmethod
    async def add_step(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        data: TransformationStepCreate,
        db: AsyncSession,
    ) -> TransformationStep:
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        # Determine step order if not explicitly set
        next_order = len(pipeline.steps) if data.step_order is None else data.step_order

        step = TransformationStep(
            pipeline_id=pipeline_id,
            step_order=next_order,
            operation_type=data.operation_type,
            configuration=data.configuration,
            input_references=data.input_references,
            output_schema=data.output_schema,
        )
        db.add(step)
        await db.commit()
        await db.refresh(step)
        return step

    @classmethod
    async def update_step(
        cls,
        pipeline_id: uuid.UUID,
        step_id: uuid.UUID,
        workspace_id: uuid.UUID,
        data: TransformationStepUpdate,
        db: AsyncSession,
    ) -> TransformationStep:
        await cls.get_pipeline(pipeline_id, workspace_id, db)
        stmt = select(TransformationStep).where(
            TransformationStep.id == step_id,
            TransformationStep.pipeline_id == pipeline_id,
        )
        res = await db.execute(stmt)
        step = res.scalar_one_or_none()
        if not step:
            raise DataLensException("Transformation step not found.", code="NOT_FOUND")

        if data.step_order is not None:
            step.step_order = data.step_order
        if data.operation_type is not None:
            step.operation_type = data.operation_type
        if data.configuration is not None:
            step.configuration = data.configuration
        if data.input_references is not None:
            step.input_references = data.input_references
        if data.output_schema is not None:
            step.output_schema = data.output_schema

        await db.commit()
        await db.refresh(step)
        return step

    @classmethod
    async def delete_step(
        cls,
        pipeline_id: uuid.UUID,
        step_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        stmt = select(TransformationStep).where(
            TransformationStep.id == step_id,
            TransformationStep.pipeline_id == pipeline_id,
        )
        res = await db.execute(stmt)
        step = res.scalar_one_or_none()
        if not step:
            raise DataLensException("Transformation step not found.", code="NOT_FOUND")

        await db.delete(step)
        # Re-index remaining steps
        remaining = [s for s in pipeline.steps if s.id != step_id]
        remaining.sort(key=lambda s: s.step_order)
        for idx, s in enumerate(remaining):
            s.step_order = idx
        await db.commit()

    @classmethod
    async def reorder_steps(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        step_ids: list[uuid.UUID],
        db: AsyncSession,
    ) -> list[TransformationStep]:
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        step_map = {s.id: s for s in pipeline.steps}
        if len(step_ids) != len(step_map) or any(sid not in step_map for sid in step_ids):
            raise DataLensException("Invalid step ordering list.", code="BAD_REQUEST")

        for idx, sid in enumerate(step_ids):
            step_map[sid].step_order = idx

        await db.commit()
        # Return reordered steps
        steps = sorted(pipeline.steps, key=lambda s: s.step_order)
        return steps

    # -----------------------------------------------------------------------
    # DuckDB Execution Engine
    # -----------------------------------------------------------------------

    @classmethod
    async def _setup_duckdb_sources(
        cls,
        workspace_id: uuid.UUID,
        dataset_ids: list[str],
        conn: duckdb.DuckDBPyConnection,
        db: AsyncSession,
    ) -> dict[str, dict[str, Any]]:
        """Registers source datasets as DuckDB views and returns version metadata."""
        dataset_versions_meta: dict[str, Any] = {}
        for ds_id_str in dataset_ids:
            try:
                ds_uuid = uuid.UUID(ds_id_str)
            except ValueError:
                continue

            ds, ver, paths, cols = await cls._resolve_dataset(ds_uuid, workspace_id, db)
            dataset_versions_meta[str(ds.id)] = {
                "name": ds.name,
                "version_id": str(ver.id),
                "version_number": ver.version_number,
                "row_count": ver.row_count,
            }
            clean_paths = [str(p).replace("\\", "/") for p in paths if p.is_file()]
            if not clean_paths:
                raise DataLensException(f"Parquet files missing for dataset '{ds.name}'", code="STORAGE_NOT_FOUND")

            paths_expr = ", ".join(f"'{p}'" for p in clean_paths)
            table_name = f"ds_{ds_uuid.hex}"
            conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet([{paths_expr}])")

        return dataset_versions_meta

    @classmethod
    def _execute_step(
        cls,
        step: TransformationStep,
        step_idx: int,
        input_table: str,
        conn: duckdb.DuckDBPyConnection,
    ) -> str:
        """Executes a single transformation step in DuckDB and returns the output table name."""
        output_table = f"step_{step_idx}"
        cfg = step.configuration or {}
        op = step.operation_type

        # 1. JOIN
        if op == "join":
            right_ds_id = cfg.get("right_dataset_id")
            if not right_ds_id:
                raise DataLensException("Join step requires 'right_dataset_id'", code="INVALID_STEP")
            try:
                right_uuid = uuid.UUID(str(right_ds_id))
            except ValueError:
                raise DataLensException("Invalid right_dataset_id in Join step", code="INVALID_STEP")

            right_table = f"ds_{right_uuid.hex}"
            join_type = cfg.get("join_type", "inner").upper()
            if join_type not in ("INNER", "LEFT", "RIGHT", "FULL", "FULL OUTER"):
                join_type = "INNER"
            if join_type == "FULL OUTER":
                join_type = "FULL"

            join_keys = cfg.get("join_keys", [])
            if not join_keys:
                raise DataLensException("Join step requires at least one join key pair", code="INVALID_STEP")

            # Validate columns in left and right tables
            left_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            right_cols = [c[0] for c in conn.execute(f"DESCRIBE {right_table}").fetchall()]

            on_clauses = []
            for jk in join_keys:
                l_col = jk.get("left")
                r_col = jk.get("right")
                if not l_col or not r_col:
                    raise DataLensException("Join key missing 'left' or 'right' column", code="INVALID_STEP")
                on_clauses.append(f'{input_table}."{l_col}" = {right_table}."{r_col}"')

            # Conflict column resolution
            left_suffix = cfg.get("conflict_suffix_left", "_left")
            right_suffix = cfg.get("conflict_suffix_right", "_right")
            common_cols = set(left_cols).intersection(set(right_cols))

            select_items = []
            for col in left_cols:
                if col in common_cols:
                    select_items.append(f'{input_table}."{col}" AS "{col}{left_suffix}"')
                else:
                    select_items.append(f'{input_table}."{col}"')

            for col in right_cols:
                if col in common_cols:
                    select_items.append(f'{right_table}."{col}" AS "{col}{right_suffix}"')
                else:
                    select_items.append(f'{right_table}."{col}"')

            sql = f"""
            CREATE OR REPLACE TABLE {output_table} AS
            SELECT {', '.join(select_items)}
            FROM {input_table}
            {join_type} JOIN {right_table}
            ON {' AND '.join(on_clauses)}
            """
            conn.execute(sql)

        # 2. APPEND (UNION)
        elif op == "append":
            other_ds_ids = cfg.get("dataset_ids", [])
            mode = cfg.get("mode", "all").lower()
            union_op = "UNION ALL" if mode == "all" else "UNION"

            # Align columns
            base_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            union_queries = [f"SELECT {', '.join(cls._sanitize_ident(c) for c in base_cols)} FROM {input_table}"]

            for ds_id_str in other_ds_ids:
                try:
                    other_uuid = uuid.UUID(str(ds_id_str))
                except ValueError:
                    continue
                other_table = f"ds_{other_uuid.hex}"
                other_cols = set(c[0] for c in conn.execute(f"DESCRIBE {other_table}").fetchall())

                proj = []
                for c in base_cols:
                    if c in other_cols:
                        proj.append(cls._sanitize_ident(c))
                    else:
                        proj.append(f"NULL AS {cls._sanitize_ident(c)}")
                union_queries.append(f"SELECT {', '.join(proj)} FROM {other_table}")

            sql = f"CREATE OR REPLACE TABLE {output_table} AS ({f' {union_op} '.join(union_queries)})"
            conn.execute(sql)

        # 3. CLEAN NULLS
        elif op == "clean_nulls":
            strategies = cfg.get("strategies", [])
            existing_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            where_conditions = []
            transform_map: dict[str, str] = {}

            for strat in strategies:
                col = strat.get("column")
                if col not in existing_cols:
                    continue
                action = strat.get("strategy", "drop")
                if action == "drop":
                    where_conditions.append(f"{cls._sanitize_ident(col)} IS NOT NULL")
                elif action == "fill_value":
                    val = strat.get("fill_value", "")
                    if isinstance(val, (int, float)):
                        transform_map[col] = f"COALESCE({cls._sanitize_ident(col)}, {val}) AS {cls._sanitize_ident(col)}"
                    else:
                        clean_val = str(val).replace("'", "''")
                        transform_map[col] = f"COALESCE({cls._sanitize_ident(col)}, '{clean_val}') AS {cls._sanitize_ident(col)}"
                elif action == "fill_mean":
                    mean_val = conn.execute(f"SELECT AVG({cls._sanitize_ident(col)}) FROM {input_table}").fetchone()[0]
                    fill = mean_val if mean_val is not None else 0
                    transform_map[col] = f"COALESCE({cls._sanitize_ident(col)}, {fill}) AS {cls._sanitize_ident(col)}"
                elif action == "fill_median":
                    med_val = conn.execute(f"SELECT MEDIAN({cls._sanitize_ident(col)}) FROM {input_table}").fetchone()[0]
                    fill = med_val if med_val is not None else 0
                    transform_map[col] = f"COALESCE({cls._sanitize_ident(col)}, {fill}) AS {cls._sanitize_ident(col)}"
                elif action == "fill_mode":
                    mode_row = conn.execute(
                        f"SELECT {cls._sanitize_ident(col)}, COUNT(*) as cnt FROM {input_table} WHERE {cls._sanitize_ident(col)} IS NOT NULL GROUP BY 1 ORDER BY cnt DESC LIMIT 1"
                    ).fetchone()
                    fill = mode_row[0] if mode_row else "Unknown"
                    if isinstance(fill, (int, float)):
                        transform_map[col] = f"COALESCE({cls._sanitize_ident(col)}, {fill}) AS {cls._sanitize_ident(col)}"
                    else:
                        clean_fill = str(fill).replace("'", "''")
                        transform_map[col] = f"COALESCE({cls._sanitize_ident(col)}, '{clean_fill}') AS {cls._sanitize_ident(col)}"

            select_parts = [transform_map.get(c, cls._sanitize_ident(c)) for c in existing_cols]
            where_sql = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
            sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT {', '.join(select_parts)} FROM {input_table} {where_sql}"
            conn.execute(sql)

        # 4. CLEAN DUPLICATES
        elif op == "clean_duplicates":
            subset = cfg.get("subset_columns", [])
            if subset:
                subset_idents = [cls._sanitize_ident(c) for c in subset]
                sql = f"""
                CREATE OR REPLACE TABLE {output_table} AS
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY {', '.join(subset_idents)} ORDER BY (SELECT NULL)) as __rn
                    FROM {input_table}
                ) WHERE __rn = 1
                """
                conn.execute(sql)
                conn.execute(f"ALTER TABLE {output_table} DROP COLUMN __rn")
            else:
                sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT DISTINCT * FROM {input_table}"
                conn.execute(sql)

        # 5. TYPE CAST
        elif op == "type_cast":
            casts = cfg.get("casts", [])
            existing_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            type_map = {
                "integer": "BIGINT",
                "float": "DOUBLE",
                "string": "VARCHAR",
                "boolean": "BOOLEAN",
                "date": "DATE",
                "timestamp": "TIMESTAMP",
            }
            cast_dict: dict[str, str] = {}
            for item in casts:
                col = item.get("column")
                target = item.get("target_type", "string").lower()
                duck_type = type_map.get(target, "VARCHAR")
                if col in existing_cols:
                    cast_dict[col] = f"TRY_CAST({cls._sanitize_ident(col)} AS {duck_type}) AS {cls._sanitize_ident(col)}"

            select_parts = [cast_dict.get(c, cls._sanitize_ident(c)) for c in existing_cols]
            sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT {', '.join(select_parts)} FROM {input_table}"
            conn.execute(sql)

        # 6. STRING OPERATIONS
        elif op == "string_op":
            operations = cfg.get("operations", [])
            existing_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            op_dict: dict[str, str] = {}
            for item in operations:
                col = item.get("column")
                action = item.get("op", "trim").lower()
                ident = cls._sanitize_ident(col)
                if col not in existing_cols:
                    continue
                if action == "trim":
                    op_dict[col] = f"TRIM({ident}) AS {ident}"
                elif action == "upper":
                    op_dict[col] = f"UPPER({ident}) AS {ident}"
                elif action == "lower":
                    op_dict[col] = f"LOWER({ident}) AS {ident}"
                elif action == "capitalize":
                    op_dict[col] = f"CONCAT(UPPER(SUBSTRING({ident}, 1, 1)), LOWER(SUBSTRING({ident}, 2))) AS {ident}"
                elif action == "replace":
                    search = str(item.get("search", "")).replace("'", "''")
                    replace_with = str(item.get("replace_with", "")).replace("'", "''")
                    op_dict[col] = f"REPLACE({ident}, '{search}', '{replace_with}') AS {ident}"
                elif action == "substring":
                    start = int(item.get("start", 1))
                    length = item.get("length")
                    if length is not None:
                        op_dict[col] = f"SUBSTRING({ident}, {start}, {int(length)}) AS {ident}"
                    else:
                        op_dict[col] = f"SUBSTRING({ident}, {start}) AS {ident}"

            select_parts = [op_dict.get(c, cls._sanitize_ident(c)) for c in existing_cols]
            sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT {', '.join(select_parts)} FROM {input_table}"
            conn.execute(sql)

        # 7. FORMULA / CALCULATED COLUMN
        elif op == "formula":
            output_col = cfg.get("output_column", "calculated_col").strip()
            expression = cfg.get("expression", "").strip()
            if not expression:
                raise DataLensException("Formula expression is required", code="INVALID_STEP")

            existing_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            _, formula_sql, _ = FormulaEngine.parse_and_validate(expression, existing_cols)

            sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT *, ({formula_sql}) AS {cls._sanitize_ident(output_col)} FROM {input_table}"
            conn.execute(sql)

        # 8. FILTER
        elif op == "filter":
            conditions = cfg.get("conditions", [])
            logical_op = cfg.get("logical_op", "AND").upper()
            if logical_op not in ("AND", "OR"):
                logical_op = "AND"

            existing_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            cond_clauses = []
            for cond in conditions:
                col = cond.get("column")
                operator = cond.get("operator", "eq").lower()
                val = cond.get("value")
                if col not in existing_cols:
                    continue
                ident = cls._sanitize_ident(col)
                if operator == "eq":
                    cond_clauses.append(f"{ident} = '{val}'" if isinstance(val, str) else f"{ident} = {val}")
                elif operator == "neq":
                    cond_clauses.append(f"{ident} != '{val}'" if isinstance(val, str) else f"{ident} != {val}")
                elif operator == "gt":
                    cond_clauses.append(f"{ident} > {val}")
                elif operator == "gte":
                    cond_clauses.append(f"{ident} >= {val}")
                elif operator == "lt":
                    cond_clauses.append(f"{ident} < {val}")
                elif operator == "lte":
                    cond_clauses.append(f"{ident} <= {val}")
                elif operator == "contains":
                    cond_clauses.append(f"{ident} ILIKE '%{val}%'")
                elif operator == "starts_with":
                    cond_clauses.append(f"{ident} ILIKE '{val}%'")
                elif operator == "is_null":
                    cond_clauses.append(f"{ident} IS NULL")
                elif operator == "not_null":
                    cond_clauses.append(f"{ident} IS NOT NULL")

            where_sql = f"WHERE {f' {logical_op} '.join(cond_clauses)}" if cond_clauses else ""
            sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT * FROM {input_table} {where_sql}"
            conn.execute(sql)

        # 9. SELECT / RENAME COLUMNS
        elif op == "select_columns":
            selected = cfg.get("columns", [])
            renames = cfg.get("renames", {})  # {orig: new}
            existing_cols = [c[0] for c in conn.execute(f"DESCRIBE {input_table}").fetchall()]
            cols_to_use = [c for c in selected if c in existing_cols] if selected else existing_cols

            select_parts = []
            for c in cols_to_use:
                if c in renames and renames[c]:
                    select_parts.append(f"{cls._sanitize_ident(c)} AS {cls._sanitize_ident(renames[c])}")
                else:
                    select_parts.append(cls._sanitize_ident(c))

            sql = f"CREATE OR REPLACE TABLE {output_table} AS SELECT {', '.join(select_parts)} FROM {input_table}"
            conn.execute(sql)

        else:
            raise DataLensException(f"Unsupported transformation operation: '{op}'", code="UNSUPPORTED_OPERATION")

        return output_table

    # -----------------------------------------------------------------------
    # Preview Execution
    # -----------------------------------------------------------------------

    @classmethod
    async def preview_pipeline(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        step_index: int | None,
        limit: int,
        db: AsyncSession,
    ) -> PreviewResponse:
        start_time = time.perf_counter()
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        if not pipeline.source_dataset_ids:
            raise DataLensException("Pipeline has no source datasets configured.", code="BAD_REQUEST")

        conn = duckdb.connect(":memory:")
        try:
            # 1. Register sources
            await cls._setup_duckdb_sources(workspace_id, pipeline.source_dataset_ids, conn, db)

            # 2. Base table is the first source dataset
            first_uuid = uuid.UUID(pipeline.source_dataset_ids[0])
            current_table = f"ds_{first_uuid.hex}"

            # 3. Apply steps in order up to target step
            sorted_steps = sorted(pipeline.steps, key=lambda s: s.step_order)
            steps_to_run = (
                sorted_steps[: step_index + 1]
                if step_index is not None and step_index >= 0
                else sorted_steps
            )

            executed_step_count = len(steps_to_run)
            for idx, step in enumerate(steps_to_run):
                current_table = cls._execute_step(step, idx + 1, current_table, conn)

            # 4. Describe schema and fetch sample rows
            desc_rows = conn.execute(f"DESCRIBE {current_table}").fetchall()
            columns = [
                PreviewColumn(name=r[0], data_type=cls._map_duckdb_type(r[1]))
                for r in desc_rows
            ]

            fetch_rows = conn.execute(f"SELECT * FROM {current_table} LIMIT {limit}").fetchall()
            col_names = [r[0] for r in desc_rows]
            formatted_rows: list[dict[str, Any]] = []
            for row in fetch_rows:
                row_dict = {}
                for idx, val in enumerate(row):
                    if isinstance(val, (datetime,)):
                        row_dict[col_names[idx]] = val.isoformat()
                    else:
                        row_dict[col_names[idx]] = val
                formatted_rows.append(row_dict)

            total_sampled = conn.execute(f"SELECT COUNT(*) FROM {current_table}").fetchone()[0]
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            return PreviewResponse(
                columns=columns,
                rows=formatted_rows,
                total_rows_sampled=total_sampled,
                step_executed=executed_step_count,
                execution_duration_ms=elapsed_ms,
            )
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Full Execution & Dataset Materialization
    # -----------------------------------------------------------------------

    @classmethod
    async def run_pipeline(
        cls,
        pipeline_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        output_name: str | None,
        output_desc: str | None,
        db: AsyncSession,
    ) -> TransformationRun:
        start_time = time.perf_counter()
        pipeline = await cls.get_pipeline(pipeline_id, workspace_id, db)
        if not pipeline.source_dataset_ids:
            raise DataLensException("Pipeline has no source datasets configured.", code="BAD_REQUEST")

        run = TransformationRun(
            pipeline_id=pipeline.id,
            workspace_id=workspace_id,
            triggered_by=user_id,
            status="running",
            source_dataset_versions={},
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        conn = duckdb.connect(":memory:")
        try:
            # 1. Register sources and record source versions for lineage
            sources_meta = await cls._setup_duckdb_sources(workspace_id, pipeline.source_dataset_ids, conn, db)
            run.source_dataset_versions = sources_meta

            # 2. Base table
            first_uuid = uuid.UUID(pipeline.source_dataset_ids[0])
            current_table = f"ds_{first_uuid.hex}"

            # 3. Run all steps sequentially
            sorted_steps = sorted(pipeline.steps, key=lambda s: s.step_order)
            for idx, step in enumerate(sorted_steps):
                current_table = cls._execute_step(step, idx + 1, current_table, conn)

            # 4. Materialize output Parquet
            out_dataset_id = uuid.uuid4()
            out_version_id = uuid.uuid4()
            storage_root = Path(settings.STORAGE_ROOT).resolve()

            safe_rel_dir = f"datasets/{workspace_id}/{out_dataset_id}/{out_version_id}/processed"
            target_dir = storage_root / safe_rel_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            parquet_file_path = target_dir / "part_0.parquet"
            conn.execute(f"COPY (SELECT * FROM {current_table}) TO '{str(parquet_file_path).replace('\\', '/')}' (FORMAT PARQUET)")

            # Compute row count, columns and schema
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {current_table}").fetchone()[0]
            desc_rows = conn.execute(f"DESCRIBE {current_table}").fetchall()

            # Columns metadata
            columns_meta = []
            for col_info in desc_rows:
                col_name = col_info[0]
                duck_type = col_info[1]
                inferred = cls._map_duckdb_type(duck_type)
                # Sample values
                sample_rows = conn.execute(f"SELECT {cls._sanitize_ident(col_name)} FROM {current_table} WHERE {cls._sanitize_ident(col_name)} IS NOT NULL LIMIT 3").fetchall()
                samples = [str(r[0]) for r in sample_rows]
                null_cnt = conn.execute(f"SELECT COUNT(*) FROM {current_table} WHERE {cls._sanitize_ident(col_name)} IS NULL").fetchone()[0]
                columns_meta.append({
                    "name": col_name,
                    "inferred_type": inferred,
                    "null_count": null_cnt,
                    "sample_values": samples,
                })

            # Checksum
            with open(parquet_file_path, "rb") as pf:
                checksum = hashlib.sha256(pf.read()).hexdigest()

            # Write manifest.json
            manifest_data = {
                "parts": [f"{safe_rel_dir}/part_0.parquet"],
                "row_count": total_rows,
                "column_count": len(columns_meta),
                "columns": columns_meta,
                "checksum": checksum,
                "created_at": datetime.now(UTC).isoformat(),
                "transformation_pipeline_id": str(pipeline.id),
                "transformation_run_id": str(run.id),
            }
            manifest_key = f"{safe_rel_dir}/manifest.json"
            (storage_root / manifest_key).write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

            # 5. Create derived Dataset & DatasetVersion in PostgreSQL
            ds_name = (output_name or f"Transformed - {pipeline.name}").strip()
            derived_dataset = Dataset(
                id=out_dataset_id,
                workspace_id=workspace_id,
                uploaded_by=user_id,
                name=ds_name,
                original_filename=f"pipeline_{pipeline.id.hex[:8]}.parquet",
                file_type="parquet",
                row_count=total_rows,
                column_count=len(columns_meta),
                status="ready",
                is_archived=False,
            )
            db.add(derived_dataset)
            await db.flush()

            derived_version = DatasetVersion(
                id=out_version_id,
                dataset_id=out_dataset_id,
                version_number="v1",
                storage_key=manifest_key,
                original_storage_key=manifest_key,
                file_size=parquet_file_path.stat().st_size,
                schema_metadata={"columns": columns_meta, "row_count": total_rows, "column_count": len(columns_meta)},
                row_count=total_rows,
                column_count=len(columns_meta),
                checksum=checksum,
                status="ready",
            )
            db.add(derived_version)
            await db.flush()

            derived_dataset.current_version_id = derived_version.id

            # 6. Mark Run as completed
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            run.status = "completed"
            run.output_dataset_id = derived_dataset.id
            run.output_dataset_version_id = derived_version.id
            run.execution_duration_ms = elapsed_ms
            run.row_count = total_rows
            await db.commit()
            await db.refresh(run)
            return run

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception("Transformation pipeline execution failed: %s", e)
            run.status = "failed"
            run.error_details = str(e)
            run.execution_duration_ms = elapsed_ms
            await db.commit()
            await db.refresh(run)
            raise DataLensException(f"Pipeline execution failed: {e}", code="TRANSFORMATION_FAILED")
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Formula Dry-Run Validation
    # -----------------------------------------------------------------------

    @classmethod
    def validate_formula(
        cls,
        expression: str,
        columns: list[dict[str, Any]],
    ) -> ValidateFormulaResponse:
        col_names = [c.get("name") for c in columns if c.get("name")]
        try:
            ast, sql, cols = FormulaEngine.parse_and_validate(expression, col_names)
            return ValidateFormulaResponse(
                valid=True,
                ast_summary=ast.describe(),
                referenced_columns=cols,
                sql_expression=sql,
            )
        except FormulaError as fe:
            return ValidateFormulaResponse(
                valid=False,
                error=str(fe),
            )
        except Exception as e:
            return ValidateFormulaResponse(
                valid=False,
                error=f"Syntax error: {e}",
            )
