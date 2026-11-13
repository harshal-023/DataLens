import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.business_report import (
    BusinessReport,
    ReportRun,
    ReportSchedule,
    ReportTemplate,
)
from app.services.reports.business_report_export import BusinessReportExportService
from app.services.reports.report_assembly import ReportAssemblyEngine
from app.services.reports.scheduler_service import ReportSchedulerService
from app.services.reports.templates import SYSTEM_REPORT_TEMPLATES


class BusinessReportService:
    """
    Core management service for DataLens Phase 4D Business Reporting.
    Handles report templates, configuration, manual/scheduled execution, and run history.
    """

    # -------------------------------------------------------------------------
    # TEMPLATES
    # -------------------------------------------------------------------------
    @classmethod
    async def list_templates(
        cls,
        workspace_id: uuid.UUID,
        category: str | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """
        Returns system templates combined with custom workspace templates.
        """
        templates = list(SYSTEM_REPORT_TEMPLATES)

        if db:
            stmt = select(ReportTemplate).where(
                (ReportTemplate.workspace_id == workspace_id) | (ReportTemplate.is_system.is_(True))
            )
            if category:
                stmt = stmt.where(ReportTemplate.category == category)
            res = await db.execute(stmt)
            db_templates = res.scalars().all()
            for t in db_templates:
                if not any(st["id"] == str(t.id) for st in templates):
                    templates.append({
                        "id": str(t.id),
                        "name": t.name,
                        "category": t.category,
                        "description": t.description,
                        "template_config": t.template_config,
                        "default_sections": t.default_sections,
                        "is_system": t.is_system,
                    })

        if category:
            templates = [t for t in templates if t["category"] == category]

        return templates

    @classmethod
    async def get_template(
        cls,
        template_id: str,
        workspace_id: uuid.UUID,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        for st in SYSTEM_REPORT_TEMPLATES:
            if st["id"] == template_id:
                return st

        if db:
            try:
                t_uuid = uuid.UUID(template_id)
                stmt = select(ReportTemplate).where(
                    ReportTemplate.id == t_uuid,
                    (ReportTemplate.workspace_id == workspace_id) | (ReportTemplate.is_system.is_(True)),
                )
                t = (await db.execute(stmt)).scalar_one_or_none()
                if t:
                    return {
                        "id": str(t.id),
                        "name": t.name,
                        "category": t.category,
                        "description": t.description,
                        "template_config": t.template_config,
                        "default_sections": t.default_sections,
                        "is_system": t.is_system,
                    }
            except Exception:
                pass

        raise DataLensException(f"Template '{template_id}' not found.", code="NOT_FOUND")

    # -------------------------------------------------------------------------
    # REPORTS CRUD
    # -------------------------------------------------------------------------
    @classmethod
    async def create_report(
        cls,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID | None,
        title: str,
        description: str | None,
        report_type: str,
        template_id: str | None,
        configuration: dict[str, Any],
        source_dashboard_ids: list[str] | None,
        source_dataset_refs: list[dict[str, Any]] | None,
        source_model_run_refs: list[dict[str, Any]] | None,
        db: AsyncSession,
    ) -> BusinessReport:
        # If template provided and sections missing, load default sections from template
        if template_id and not configuration.get("sections"):
            try:
                tpl = await cls.get_template(template_id, workspace_id, db)
                configuration["sections"] = tpl.get("default_sections", [])
                if not configuration.get("branding"):
                    configuration["branding"] = tpl.get("template_config", {})
            except Exception:
                pass

        tpl_uuid = None
        if template_id:
            try:
                tpl_uuid = uuid.UUID(template_id)
            except Exception:
                tpl_uuid = None

        report = BusinessReport(
            workspace_id=workspace_id,
            owner_id=owner_id,
            template_id=tpl_uuid,
            title=title.strip(),
            description=description.strip() if description else None,
            report_type=report_type or "custom",
            status="published",
            configuration=configuration or {},
            source_dashboard_ids=source_dashboard_ids or [],
            source_dataset_refs=source_dataset_refs or [],
            source_model_run_refs=source_model_run_refs or [],
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        report.runs = []
        report.schedules = []
        return report

    @classmethod
    async def get_report(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> BusinessReport:
        stmt = (
            select(BusinessReport)
            .options(
                selectinload(BusinessReport.runs),
                selectinload(BusinessReport.schedules),
            )
            .where(
                BusinessReport.id == report_id,
                BusinessReport.workspace_id == workspace_id,
            )
        )
        report = (await db.execute(stmt)).scalar_one_or_none()
        if not report:
            raise DataLensException("Report not found in this workspace.", code="NOT_FOUND")
        return report

    @classmethod
    async def update_report(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> BusinessReport:
        report = await cls.get_report(report_id, workspace_id, db)

        for key, val in payload.items():
            if hasattr(report, key) and val is not None:
                setattr(report, key, val)

        report.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def delete_report(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        report = await cls.get_report(report_id, workspace_id, db)
        await db.delete(report)
        await db.commit()

    @classmethod
    async def duplicate_report(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> BusinessReport:
        original = await cls.get_report(report_id, workspace_id, db)
        duplicated = BusinessReport(
            workspace_id=workspace_id,
            owner_id=owner_id,
            template_id=original.template_id,
            title=f"{original.title} (Copy)",
            description=original.description,
            report_type=original.report_type,
            status=original.status,
            configuration=dict(original.configuration),
            source_dashboard_ids=list(original.source_dashboard_ids),
            source_dataset_refs=list(original.source_dataset_refs),
            source_model_run_refs=list(original.source_model_run_refs),
        )
        db.add(duplicated)
        await db.commit()
        await db.refresh(duplicated)
        duplicated.runs = []
        duplicated.schedules = []
        return duplicated

    @classmethod
    async def list_reports(
        cls,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        report_type: str | None = None,
        search: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        if not db:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 1}

        stmt = select(BusinessReport).where(BusinessReport.workspace_id == workspace_id)
        if report_type:
            stmt = stmt.where(BusinessReport.report_type == report_type)
        if search:
            stmt = stmt.where(BusinessReport.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            stmt.options(
                selectinload(BusinessReport.runs),
                selectinload(BusinessReport.schedules),
            )
            .order_by(BusinessReport.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        reports = (await db.execute(stmt)).scalars().all()
        total_pages = max(1, (total + page_size - 1) // page_size)

        return {
            "items": reports,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # -------------------------------------------------------------------------
    # MANUAL REPORT GENERATION & EXECUTION
    # -------------------------------------------------------------------------
    @classmethod
    async def generate_report_run(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        period: str | None,
        formats: list[str] | None,
        applied_filters: list[dict[str, Any]] | None,
        db: AsyncSession,
    ) -> ReportRun:
        start_time = time.time()
        report = await cls.get_report(report_id, workspace_id, db)

        run = ReportRun(
            report_id=report.id,
            workspace_id=workspace_id,
            triggered_by=triggered_by,
            trigger_type="manual",
            execution_status="running",
            report_period=period or report.configuration.get("period", "Current Period"),
            applied_filters=applied_filters or [],
            source_provenance={},
            generated_files={},
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            # 1. Assemble Evidence
            evidence = await ReportAssemblyEngine.assemble_report_evidence(
                workspace_id=workspace_id,
                report=report,
                runtime_filters=applied_filters or [],
                period=run.report_period,
                db=db,
            )

            # 2. Output File Directory
            storage_root = Path(getattr(settings, "STORAGE_ROOT", "./storage_data")).resolve()
            run_dir = storage_root / "reports" / str(workspace_id) / str(run.id)
            run_dir.mkdir(parents=True, exist_ok=True)

            requested = formats or ["pdf", "docx", "xlsx", "csv"]
            generated_files = {}

            # PDF
            if "pdf" in requested:
                pdf_bytes = BusinessReportExportService.generate_pdf(evidence)
                pdf_path = run_dir / "report.pdf"
                pdf_path.write_bytes(pdf_bytes)
                rel_path = str(pdf_path.relative_to(storage_root)).replace("\\", "/")
                generated_files["pdf"] = {
                    "storage_key": rel_path,
                    "file_size": len(pdf_bytes),
                    "filename": f"{report.title.lower().replace(' ', '_')}.pdf",
                    "media_type": "application/pdf",
                }

            # DOCX
            if "docx" in requested:
                docx_bytes = BusinessReportExportService.generate_docx(evidence)
                docx_path = run_dir / "report.docx"
                docx_path.write_bytes(docx_bytes)
                rel_path = str(docx_path.relative_to(storage_root)).replace("\\", "/")
                generated_files["docx"] = {
                    "storage_key": rel_path,
                    "file_size": len(docx_bytes),
                    "filename": f"{report.title.lower().replace(' ', '_')}.docx",
                    "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                }

            # XLSX
            if "xlsx" in requested:
                xlsx_bytes = BusinessReportExportService.generate_xlsx(evidence)
                xlsx_path = run_dir / "report.xlsx"
                xlsx_path.write_bytes(xlsx_bytes)
                rel_path = str(xlsx_path.relative_to(storage_root)).replace("\\", "/")
                generated_files["xlsx"] = {
                    "storage_key": rel_path,
                    "file_size": len(xlsx_bytes),
                    "filename": f"{report.title.lower().replace(' ', '_')}.xlsx",
                    "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }

            # CSV
            if "csv" in requested:
                csv_bytes = BusinessReportExportService.generate_csv(evidence)
                csv_path = run_dir / "report.csv"
                csv_path.write_bytes(csv_bytes)
                rel_path = str(csv_path.relative_to(storage_root)).replace("\\", "/")
                generated_files["csv"] = {
                    "storage_key": rel_path,
                    "file_size": len(csv_bytes),
                    "filename": f"{report.title.lower().replace(' ', '_')}.csv",
                    "media_type": "text/csv",
                }

            duration_ms = int((time.time() - start_time) * 1000)
            run.execution_status = "completed"
            run.generated_files = generated_files
            run.source_provenance = evidence.get("provenance", [])
            run.ai_generated = evidence.get("ai_generated", False)
            run.execution_duration_ms = duration_ms

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            run.execution_status = "failed"
            run.error_details = str(e)
            run.execution_duration_ms = duration_ms

        await db.commit()
        await db.refresh(run)
        return run

    @classmethod
    async def list_report_runs(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[ReportRun]:
        stmt = (
            select(ReportRun)
            .where(
                ReportRun.report_id == report_id,
                ReportRun.workspace_id == workspace_id,
            )
            .order_by(ReportRun.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_run_file(
        cls,
        run_id: uuid.UUID,
        format_type: str,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[bytes, str, str]:
        """
        Returns: (file_bytes, media_type, filename)
        """
        run = await db.get(ReportRun, run_id)
        if not run or run.workspace_id != workspace_id:
            raise DataLensException("Report execution record not found.", code="NOT_FOUND")

        clean_fmt = format_type.lower().strip()
        file_meta = run.generated_files.get(clean_fmt)
        if not file_meta or not file_meta.get("storage_key"):
            raise DataLensException(f"Format '{clean_fmt}' not available for this report run.", code="NOT_FOUND")

        storage_root = Path(getattr(settings, "STORAGE_ROOT", "./storage_data")).resolve()
        file_path = storage_root / file_meta["storage_key"]
        if not file_path.is_file():
            raise DataLensException("Report file missing from disk storage.", code="STORAGE_NOT_FOUND")

        return (
            file_path.read_bytes(),
            file_meta.get("media_type", "application/octet-stream"),
            file_meta.get("filename", f"report.{clean_fmt}"),
        )

    # -------------------------------------------------------------------------
    # SCHEDULES CRUD
    # -------------------------------------------------------------------------
    @classmethod
    async def create_schedule(
        cls,
        report_id: uuid.UUID,
        workspace_id: uuid.UUID,
        created_by: uuid.UUID | None,
        frequency: str,
        hour: int,
        minute: int,
        day_of_week: int | None,
        day_of_month: int | None,
        timezone: str,
        delivery_configuration: dict[str, Any] | None,
        db: AsyncSession,
    ) -> ReportSchedule:
        # Verify report exists in workspace
        await cls.get_report(report_id, workspace_id, db)

        next_run = ReportSchedulerService.calculate_next_run(
            frequency=frequency,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            tz_str=timezone,
        )

        schedule = ReportSchedule(
            report_id=report_id,
            workspace_id=workspace_id,
            created_by=created_by,
            frequency=frequency,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            timezone=timezone,
            next_execution_time=next_run,
            is_enabled=True,
            delivery_configuration=delivery_configuration or {},
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    @classmethod
    async def update_schedule(
        cls,
        schedule_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> ReportSchedule:
        schedule = await db.get(ReportSchedule, schedule_id)
        if not schedule or schedule.workspace_id != workspace_id:
            raise DataLensException("Report schedule not found.", code="NOT_FOUND")

        for k, v in payload.items():
            if hasattr(schedule, k) and v is not None:
                setattr(schedule, k, v)

        # Recalculate next execution time if timing parameters changed
        schedule.next_execution_time = ReportSchedulerService.calculate_next_run(
            frequency=schedule.frequency,
            hour=schedule.hour,
            minute=schedule.minute,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
            tz_str=schedule.timezone,
        )
        schedule.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    @classmethod
    async def delete_schedule(
        cls,
        schedule_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        schedule = await db.get(ReportSchedule, schedule_id)
        if not schedule or schedule.workspace_id != workspace_id:
            raise DataLensException("Report schedule not found.", code="NOT_FOUND")
        await db.delete(schedule)
        await db.commit()
