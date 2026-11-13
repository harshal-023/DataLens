"""Scheduled refresh service for external data sources."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import DataSourceConnection, DataSourceImport, DataSourceRefreshConfig
from app.services.connectors.import_engine import ImportEngine


class RefreshSchedulerService:
    """Manages scheduled refreshes and automated syncs for external connections."""

    @classmethod
    def calculate_next_run(
        cls,
        frequency: str,
        from_time: datetime | None = None,
        cron_expression: str | None = None,
    ) -> datetime:
        base = from_time or datetime.now(UTC)
        freq = frequency.lower()
        if freq == "hourly":
            return base + timedelta(hours=1)
        elif freq == "daily":
            return base + timedelta(days=1)
        elif freq == "weekly":
            return base + timedelta(weeks=1)
        elif freq == "custom_cron" and cron_expression:
            try:
                from croniter import croniter
                iter_cron = croniter(cron_expression, base)
                return iter_cron.get_next(datetime)
            except Exception:
                return base + timedelta(days=1)
        # Default daily
        return base + timedelta(days=1)

    @classmethod
    async def trigger_due_refreshes(cls, db: AsyncSession) -> list[DataSourceImport]:
        """Inspect all active refresh configs and run due import operations."""
        now = datetime.now(UTC)
        stmt = (
            select(DataSourceRefreshConfig)
            .where(
                DataSourceRefreshConfig.is_active.is_(True),
                DataSourceRefreshConfig.next_run_at <= now,
            )
        )
        res = await db.execute(stmt)
        configs = res.scalars().all()

        executed_imports: list[DataSourceImport] = []

        for config in configs:
            try:
                # Find associated connection
                conn_res = await db.execute(
                    select(DataSourceConnection).where(DataSourceConnection.id == config.connection_id)
                )
                conn = conn_res.scalar_one_or_none()
                if not conn or not conn.is_active:
                    continue

                # Run import
                imp = await ImportEngine.execute_import(
                    db=db,
                    connection_id=conn.id,
                    resource_path=config.target_resource,
                    user_id=conn.created_by,
                    import_mode=config.refresh_mode,
                    target_dataset_id=config.dataset_id,
                    watermark_column=config.watermark_column,
                )
                executed_imports.append(imp)

                # Update schedule
                config.last_run_at = now
                config.next_run_at = cls.calculate_next_run(
                    config.frequency,
                    from_time=now,
                    cron_expression=config.cron_expression,
                )
                await db.commit()
            except Exception:
                # Log and continue next config without breaking the batch
                await db.rollback()
                config.last_run_at = now
                config.next_run_at = cls.calculate_next_run(
                    config.frequency,
                    from_time=now,
                    cron_expression=config.cron_expression,
                )
                await db.commit()

        return executed_imports
