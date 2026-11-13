import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.report import Report
from app.services.analytics.engine import AnalyticsEngine
from app.services.reports.csv_generator import generate_csv_report
from app.services.reports.docx_generator import generate_docx_report
from app.services.reports.pdf_generator import generate_pdf_report
from app.services.reports.xlsx_generator import generate_xlsx_report
from app.storage import get_storage_backend


class ReportService:
    ALLOWED_FORMATS = {"pdf", "docx", "xlsx", "csv"}

    @classmethod
    async def create_report(
        cls,
        workspace_id: uuid.UUID,
        creator_id: uuid.UUID,
        dataset_id: uuid.UUID,
        title: str,
        report_format: str,
        version_id: uuid.UUID | None,
        report_config: dict[str, Any] | None,
        db: AsyncSession,
    ) -> Report:
        clean_format = report_format.lower().strip()
        if clean_format not in cls.ALLOWED_FORMATS:
            raise DataLensException(
                f"Unsupported report format '{clean_format}'. Allowed: {', '.join(cls.ALLOWED_FORMATS)}.",
                code="INVALID_FORMAT",
            )

        # 1. Fetch Dataset & Version
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

        target_ver_id = version_id or dataset.current_version_id
        if not target_ver_id:
            raise DataLensException("Dataset has no active version to report on.", code="NOT_FOUND")

        ver_stmt = select(DatasetVersion).where(
            DatasetVersion.id == target_ver_id,
            DatasetVersion.dataset_id == dataset.id,
        )
        version = (await db.execute(ver_stmt)).scalar_one_or_none()
        if not version:
            raise DataLensException("Dataset version not found.", code="NOT_FOUND")

        # 2. Gather Parquet Part Files
        storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
        import json

        manifest_path = storage_root / version.storage_key
        if not manifest_path.is_file():
            raise DataLensException("Dataset manifest not found on disk.", code="STORAGE_NOT_FOUND")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parquet_paths = [storage_root / p for p in manifest.get("parts", [])]
        columns_meta = manifest.get("columns", [])

        # 3. Compute Analytics
        profile_res = AnalyticsEngine.compute_profiling(
            parquet_files=parquet_paths,
            columns_meta=columns_meta,
            dataset_id=dataset.id,
            version_id=str(version.id),
        )

        stats_res = AnalyticsEngine.compute_descriptive_stats(
            parquet_files=parquet_paths,
            columns_meta=columns_meta,
            target_columns=None,
            filters=None,
            version_id=str(version.id),
        )

        quality_res = AnalyticsEngine.compute_data_quality(
            parquet_files=parquet_paths,
            columns_meta=columns_meta,
            version_id=str(version.id),
        )

        # Compute default aggregation if grouping column specified or detected
        agg_data = None
        group_cols = [c["name"] for c in columns_meta if c.get("inferred_type") == "string"][:1]
        metric_cols = [c["name"] for c in columns_meta if c.get("inferred_type") in ("integer", "float", "number")][:1]
        if group_cols and metric_cols:
            agg_resp = AnalyticsEngine.compute_aggregation(
                parquet_files=parquet_paths,
                group_by_columns=group_cols,
                metric_column=metric_cols[0],
                aggregation="sum",
                sort_order="desc",
                limit=15,
                filters=None,
                version_id=str(version.id),
            )
            agg_data = agg_resp.model_dump()

        profile_dict = profile_res.model_dump()
        stats_dict = stats_res.model_dump()
        quality_dict = quality_res.model_dump()

        # 4. Generate Document File
        report_id = uuid.uuid4()
        if clean_format == "pdf":
            file_bytes = generate_pdf_report(
                title=title,
                dataset_name=dataset.name,
                version_number=version.version_number,
                workspace_name="DataLens Workspace",
                profile_data=profile_dict,
                stats_data=stats_dict,
                agg_data=agg_data,
                quality_data=quality_dict,
            )
        elif clean_format == "docx":
            file_bytes = generate_docx_report(
                title=title,
                dataset_name=dataset.name,
                version_number=version.version_number,
                workspace_name="DataLens Workspace",
                profile_data=profile_dict,
                stats_data=stats_dict,
                agg_data=agg_data,
                quality_data=quality_dict,
            )
        elif clean_format == "xlsx":
            file_bytes = generate_xlsx_report(
                title=title,
                dataset_name=dataset.name,
                version_number=version.version_number,
                workspace_name="DataLens Workspace",
                profile_data=profile_dict,
                stats_data=stats_dict,
                agg_data=agg_data,
                quality_data=quality_dict,
            )
        else:  # csv
            file_bytes = generate_csv_report(
                agg_data=agg_data,
                stats_data=stats_dict,
            )

        # 5. Persist Binary in Storage
        storage_key = f"reports/{workspace_id}/{report_id}/report.{clean_format}"
        storage = get_storage_backend()
        await storage.save_file(storage_key, file_bytes)

        # 6. Save Report Record
        report = Report(
            id=report_id,
            workspace_id=workspace_id,
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            created_by=creator_id,
            title=title.strip() or f"{dataset.name} Business Report",
            format=clean_format,
            status="published",
            storage_key=storage_key,
            file_size=len(file_bytes),
            report_config=report_config or {
                "generated_at": datetime.now(UTC).isoformat(),
                "dataset_name": dataset.name,
                "version_number": version.version_number,
            },
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def list_reports(
        cls,
        workspace_id: uuid.UUID,
        page: int,
        page_size: int,
        dataset_id: uuid.UUID | None,
        format_filter: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        base_query = select(Report).where(Report.workspace_id == workspace_id)

        if dataset_id:
            base_query = base_query.where(Report.dataset_id == dataset_id)

        if format_filter and format_filter.lower() != "all":
            base_query = base_query.where(Report.format == format_filter.lower())

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        paged_stmt = (
            base_query.order_by(desc(Report.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await db.execute(paged_stmt)).scalars().all()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def get_report(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Report:
        stmt = (
            select(Report)
            .options(
                selectinload(Report.dataset),
                selectinload(Report.dataset_version),
            )
            .where(Report.id == report_id, Report.workspace_id == workspace_id)
        )
        report = (await db.execute(stmt)).scalar_one_or_none()
        if not report:
            raise DataLensException("Report not found in this workspace.", code="NOT_FOUND")
        return report

    @classmethod
    async def download_report_file(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[bytes, str, str]:
        report = await cls.get_report(report_id, workspace_id, db)
        if not report.storage_key:
            raise DataLensException("Report file is not available.", code="NOT_FOUND")

        storage = get_storage_backend()
        data = await storage.read_file(report.storage_key)

        mimes = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
        }
        mime = mimes.get(report.format, "application/octet-stream")
        safe_title = "".join(c for c in report.title if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"{safe_title}.{report.format}"
        return data, filename, mime

    @classmethod
    async def delete_report(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        report = await cls.get_report(report_id, workspace_id, db)
        if report.storage_key:
            storage = get_storage_backend()
            import contextlib
            with contextlib.suppress(Exception):
                await storage.delete_file(report.storage_key)

        await db.delete(report)
        await db.commit()

