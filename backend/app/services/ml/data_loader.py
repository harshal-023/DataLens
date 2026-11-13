import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion


class DatasetDataLoader:
    """
    Loads dataset version Parquet tables from storage, identifies feature types,
    handles missing values, and validates sample sizes for ML operations.
    """

    @classmethod
    async def load_version_data(
        cls,
        db: AsyncSession,
        dataset_id: Any,
        version_id: Any | None,
        workspace_id: Any,
        columns: list[str] | None = None,
    ) -> tuple[Dataset, DatasetVersion, list[dict[str, Any]], dict[str, str]]:
        """
        Loads records and column types from the immutable dataset version Parquet manifest.
        Returns: (dataset, version, records, column_types)
        """
        # 1. Fetch Dataset & verify workspace isolation
        d_stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id)
        dataset = (await db.execute(d_stmt)).scalar_one_or_none()
        if not dataset:
            raise DataLensException("Dataset not found in workspace.", code="NOT_FOUND")

        # 2. Fetch specific version or active current version
        if version_id:
            v_stmt = select(DatasetVersion).where(
                DatasetVersion.id == version_id,
                DatasetVersion.dataset_id == dataset.id,
            )
            version = (await db.execute(v_stmt)).scalar_one_or_none()
            if not version:
                raise DataLensException("Specified dataset version not found.", code="NOT_FOUND")
        else:
            if not dataset.current_version_id:
                raise DataLensException("Dataset has no active version.", code="INVALID_STATE")
            v_stmt = select(DatasetVersion).where(DatasetVersion.id == dataset.current_version_id)
            version = (await db.execute(v_stmt)).scalar_one_or_none()
            if not version:
                raise DataLensException("Active dataset version not found.", code="NOT_FOUND")

        # 3. Read Parquet manifest from storage
        storage_root = Path(settings.STORAGE_ROOT).resolve()
        manifest_path = storage_root / version.storage_key
        if not manifest_path.is_file():
            raise DataLensException(
                f"Storage manifest missing for dataset version {version.id}.",
                code="STORAGE_ERROR",
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parts = manifest.get("parts", [])
        if not parts:
            raise DataLensException("Dataset contains zero data partitions.", code="EMPTY_DATASET")

        # 4. Read Parquet tables across parts
        tables = []
        for part in parts:
            part_path = storage_root / part
            if part_path.is_file():
                tables.append(pq.read_table(part_path, columns=columns))

        if not tables:
            raise DataLensException("No readable data partitions found on disk.", code="STORAGE_ERROR")

        import pyarrow as pa
        full_table = pa.concat_tables(tables) if len(tables) > 1 else tables[0]
        records = full_table.to_pylist()

        # 5. Extract inferred column types from schema metadata
        schema_meta = version.schema_metadata or {}
        col_types = {}
        for c in schema_meta.get("columns", []):
            col_types[c["name"]] = c.get("inferred_type", "string")

        # Fallback type inference from records if schema_metadata is incomplete
        if not col_types and records:
            first_row = records[0]
            for k, val in first_row.items():
                if isinstance(val, (int, float)):
                    col_types[k] = "numeric"
                elif isinstance(val, str) and ("-" in val or "/" in val) and len(val) >= 8:
                    col_types[k] = "date"
                else:
                    col_types[k] = "string"

        return dataset, version, records, col_types

    @classmethod
    def extract_numeric_series(
        cls,
        records: list[dict[str, Any]],
        target_column: str,
        time_column: str | None = None,
        min_rows: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Extracts, filters non-null numeric values, and validates row count threshold.
        """
        if not records:
            raise DataLensException("Dataset is empty; cannot perform analytical calculation.", code="INSUFFICIENT_DATA")

        cleaned = []
        for idx, row in enumerate(records):
            val = row.get(target_column)
            if val is None:
                continue

            try:
                numeric_val = float(val)
                t_val = str(row.get(time_column)) if time_column and row.get(time_column) is not None else None
                cleaned.append({
                    "row_index": idx,
                    "value": numeric_val,
                    "timestamp": t_val,
                })
            except (ValueError, TypeError):
                # Ignore non-convertible values
                continue

        if len(cleaned) < min_rows:
            raise DataLensException(
                f"Insufficient valid numerical observations in column '{target_column}'. "
                f"Found {len(cleaned)} rows, but at least {min_rows} rows are required.",
                code="INSUFFICIENT_DATA",
            )

        return cleaned

