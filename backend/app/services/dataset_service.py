import contextlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.services.dataset_processor import DatasetProcessor
from app.storage import get_storage_backend


class DatasetService:
    ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB configurable ceiling

    @classmethod
    def _validate_file(cls, filename: str, content: bytes) -> str:
        if not filename or "." not in filename:
            raise DataLensException("Invalid file: Missing extension.", code="BAD_REQUEST")

        ext = Path(filename).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise DataLensException(
                f"Unsupported file format '{ext}'. Only CSV and XLSX files are accepted.",
                code="UNSUPPORTED_FORMAT",
            )

        if len(content) == 0:
            raise DataLensException("The uploaded file is completely empty.", code="EMPTY_FILE")

        if len(content) > cls.MAX_FILE_SIZE:
            raise DataLensException(
                f"File size exceeds maximum allowed limit of {cls.MAX_FILE_SIZE // (1024 * 1024)}MB.",
                code="FILE_TOO_LARGE",
            )

        return ext

    @classmethod
    async def create_dataset_from_upload(
        cls,
        workspace_id: uuid.UUID,
        uploader_id: uuid.UUID,
        name: str,
        upload_file: UploadFile,
        selected_worksheet: str | None,
        db: AsyncSession,
    ) -> Dataset:
        filename = upload_file.filename or "uploaded_data"
        content = await upload_file.read()
        ext = cls._validate_file(filename, content)
        clean_ext = ext.lstrip(".")

        dataset_id = uuid.uuid4()
        version_id = uuid.uuid4()
        storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()

        # Opaque structured layout:
        # datasets/{workspace_id}/{dataset_id}/{version_id}/original/...
        # datasets/{workspace_id}/{dataset_id}/{version_id}/processed/...
        safe_rel_dir = f"datasets/{workspace_id}/{dataset_id}/{version_id}"
        original_key = f"{safe_rel_dir}/original/source.{clean_ext}"
        processed_dir_rel = f"{safe_rel_dir}/processed"

        # 1. Save original file
        storage = get_storage_backend()
        await storage.save_file(original_key, content)

        try:
            # 2. Process data & write Parquet parts
            if clean_ext == "csv":
                res = DatasetProcessor.process_csv(
                    data=content,
                    storage_root=storage_root,
                    relative_processed_dir=processed_dir_rel,
                )
            else:
                res = DatasetProcessor.process_excel(
                    data=content,
                    storage_root=storage_root,
                    relative_processed_dir=processed_dir_rel,
                    selected_worksheet=selected_worksheet,
                )

            # 3. Create Dataset Record
            dataset = Dataset(
                id=dataset_id,
                workspace_id=workspace_id,
                uploaded_by=uploader_id,
                name=name.strip() or Path(filename).stem,
                original_filename=filename,
                file_type=clean_ext,
                row_count=res.row_count,
                column_count=res.column_count,
                status="ready",
                is_archived=False,
            )
            db.add(dataset)
            await db.flush()

            # 4. Create Immutable Version v1
            version = DatasetVersion(
                id=version_id,
                dataset_id=dataset_id,
                version_number="v1",
                storage_key=res.manifest_key,
                original_storage_key=original_key,
                file_size=len(content),
                schema_metadata=res.schema_metadata,
                row_count=res.row_count,
                column_count=res.column_count,
                checksum=res.checksum,
                status="ready",
            )
            db.add(version)
            await db.flush()

            # 5. Link current_version_id
            dataset.current_version_id = version.id
            await db.commit()
            await db.refresh(dataset)
            return dataset

        except Exception as e:
            await db.rollback()
            # Clean up saved files if failed
            with contextlib.suppress(Exception):
                await storage.delete_file(original_key)
            if isinstance(e, DataLensException):
                raise e
            raise DataLensException(
                f"Failed to process and ingest dataset: {e!s}",
                code="PROCESSING_ERROR",
            )

    @classmethod
    async def create_replacement_version(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        upload_file: UploadFile,
        selected_worksheet: str | None,
        db: AsyncSession,
    ) -> DatasetVersion:
        # Load dataset
        stmt = (
            select(Dataset)
            .options(selectinload(Dataset.versions))
            .where(
                Dataset.id == dataset_id,
                Dataset.workspace_id == workspace_id,
                Dataset.is_archived.is_(False),
            )
        )
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

        filename = upload_file.filename or "replacement_data"
        content = await upload_file.read()
        ext = cls._validate_file(filename, content)
        clean_ext = ext.lstrip(".")

        # Determine next version number (v1 -> v2 -> v3)
        existing_version_nums = [
            int(v.version_number.lstrip("v"))
            for v in dataset.versions
            if v.version_number.startswith("v") and v.version_number[1:].isdigit()
        ]
        next_ver_num = f"v{max(existing_version_nums, default=0) + 1}"

        version_id = uuid.uuid4()
        storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
        safe_rel_dir = f"datasets/{workspace_id}/{dataset_id}/{version_id}"
        original_key = f"{safe_rel_dir}/original/source.{clean_ext}"
        processed_dir_rel = f"{safe_rel_dir}/processed"

        storage = get_storage_backend()
        await storage.save_file(original_key, content)

        try:
            if clean_ext == "csv":
                proc_res = DatasetProcessor.process_csv(
                    data=content,
                    storage_root=storage_root,
                    relative_processed_dir=processed_dir_rel,
                )
            else:
                proc_res = DatasetProcessor.process_excel(
                    data=content,
                    storage_root=storage_root,
                    relative_processed_dir=processed_dir_rel,
                    selected_worksheet=selected_worksheet,
                )

            new_version = DatasetVersion(
                id=version_id,
                dataset_id=dataset_id,
                version_number=next_ver_num,
                storage_key=proc_res.manifest_key,
                original_storage_key=original_key,
                file_size=len(content),
                schema_metadata=proc_res.schema_metadata,
                row_count=proc_res.row_count,
                column_count=proc_res.column_count,
                checksum=proc_res.checksum,
                status="ready",
            )
            db.add(new_version)
            await db.flush()

            # Update dataset pointer and stats
            prev_version_id = dataset.current_version_id
            dataset.current_version_id = new_version.id
            dataset.row_count = proc_res.row_count
            dataset.column_count = proc_res.column_count
            dataset.updated_at = datetime.now(UTC)

            # Inherit prior column semantic mappings if prior version existed
            if prev_version_id:
                try:
                    from app.services.intelligence.semantic_layer import SemanticLayerService
                    await SemanticLayerService.inherit_mappings_for_new_version(
                        dataset_id=dataset.id,
                        prior_version_id=prev_version_id,
                        new_version_id=new_version.id,
                        db=db,
                    )
                except Exception as ex:
                    logger.warning("Could not inherit column semantics for new version: %s", ex)

            await db.commit()
            await db.refresh(new_version)
            return new_version

        except Exception as e:
            await db.rollback()
            with contextlib.suppress(Exception):
                await storage.delete_file(original_key)
            if isinstance(e, DataLensException):
                raise e
            raise DataLensException(
                f"Failed to create replacement dataset version: {e!s}",
                code="PROCESSING_ERROR",
            )

    @classmethod
    async def list_datasets(
        cls,
        workspace_id: uuid.UUID,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None,
        sort_by: str,
        sort_dir: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        base_query = select(Dataset).where(
            Dataset.workspace_id == workspace_id,
            Dataset.is_archived.is_(False),
        )

        if search:
            pattern = f"%{search.strip().lower()}%"
            base_query = base_query.where(func.lower(Dataset.name).like(pattern))

        if status and status.lower() != "all":
            base_query = base_query.where(Dataset.status == status.lower())

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_count = (await db.execute(count_stmt)).scalar_one()

        # Sort
        sort_col = getattr(Dataset, sort_by, Dataset.created_at)
        order_by_clause = desc(sort_col) if sort_dir.lower() == "desc" else sort_col
        paged_query = (
            base_query.order_by(order_by_clause)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        items = (await db.execute(paged_query)).scalars().all()
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def get_dataset(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Dataset:
        stmt = (
            select(Dataset)
            .options(
                selectinload(Dataset.versions),
                selectinload(Dataset.current_version),
            )
            .where(
                Dataset.id == dataset_id,
                Dataset.workspace_id == workspace_id,
                Dataset.is_archived.is_(False),
            )
        )
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")
        return dataset

    @classmethod
    async def get_dataset_versions(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[DatasetVersion]:
        # Ensure workspace ownership
        await cls.get_dataset(dataset_id, workspace_id, db)
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(desc(DatasetVersion.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_version(
        cls,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> DatasetVersion:
        await cls.get_dataset(dataset_id, workspace_id, db)
        stmt = select(DatasetVersion).where(
            DatasetVersion.id == version_id,
            DatasetVersion.dataset_id == dataset_id,
        )
        res = await db.execute(stmt)
        ver = res.scalar_one_or_none()
        if not ver:
            raise DataLensException("Dataset version not found.", code="NOT_FOUND")
        return ver

    @classmethod
    async def get_dataset_rows(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        version_id: uuid.UUID | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
        columns: list[str] | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        dataset = await cls.get_dataset(dataset_id, workspace_id, db)
        target_ver_id = version_id or dataset.current_version_id
        if not target_ver_id:
            raise DataLensException("Dataset has no active version.", code="NOT_FOUND")

        version = await cls.get_version(dataset_id, target_ver_id, workspace_id, db)
        storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()

        offset = max(0, (page - 1) * page_size)
        read_result = DatasetProcessor.read_paginated_rows(
            storage_root=storage_root,
            manifest_key=version.storage_key,
            offset=offset,
            limit=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            columns=columns,
        )

        total = read_result["total"]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        cols_metadata = version.schema_metadata.get("columns", []) if version.schema_metadata else []

        return {
            "rows": read_result["rows"],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "columns": cols_metadata,
        }

    @classmethod
    async def download_original_file(
        cls,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[bytes, str, str]:
        dataset = await cls.get_dataset(dataset_id, workspace_id, db)
        version = await cls.get_version(dataset_id, version_id, workspace_id, db)

        if not version.original_storage_key:
            raise DataLensException("Original uploaded file is not available.", code="NOT_FOUND")

        storage = get_storage_backend()
        data = await storage.read_file(version.original_storage_key)

        filename = f"{dataset.name}_{version.version_number}.{dataset.file_type}"
        mime = "text/csv" if dataset.file_type == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return data, filename, mime

    @classmethod
    async def delete_dataset(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        permanent: bool,
        db: AsyncSession,
    ) -> None:
        dataset = await cls.get_dataset(dataset_id, workspace_id, db)
        if not permanent:
            # Safe soft archival
            dataset.is_archived = True
            dataset.updated_at = datetime.now(UTC)
            await db.commit()
        else:
            # Permanent delete
            await db.delete(dataset)
            await db.commit()

    @classmethod
    async def get_dataset_status(
        cls,
        dataset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        dataset = await cls.get_dataset(dataset_id, workspace_id, db)
        ver = dataset.current_version
        error_msg = ver.error_message if ver else None
        warnings = []
        if ver and ver.schema_metadata:
            manifest_key = ver.schema_metadata.get("manifest_key")
            if manifest_key:
                storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
                manifest_path = storage_root / manifest_key
                if manifest_path.is_file():
                    import json
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    warnings = manifest.get("warnings", [])

        return {
            "dataset_id": dataset.id,
            "status": dataset.status,
            "processing_stage": "completed" if dataset.status == "ready" else dataset.status,
            "rows_processed": dataset.row_count,
            "total_rows": dataset.row_count,
            "warnings": warnings,
            "error_message": error_msg,
        }
