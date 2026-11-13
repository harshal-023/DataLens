import calendar
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business_report import BusinessReport, ReportRun, ReportSchedule
from app.models.workspace import Workspace
from app.services.reports.business_report_export import BusinessReportExportService
from app.services.reports.email_delivery import EmailDeliveryService
from app.services.reports.report_assembly import ReportAssemblyEngine

logger = logging.getLogger("datalens.reports.scheduler")


def _resolve_tz(tz_str: str):
    if not tz_str or tz_str.upper() in ("UTC", "GMT", "ETC/UTC"):
        return UTC
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_str)
    except Exception:
        return UTC


class ReportSchedulerService:
    """
    Timezone-aware recurring report scheduler.
    Orchestrates automated report generation, persistence, status tracking, and delivery.
    """

    @classmethod
    def calculate_next_run(
        cls,
        frequency: str,
        hour: int = 8,
        minute: int = 0,
        day_of_week: int | None = None,
        day_of_month: int | None = None,
        tz_str: str = "UTC",
        base_time: datetime | None = None,
    ) -> datetime:
        """
        Calculates the next execution timestamp in UTC for daily, weekly, or monthly schedules.
        """
        tz = _resolve_tz(tz_str)

        now = base_time or datetime.now(tz)
        now = now.replace(tzinfo=tz) if now.tzinfo is None else now.astimezone(tz)

        freq = frequency.lower().strip()

        if freq == "daily":
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate.astimezone(UTC)

        elif freq == "weekly":
            dow = day_of_week if day_of_week is not None else 0  # 0=Monday
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = (dow - now.weekday()) % 7
            if days_ahead == 0 and candidate <= now:
                days_ahead = 7
            candidate += timedelta(days=days_ahead)
            return candidate.astimezone(UTC)

        elif freq == "monthly":
            dom = day_of_month if day_of_month is not None else 1
            year = now.year
            month = now.month

            # Try this month
            max_days = calendar.monthrange(year, month)[1]
            clamped_day = min(dom, max_days)
            candidate = now.replace(year=year, month=month, day=clamped_day, hour=hour, minute=minute, second=0, microsecond=0)

            if candidate <= now:
                # Next month
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                max_days = calendar.monthrange(year, month)[1]
                clamped_day = min(dom, max_days)
                candidate = now.replace(year=year, month=month, day=clamped_day, hour=hour, minute=minute, second=0, microsecond=0)

            return candidate.astimezone(UTC)

        else:
            # Default fallback: 24h from now
            return (now + timedelta(days=1)).astimezone(UTC)

    @classmethod
    async def execute_schedule(
        cls,
        schedule: ReportSchedule,
        db: AsyncSession,
    ) -> ReportRun:
        """
        Executes a due scheduled report, saves outputs to disk, updates status, and delivers emails.
        """
        start_time = time.time()
        logger.info(f"Executing scheduled report run for schedule {schedule.id} (report: {schedule.report_id})")

        # 1. Fetch Report & Workspace
        report = await db.get(BusinessReport, schedule.report_id)
        if not report:
            raise ValueError(f"Report {schedule.report_id} not found.")

        workspace = await db.get(Workspace, schedule.workspace_id)
        workspace_name = workspace.name if workspace else "DataLens Workspace"

        # 2. Advance next execution time immediately (Concurrency / Idempotency protection)
        next_run = cls.calculate_next_run(
            frequency=schedule.frequency,
            hour=schedule.hour,
            minute=schedule.minute,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
            tz_str=schedule.timezone,
        )
        schedule.next_execution_time = next_run
        schedule.last_execution_time = datetime.now(UTC)
        schedule.last_execution_status = "running"
        await db.commit()

        # 3. Create ReportRun record
        run = ReportRun(
            report_id=report.id,
            workspace_id=schedule.workspace_id,
            triggered_by=schedule.created_by,
            trigger_type="scheduled",
            execution_status="running",
            report_period=f"{datetime.now(UTC).strftime('%Y-%m-%d')} Automated Run",
            applied_filters=[],
            source_provenance={},
            generated_files={},
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            # 4. Assemble Evidence
            evidence = await ReportAssemblyEngine.assemble_report_evidence(
                workspace_id=schedule.workspace_id,
                report=report,
                runtime_filters=[],
                period=run.report_period,
                db=db,
            )

            # 5. Generate Formats
            storage_root = Path(getattr(settings, "STORAGE_ROOT", "./storage_data")).resolve()
            run_dir = storage_root / "reports" / str(schedule.workspace_id) / str(run.id)
            run_dir.mkdir(parents=True, exist_ok=True)

            delivery_cfg = schedule.delivery_configuration or {}
            requested_formats = delivery_cfg.get("attach_formats", ["pdf"])
            generated_files = {}
            attachments = {}

            # Generate PDF
            if "pdf" in requested_formats or not requested_formats:
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
                attachments[f"{report.title}.pdf"] = pdf_bytes

            # Generate DOCX
            if "docx" in requested_formats:
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
                attachments[f"{report.title}.docx"] = docx_bytes

            # Generate XLSX
            if "xlsx" in requested_formats:
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
                attachments[f"{report.title}.xlsx"] = xlsx_bytes

            # Generate CSV
            if "csv" in requested_formats:
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
                attachments[f"{report.title}.csv"] = csv_bytes

            # 6. Email Delivery
            recipients = delivery_cfg.get("email_recipients", [])
            if recipients and attachments:
                await EmailDeliveryService.deliver_report(
                    report_title=report.title,
                    recipients=recipients,
                    attachments=attachments,
                    period=run.report_period,
                    workspace_name=workspace_name,
                )

            # 7. Finalize Run
            duration_ms = int((time.time() - start_time) * 1000)
            run.execution_status = "completed"
            run.generated_files = generated_files
            run.source_provenance = evidence.get("provenance", [])
            run.ai_generated = evidence.get("ai_generated", False)
            run.execution_duration_ms = duration_ms
            schedule.last_execution_status = "success"

        except Exception as e:
            logger.error(f"Scheduled report execution failed: {e}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            run.execution_status = "failed"
            run.error_details = str(e)
            run.execution_duration_ms = duration_ms
            schedule.last_execution_status = "failure"

        await db.commit()
        await db.refresh(run)
        return run

    @classmethod
    async def trigger_due_schedules(cls, db: AsyncSession) -> list[ReportRun]:
        """
        Polls for due schedules and executes them sequentially.
        """
        now = datetime.now(UTC)
        stmt = (
            select(ReportSchedule)
            .where(
                ReportSchedule.is_enabled.is_(True),
                ReportSchedule.next_execution_time <= now,
            )
            .order_by(ReportSchedule.next_execution_time.asc())
        )
        res = await db.execute(stmt)
        schedules = res.scalars().all()

        runs = []
        for sched in schedules:
            try:
                run = await cls.execute_schedule(sched, db)
                runs.append(run)
            except Exception as e:
                logger.error(f"Error triggering schedule {sched.id}: {e}")

        return runs
