"""Unified Data Import Engine for external data sources."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import ConnectorRegistry
from app.connectors.security import vault
from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.data_source import (
    DataSourceConnection,
    DataSourceImport,
    DataSourceTableMetadata,
)
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.services.dataset_processor import DatasetProcessor


class ImportEngine:
    """Orchestrates streaming ingestion from external connectors to immutable Parquet datasets."""

    CHUNK_SIZE = 5000

    @classmethod
    async def execute_import(
        cls,
        db: AsyncSession,
        connection_id: uuid.UUID,
        resource_path: str,
        user_id: uuid.UUID,
        import_mode: str = "full",
        target_dataset_name: str | None = None,
        target_dataset_id: uuid.UUID | None = None,
        watermark_column: str | None = None,
        existing_import_id: uuid.UUID | None = None,
    ) -> DataSourceImport:
        """
        Stream records from external connector, write partitioned Parquet files,
        and create/update Dataset and DatasetVersion records.
        """
        # 1. Fetch connection
        stmt = select(DataSourceConnection).where(DataSourceConnection.id == connection_id)
        res = await db.execute(stmt)
        conn = res.scalar_one_or_none()
        if not conn:
            raise DataLensException(f"DataSourceConnection {connection_id} not found.", code="NOT_FOUND")

        workspace_id = conn.workspace_id

        # 2. Get or create DataSourceImport record
        if existing_import_id:
            imp_res = await db.execute(select(DataSourceImport).where(DataSourceImport.id == existing_import_id))
            import_record = imp_res.scalar_one_or_none()
            if not import_record:
                raise DataLensException(f"DataSourceImport {existing_import_id} not found.", code="NOT_FOUND")
        else:
            import_record = DataSourceImport(
                id=uuid.uuid4(),
                connection_id=conn.id,
                workspace_id=workspace_id,
                source_resource=resource_path,
                import_mode=import_mode,
                watermark_column=watermark_column,
                status="in_progress",
                triggered_by=user_id,
                started_at=datetime.now(UTC),
            )
            db.add(import_record)
            await db.flush()

        import_record.status = "in_progress"
        import_record.started_at = datetime.now(UTC)
        await db.commit()

        # 3. Decrypt credentials and instantiate connector
        try:
            creds = vault.decrypt(conn.encrypted_credentials)
            connector = ConnectorRegistry.get(conn.source_type, str(conn.id), conn.config, creds)
        except Exception as e:
            import_record.status = "failed"
            import_record.error_message = f"Credential or connector init error: {str(e)}"
            import_record.completed_at = datetime.now(UTC)
            await db.commit()
            raise DataLensException(f"Failed to initialize connector: {str(e)}", code="CONNECTOR_INIT_ERROR")

        # 4. Resolve watermark value if incremental
        watermark_val = None
        if import_mode == "incremental" and watermark_column:
            # Check previous completed import watermark
            prev_stmt = (
                select(DataSourceImport)
                .where(
                    DataSourceImport.connection_id == conn.id,
                    DataSourceImport.source_resource == resource_path,
                    DataSourceImport.status == "completed",
                    DataSourceImport.last_watermark_value.is_not(None),
                )
                .order_by(desc(DataSourceImport.completed_at))
            )
            prev_res = await db.execute(prev_stmt)
            prev_imp = prev_res.scalars().first()
            if prev_imp:
                watermark_val = prev_imp.watermark_value

        # 5. Prepare Storage paths
        dataset_id = target_dataset_id or uuid.uuid4()
        version_id = uuid.uuid4()
        storage_root = Path(settings.STORAGE_ROOT).resolve()
        safe_rel_dir = f"datasets/{workspace_id}/{dataset_id}/{version_id}"
        processed_dir_rel = f"{safe_rel_dir}/processed"
        processed_dir_path = storage_root / processed_dir_rel
        processed_dir_path.mkdir(parents=True, exist_ok=True)

        parts: list[str] = []
        part_idx = 1
        total_rows = 0
        total_bytes = 0
        max_watermark_seen = watermark_val
        headers: list[str] = []
        seen_headers: dict[str, int] = {}
        col_type_votes: dict[str, dict[str, int]] = {}
        col_null_counts: dict[str, int] = {}
        sample_values: dict[str, list[Any]] = {}

        try:
            # 6. Stream and write Parquet chunks
            rows_buffer: list[dict[str, Any]] = []

            async for batch in connector.stream_data(
                resource_path=resource_path,
                chunk_size=cls.CHUNK_SIZE,
                watermark_col=watermark_column,
                watermark_val=watermark_val,
            ):
                if not batch:
                    continue

                # Initialize headers from the first non-empty batch
                if not headers:
                    raw_keys = list(batch[0].keys())
                    headers = [DatasetProcessor.sanitize_column_name(k, idx, seen_headers) for idx, k in enumerate(raw_keys)]
                    for h in headers:
                        col_type_votes[h] = {}
                        col_null_counts[h] = 0
                        sample_values[h] = []

                for row in batch:
                    row_dict: dict[str, Any] = {}
                    for idx, orig_k in enumerate(list(row.keys())):
                        if idx < len(headers):
                            clean_col = headers[idx]
                            val = row[orig_k]
                            coerced, detected_type = DatasetProcessor.infer_and_coerce_value(val)
                            row_dict[clean_col] = coerced

                            if watermark_column and (orig_k == watermark_column or clean_col == watermark_column):
                                if val is not None:
                                    val_str = str(val)
                                    if max_watermark_seen is None or val_str > str(max_watermark_seen):
                                        max_watermark_seen = val_str

                            if coerced is None:
                                col_null_counts[clean_col] += 1
                            else:
                                col_type_votes[clean_col][detected_type] = col_type_votes[clean_col].get(detected_type, 0) + 1
                                if len(sample_values[clean_col]) < 5:
                                    sample_values[clean_col].append(coerced)

                    rows_buffer.append(row_dict)
                    total_rows += 1

                    if len(rows_buffer) >= cls.CHUNK_SIZE:
                        part_filename = f"part-{part_idx:05d}.parquet"
                        part_dest = processed_dir_path / part_filename
                        cls._write_parquet(rows_buffer, headers, part_dest)
                        part_bytes = part_dest.stat().st_size
                        total_bytes += part_bytes
                        parts.append(f"{processed_dir_rel}/{part_filename}")
                        part_idx += 1
                        rows_buffer.clear()

            # Flush remaining buffer
            if rows_buffer or total_rows == 0:
                if not headers:
                    headers = ["empty_column"]
                    col_type_votes["empty_column"] = {}
                    col_null_counts["empty_column"] = 0
                    sample_values["empty_column"] = []
                part_filename = f"part-{part_idx:05d}.parquet"
                part_dest = processed_dir_path / part_filename
                cls._write_parquet(rows_buffer, headers, part_dest)
                part_bytes = part_dest.stat().st_size
                total_bytes += part_bytes
                parts.append(f"{processed_dir_rel}/{part_filename}")
                rows_buffer.clear()

            # 7. Finalize column metadata
            columns_meta = []
            for h in headers:
                votes = col_type_votes.get(h, {})
                if not votes:
                    final_type = "string"
                else:
                    sorted_types = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)
                    final_type = sorted_types[0][0]
                    if final_type == "null":
                        final_type = "string"
                columns_meta.append({
                    "name": h,
                    "inferred_type": final_type,
                    "null_count": col_null_counts.get(h, 0),
                    "sample_values": [str(v) for v in sample_values.get(h, [])],
                })

            # 8. Write manifest.json
            manifest_data = {
                "parts": parts,
                "row_count": total_rows,
                "column_count": len(headers),
                "columns": columns_meta,
                "watermark_column": watermark_column,
                "watermark_value": max_watermark_seen,
                "source_type": conn.source_type,
                "source_resource": resource_path,
            }
            manifest_filename = "manifest.json"
            manifest_rel_key = f"{processed_dir_rel}/{manifest_filename}"
            manifest_dest = storage_root / manifest_rel_key
            manifest_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")
            manifest_dest.write_bytes(manifest_bytes)
            total_bytes += len(manifest_bytes)

            checksum = hashlib.sha256(manifest_bytes).hexdigest()

            # 9. Create Dataset and DatasetVersion records
            if target_dataset_id:
                d_stmt = select(Dataset).where(Dataset.id == target_dataset_id)
                d_res = await db.execute(d_stmt)
                dataset = d_res.scalar_one_or_none()
                if not dataset:
                    raise DataLensException(f"Target Dataset {target_dataset_id} not found.", code="NOT_FOUND")
                
                # Compute version number
                v_count_stmt = select(DatasetVersion).where(DatasetVersion.dataset_id == target_dataset_id)
                v_res = await db.execute(v_count_stmt)
                existing_versions = len(v_res.scalars().all())
                version_number = f"v{existing_versions + 1}.0"
            else:
                default_name = target_dataset_name or f"{conn.name} - {resource_path}"
                dataset = Dataset(
                    id=dataset_id,
                    workspace_id=workspace_id,
                    uploaded_by=user_id,
                    name=default_name.strip(),
                    original_filename=f"{conn.source_type}_{resource_path}.parquet",
                    file_type="parquet",
                    row_count=total_rows,
                    column_count=len(headers),
                    status="ready",
                )
                db.add(dataset)
                await db.flush()
                version_number = "v1.0"

            dataset_version = DatasetVersion(
                id=version_id,
                dataset_id=dataset.id,
                version_number=version_number,
                storage_key=manifest_rel_key,
                original_storage_key=manifest_rel_key,
                file_size=total_bytes,
                schema_metadata={"columns": columns_meta, "manifest": manifest_data},
                row_count=total_rows,
                column_count=len(headers),
                checksum=checksum,
                status="ready",
                created_at=datetime.now(UTC),
            )
            db.add(dataset_version)
            await db.flush()

            dataset.current_version_id = dataset_version.id
            dataset.row_count = total_rows
            dataset.column_count = len(headers)
            dataset.status = "ready"

            # 10. Update DataSourceImport
            import_record.status = "completed"
            import_record.dataset_id = dataset.id
            import_record.dataset_version_id = dataset_version.id
            import_record.rows_imported = total_rows
            import_record.bytes_imported = total_bytes
            import_record.watermark_value = max_watermark_seen
            import_record.completed_at = datetime.now(UTC)

            # 11. Update DataSourceTableMetadata
            meta_stmt = select(DataSourceTableMetadata).where(
                DataSourceTableMetadata.connection_id == conn.id,
                DataSourceTableMetadata.table_name == resource_path,
            )
            meta_res = await db.execute(meta_stmt)
            meta_record = meta_res.scalar_one_or_none()
            if not meta_record:
                meta_record = DataSourceTableMetadata(
                    id=uuid.uuid4(),
                    connection_id=conn.id,
                    table_name=resource_path,
                    row_count_estimate=total_rows,
                    last_imported_at=datetime.now(UTC),
                )
                db.add(meta_record)
            else:
                meta_record.row_count_estimate = total_rows
                meta_record.last_imported_at = datetime.now(UTC)

            # Update connection last_tested_at
            conn.last_tested_at = datetime.now(UTC)

            await db.commit()
            return import_record

        except Exception as e:
            await db.rollback()
            import_record.status = "failed"
            import_record.error_message = str(e)
            import_record.completed_at = datetime.now(UTC)
            db.add(import_record)
            await db.commit()
            raise DataLensException(f"Import execution failed: {str(e)}", code="IMPORT_FAILED") from e
        finally:
            await connector.close()

    @staticmethod
    def _write_parquet(rows: list[dict[str, Any]], headers: list[str], output_path: Path) -> None:
        if not rows:
            arrays = [pa.array([], type=pa.string()) for _ in headers]
            table = pa.Table.from_arrays(arrays, names=headers)
        else:
            col_data: dict[str, list[Any]] = {h: [] for h in headers}
            for r in rows:
                for h in headers:
                    col_data[h].append(r.get(h))

            arrays = []
            for h in headers:
                try:
                    arr = pa.array(col_data[h])
                except (pa.ArrowInvalid, pa.ArrowTypeError):
                    arr = pa.array([str(v) if v is not None else None for v in col_data[h]], type=pa.string())
                arrays.append(arr)
            table = pa.Table.from_arrays(arrays, names=headers)

        pq.write_table(table, output_path, compression="SNAPPY")
