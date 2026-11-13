"""Comprehensive unit and integration test suite for Phase 5D: Automated Data Refresh, Pipeline Orchestration & Background Jobs."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.automation import (
    BackgroundJob,
)
from app.models.user import User
from app.schemas.automation import (
    DataQualityRuleConfig,
    ErrorClassification,
    JobStatus,
    WorkflowStepCreate,
)
from app.services.automation.job_service import BackgroundJobService
from app.services.automation.quality_service import DataQualityService
from app.services.automation.scheduler_service import AutomationScheduler
from app.services.automation.workflow_service import WorkflowDAGService


@pytest.fixture
def mock_owner():
    return User(
        id=uuid.uuid4(),
        email="owner@datalens.app",
        full_name="Workspace Owner",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 1. Scheduling Engine & Cron Parsing
# ---------------------------------------------------------------------------


def test_schedule_calculation_daily():
    """Verify daily schedule calculates next run accurately."""
    base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)
    next_run = AutomationScheduler.calculate_next_run(
        frequency="daily",
        timezone_str="UTC",
        hour=14,
        minute=30,
        base_time=base_time,
    )
    assert next_run == datetime(2026, 11, 12, 14, 30, 0, tzinfo=UTC)


def test_schedule_calculation_weekly():
    """Verify weekly schedule advances to requested day of week."""
    # 2026-11-12 is a Thursday (weekday=3)
    base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)
    # Next Monday (0)
    next_run = AutomationScheduler.calculate_next_run(
        frequency="weekly",
        timezone_str="UTC",
        hour=8,
        minute=0,
        day_of_week=0,
        base_time=base_time,
    )
    # Next Monday is Nov 16, 2026
    assert next_run.weekday() == 0
    assert next_run.hour == 8
    assert next_run.day == 16


def test_schedule_cron_expression():
    """Verify standard 5-field cron parsing (minute hour dom month dow)."""
    base_time = datetime(2026, 11, 12, 8, 15, 0, tzinfo=UTC)
    # Every 15 minutes
    next_run = AutomationScheduler.calculate_next_run(
        frequency="cron",
        cron_expression="*/15 * * * *",
        base_time=base_time,
    )
    assert next_run == datetime(2026, 11, 12, 8, 30, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# 2. Workflow DAG & Circular Dependency Detection
# ---------------------------------------------------------------------------


def test_workflow_dag_valid_sequence():
    """Verify valid DAG resolves into proper topological order."""
    step_a = WorkflowStepCreate(step_name="Ingest", step_type="SOURCE_REFRESH", depends_on_step_ids=[])
    step_b = WorkflowStepCreate(step_name="Validate", step_type="DATA_VALIDATION", depends_on_step_ids=["Ingest"])
    step_c = WorkflowStepCreate(step_name="Transform", step_type="TRANSFORMATION", depends_on_step_ids=["Validate"])

    val = WorkflowDAGService.validate_and_sort_steps([step_a, step_b, step_c])
    assert val.is_valid is True
    assert len(val.errors) == 0
    assert val.topological_order == ["Ingest", "Validate", "Transform"]


def test_workflow_dag_circular_dependency_rejection():
    """Verify circular dependency is detected and rejected."""
    step_a = WorkflowStepCreate(step_name="A", step_type="TRANSFORMATION", depends_on_step_ids=["B"])
    step_b = WorkflowStepCreate(step_name="B", step_type="TRANSFORMATION", depends_on_step_ids=["A"])

    val = WorkflowDAGService.validate_and_sort_steps([step_a, step_b])
    assert val.is_valid is False
    assert any("Circular dependency" in err for err in val.errors)


# ---------------------------------------------------------------------------
# 3. Data Quality Gateways
# ---------------------------------------------------------------------------


def test_data_quality_validation_gate():
    """Verify data quality rules check required columns, nulls, and duplicate bounds."""
    config = DataQualityRuleConfig(
        required_columns=["customer_id", "email"],
        max_null_pct=15.0,
        max_duplicate_pct=5.0,
        min_row_count=2,
        on_failure="BLOCK",
    )

    valid_rows = [
        {"customer_id": "C1", "email": "c1@test.com"},
        {"customer_id": "C2", "email": "c2@test.com"},
    ]
    res_pass = DataQualityService.validate_dataset_records(valid_rows, ["customer_id", "email"], config)
    assert res_pass.passed is True
    assert len(res_pass.issues) == 0

    # Test missing column failure
    res_fail = DataQualityService.validate_dataset_records(valid_rows, ["customer_id"], config)
    assert res_fail.passed is False
    assert any("Missing required columns" in issue for issue in res_fail.issues)


# ---------------------------------------------------------------------------
# 4. Background Job Lifecycle & Retries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_enqueue_and_idempotency(mock_owner):
    """Verify job enqueueing with idempotency deduplication."""
    db = AsyncMock()
    ws_id = uuid.uuid4()
    idem_key = "sync_pg_20261112"

    # Simulate no existing job
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = None
    db.execute.return_value = exec_res

    job = await BackgroundJobService.enqueue_job(
        db=db,
        workspace_id=ws_id,
        job_type="data_import",
        payload={"connection_id": str(uuid.uuid4())},
        idempotency_key=idem_key,
        created_by=mock_owner.id,
    )
    assert job.status == JobStatus.QUEUED.value
    assert job.idempotency_key == idem_key
    assert db.add.called


@pytest.mark.asyncio
async def test_job_exponential_backoff_retry():
    """Verify transient failures trigger exponential backoff retry."""
    db = AsyncMock()
    job_id = uuid.uuid4()

    mock_job = BackgroundJob(
        id=job_id,
        workspace_id=uuid.uuid4(),
        job_type="data_import",
        status=JobStatus.RUNNING.value,
        retry_count=0,
        max_retries=3,
        retry_delay_seconds=10,
    )
    db.get.return_value = mock_job

    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = None
    db.execute.return_value = exec_res

    updated_job = await BackgroundJobService.fail_job(
        db=db,
        job_id=job_id,
        error_message="Connection reset by peer",
        error_classification=ErrorClassification.TRANSIENT.value,
    )
    assert updated_job.retry_count == 1
    assert updated_job.status == JobStatus.QUEUED.value
    assert updated_job.scheduled_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_job_permanent_failure_no_retry():
    """Verify permanent errors (e.g. invalid credentials) fail immediately without retry."""
    db = AsyncMock()
    job_id = uuid.uuid4()

    mock_job = BackgroundJob(
        id=job_id,
        workspace_id=uuid.uuid4(),
        job_type="data_import",
        status=JobStatus.RUNNING.value,
        retry_count=0,
        max_retries=3,
        retry_delay_seconds=10,
    )
    db.get.return_value = mock_job

    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = None
    db.execute.return_value = exec_res

    updated_job = await BackgroundJobService.fail_job(
        db=db,
        job_id=job_id,
        error_message="Invalid credentials 401",
        error_classification=ErrorClassification.AUTHENTICATION.value,
    )
    assert updated_job.status == JobStatus.FAILED.value
    assert updated_job.retry_count == 0


@pytest.mark.asyncio
async def test_stale_job_recovery_on_worker_crash():
    """Verify crashed worker jobs (> timeout) are recovered."""
    db = AsyncMock()
    stale_job = BackgroundJob(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        job_type="pipeline_execution",
        status=JobStatus.RUNNING.value,
        heartbeat_at=datetime.now(UTC) - timedelta(minutes=20),
        worker_id="worker_crashed_1",
        retry_count=0,
        max_retries=2,
        retry_delay_seconds=5,
    )
    db.get.return_value = stale_job

    exec_res = MagicMock()
    exec_res.scalars.return_value.all.return_value = [stale_job]
    exec_res.scalar_one_or_none.return_value = None
    db.execute.return_value = exec_res

    recovered = await BackgroundJobService.recover_stale_jobs(db, stale_threshold_seconds=600)
    assert recovered == 1
