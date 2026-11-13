"""API endpoints for Phase 5D: Automated Data Refresh, Pipeline Orchestration & Background Job Management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.automation import (
    BackgroundJob,
    JobSchedule,
    Workflow,
    WorkflowExecution,
    WorkflowStep,
    WorkflowStepExecution,
)
from app.models.user import User
from app.models.workspace import WorkspaceMembership
from app.schemas.automation import (
    AutomationOverviewResponse,
    BackgroundJobCreate,
    BackgroundJobListResponse,
    BackgroundJobResponse,
    JobScheduleCreate,
    JobScheduleListResponse,
    JobScheduleResponse,
    JobScheduleUpdate,
    WorkflowCreate,
    WorkflowExecutionListResponse,
    WorkflowExecutionResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowValidationResponse,
)
from app.services.automation.job_service import BackgroundJobService
from app.services.automation.scheduler_service import AutomationScheduler
from app.services.automation.workflow_service import WorkflowDAGService
from app.services.governance_service import GovernanceService

router = APIRouter(prefix="/automation", tags=["automation"])


# ---------------------------------------------------------------------------
# Helpers: Authorization
# ---------------------------------------------------------------------------


async def _assert_workspace_access(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user: User,
    permission_code: str | None = None,
) -> None:
    """Ensure user belongs to workspace and possesses the requested permission."""
    stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == user.id,
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    if permission_code:
        has_perm = await GovernanceService.has_workspace_permission(
            db=db,
            workspace_id=workspace_id,
            user=user,
            permission_code=permission_code,
        )
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_code}' required for this operation",
            )


# ---------------------------------------------------------------------------
# Overview & Metrics
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=AutomationOverviewResponse)
async def get_automation_overview(
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> AutomationOverviewResponse:
    """Get high-level summary metrics, active schedules, and recent jobs for workspace."""
    await _assert_workspace_access(db, workspace_id, current_user)

    # Active schedules count
    active_sched_stmt = select(func.count(JobSchedule.id)).where(
        JobSchedule.workspace_id == workspace_id,
        JobSchedule.is_active.is_(True),
    )
    active_schedules = (await db.execute(active_sched_stmt)).scalar() or 0

    # Job counts by status
    running_stmt = select(func.count(BackgroundJob.id)).where(
        BackgroundJob.workspace_id == workspace_id,
        BackgroundJob.status == "RUNNING",
    )
    running_jobs = (await db.execute(running_stmt)).scalar() or 0

    queued_stmt = select(func.count(BackgroundJob.id)).where(
        BackgroundJob.workspace_id == workspace_id,
        BackgroundJob.status == "QUEUED",
    )
    queued_jobs = (await db.execute(queued_stmt)).scalar() or 0

    failed_stmt = select(func.count(BackgroundJob.id)).where(
        BackgroundJob.workspace_id == workspace_id,
        BackgroundJob.status == "FAILED",
    )
    failed_jobs = (await db.execute(failed_stmt)).scalar() or 0

    success_stmt = select(func.count(BackgroundJob.id)).where(
        BackgroundJob.workspace_id == workspace_id,
        BackgroundJob.status == "SUCCESS",
    )
    success_jobs = (await db.execute(success_stmt)).scalar() or 0

    active_wf_stmt = select(func.count(Workflow.id)).where(
        Workflow.workspace_id == workspace_id,
        Workflow.is_active.is_(True),
    )
    active_wf = (await db.execute(active_wf_stmt)).scalar() or 0

    # Recent jobs
    recent_jobs_stmt = (
        select(BackgroundJob)
        .where(BackgroundJob.workspace_id == workspace_id)
        .options(selectinload(BackgroundJob.executions))
        .order_by(desc(BackgroundJob.created_at))
        .limit(10)
    )
    recent_jobs = (await db.execute(recent_jobs_stmt)).scalars().all()

    # Recent workflows
    recent_wf_stmt = (
        select(WorkflowExecution)
        .where(WorkflowExecution.workspace_id == workspace_id)
        .options(selectinload(WorkflowExecution.step_executions))
        .order_by(desc(WorkflowExecution.created_at))
        .limit(5)
    )
    recent_workflows = (await db.execute(recent_wf_stmt)).scalars().all()

    return AutomationOverviewResponse(
        active_schedules_count=active_schedules,
        running_jobs_count=running_jobs,
        queued_jobs_count=queued_jobs,
        failed_jobs_count=failed_jobs,
        successful_jobs_count=success_jobs,
        active_workflows_count=active_wf,
        recent_jobs=[BackgroundJobResponse.model_validate(j) for j in recent_jobs],
        recent_workflows=[WorkflowExecutionResponse.model_validate(w) for w in recent_workflows],
    )


# ---------------------------------------------------------------------------
# Background Jobs
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=BackgroundJobResponse, status_code=status.HTTP_201_CREATED)
async def create_background_job(
    job_in: BackgroundJobCreate,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> BackgroundJobResponse:
    """Enqueue a new ad-hoc background job."""
    await _assert_workspace_access(db, workspace_id, current_user, "transformation:execute")

    job = await BackgroundJobService.enqueue_job(
        db=db,
        workspace_id=workspace_id,
        job_type=job_in.job_type,
        payload=job_in.payload,
        priority=job_in.priority,
        idempotency_key=job_in.idempotency_key,
        scheduled_at=job_in.scheduled_at,
        max_retries=job_in.max_retries,
        retry_delay_seconds=job_in.retry_delay_seconds,
        timeout_seconds=job_in.timeout_seconds,
        created_by=current_user.id,
    )
    return BackgroundJobResponse.model_validate(job)


@router.get("/jobs", response_model=BackgroundJobListResponse)
async def list_background_jobs(
    workspace_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(None, alias="status"),
    job_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> BackgroundJobListResponse:
    """List background jobs with status and job type filtering."""
    await _assert_workspace_access(db, workspace_id, current_user)

    stmt = select(BackgroundJob).where(BackgroundJob.workspace_id == workspace_id)
    if status_filter:
        stmt = stmt.where(BackgroundJob.status == status_filter.upper())
    if job_type:
        stmt = stmt.where(BackgroundJob.job_type == job_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        stmt.options(selectinload(BackgroundJob.executions))
        .order_by(desc(BackgroundJob.created_at))
        .limit(limit)
        .offset(offset)
    )
    jobs = (await db.execute(stmt)).scalars().all()

    return BackgroundJobListResponse(
        jobs=[BackgroundJobResponse.model_validate(j) for j in jobs],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=BackgroundJobResponse)
async def get_background_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> BackgroundJobResponse:
    """Get background job detail including execution attempts and progress."""
    stmt = (
        select(BackgroundJob)
        .where(BackgroundJob.id == job_id)
        .options(selectinload(BackgroundJob.executions))
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await _assert_workspace_access(db, job.workspace_id, current_user)
    return BackgroundJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=BackgroundJobResponse)
async def cancel_background_job(
    job_id: uuid.UUID,
    reason: str = Query("Cancelled by user request"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> BackgroundJobResponse:
    """Cancel a queued or running background job."""
    job = await db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await _assert_workspace_access(db, job.workspace_id, current_user, "transformation:execute")
    cancelled_job = await BackgroundJobService.cancel_job(
        db=db, job_id=job_id, user_id=current_user.id, reason=reason
    )
    return BackgroundJobResponse.model_validate(cancelled_job)


@router.post("/jobs/{job_id}/retry", response_model=BackgroundJobResponse)
async def retry_background_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> BackgroundJobResponse:
    """Manually re-enqueue a failed or cancelled background job."""
    job = await db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await _assert_workspace_access(db, job.workspace_id, current_user, "transformation:execute")
    retried_job = await BackgroundJobService.retry_job(
        db=db, job_id=job_id, user_id=current_user.id
    )
    return BackgroundJobResponse.model_validate(retried_job)


# ---------------------------------------------------------------------------
# Schedules Management
# ---------------------------------------------------------------------------


@router.get("/schedules", response_model=JobScheduleListResponse)
async def list_schedules(
    workspace_id: uuid.UUID = Query(...),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> JobScheduleListResponse:
    """List all recurring and one-time schedules for workspace."""
    await _assert_workspace_access(db, workspace_id, current_user)

    stmt = select(JobSchedule).where(JobSchedule.workspace_id == workspace_id)
    if is_active is not None:
        stmt = stmt.where(JobSchedule.is_active == is_active)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(desc(JobSchedule.created_at))
    schedules = (await db.execute(stmt)).scalars().all()

    return JobScheduleListResponse(
        schedules=[JobScheduleResponse.model_validate(s) for s in schedules],
        total=total,
    )


@router.post("/schedules", response_model=JobScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    sched_in: JobScheduleCreate,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> JobScheduleResponse:
    """Create a new recurring or one-time schedule."""
    await _assert_workspace_access(db, workspace_id, current_user, "governance:manage")

    # Calculate initial next_run_at
    next_run = AutomationScheduler.calculate_next_run(
        frequency=sched_in.frequency,
        timezone_str=sched_in.timezone,
        hour=sched_in.hour,
        minute=sched_in.minute,
        day_of_week=sched_in.day_of_week,
        day_of_month=sched_in.day_of_month,
        cron_expression=sched_in.cron_expression,
    )

    schedule = JobSchedule(
        workspace_id=workspace_id,
        name=sched_in.name,
        description=sched_in.description,
        job_type=sched_in.job_type,
        target_resource_id=sched_in.target_resource_id,
        target_resource_type=sched_in.target_resource_type,
        payload=sched_in.payload,
        frequency=sched_in.frequency,
        cron_expression=sched_in.cron_expression,
        timezone=sched_in.timezone,
        hour=sched_in.hour,
        minute=sched_in.minute,
        day_of_week=sched_in.day_of_week,
        day_of_month=sched_in.day_of_month,
        is_active=True,
        next_run_at=next_run,
        created_by=current_user.id,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    await GovernanceService.record_audit_log(
        db=db,
        workspace_id=workspace_id,
        actor_id=current_user.id,
        action="schedule:create",
        resource_type="job_schedule",
        resource_id=schedule.id,
        outcome="success",
        details={"name": schedule.name, "frequency": schedule.frequency, "next_run_at": next_run.isoformat() if next_run else None},
    )

    return JobScheduleResponse.model_validate(schedule)


@router.get("/schedules/{schedule_id}", response_model=JobScheduleResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> JobScheduleResponse:
    """Get schedule details."""
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await _assert_workspace_access(db, schedule.workspace_id, current_user)
    return JobScheduleResponse.model_validate(schedule)


@router.put("/schedules/{schedule_id}", response_model=JobScheduleResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    sched_in: JobScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> JobScheduleResponse:
    """Update schedule settings, recalculating next_run_at."""
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await _assert_workspace_access(db, schedule.workspace_id, current_user, "governance:manage")

    update_data = sched_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(schedule, field, val)

    # Recalculate next run if active
    if schedule.is_active:
        schedule.next_run_at = AutomationScheduler.calculate_next_run(
            frequency=schedule.frequency,
            timezone_str=schedule.timezone,
            hour=schedule.hour,
            minute=schedule.minute,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
            cron_expression=schedule.cron_expression,
        )

    await db.commit()
    await db.refresh(schedule)

    await GovernanceService.record_audit_log(
        db=db,
        workspace_id=schedule.workspace_id,
        actor_id=current_user.id,
        action="schedule:update",
        resource_type="job_schedule",
        resource_id=schedule.id,
        outcome="success",
        details={"updated_fields": list(update_data.keys())},
    )
    return JobScheduleResponse.model_validate(schedule)


@router.post("/schedules/{schedule_id}/pause", response_model=JobScheduleResponse)
async def pause_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> JobScheduleResponse:
    """Pause an active schedule."""
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await _assert_workspace_access(db, schedule.workspace_id, current_user, "governance:manage")
    schedule.is_active = False
    await db.commit()
    await db.refresh(schedule)
    return JobScheduleResponse.model_validate(schedule)


@router.post("/schedules/{schedule_id}/resume", response_model=JobScheduleResponse)
async def resume_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> JobScheduleResponse:
    """Resume a paused schedule."""
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await _assert_workspace_access(db, schedule.workspace_id, current_user, "governance:manage")
    schedule.is_active = True
    schedule.next_run_at = AutomationScheduler.calculate_next_run(
        frequency=schedule.frequency,
        timezone_str=schedule.timezone,
        hour=schedule.hour,
        minute=schedule.minute,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        cron_expression=schedule.cron_expression,
    )
    await db.commit()
    await db.refresh(schedule)
    return JobScheduleResponse.model_validate(schedule)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> None:
    """Delete a schedule."""
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await _assert_workspace_access(db, schedule.workspace_id, current_user, "governance:manage")
    await db.delete(schedule)
    await db.commit()


# ---------------------------------------------------------------------------
# Workflow Orchestration (DAGs)
# ---------------------------------------------------------------------------


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> WorkflowListResponse:
    """List workflows for workspace."""
    await _assert_workspace_access(db, workspace_id, current_user)

    stmt = (
        select(Workflow)
        .where(Workflow.workspace_id == workspace_id)
        .options(selectinload(Workflow.steps))
        .order_by(desc(Workflow.created_at))
    )
    wfs = (await db.execute(stmt)).scalars().all()

    return WorkflowListResponse(
        workflows=[WorkflowResponse.model_validate(w) for w in wfs],
        total=len(wfs),
    )


@router.post("/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    wf_in: WorkflowCreate,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> WorkflowResponse:
    """Create a new DAG workflow with steps."""
    await _assert_workspace_access(db, workspace_id, current_user, "transformation:create")

    # Validate DAG for cycles
    val = WorkflowDAGService.validate_and_sort_steps(wf_in.steps)
    if not val.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow validation failed: {'; '.join(val.errors)}",
        )

    wf = Workflow(
        workspace_id=workspace_id,
        name=wf_in.name,
        description=wf_in.description,
        failure_policy=wf_in.failure_policy,
        created_by=current_user.id,
    )
    db.add(wf)
    await db.flush()

    for idx, s in enumerate(wf_in.steps):
        step = WorkflowStep(
            workflow_id=wf.id,
            step_name=s.step_name,
            step_order=s.step_order or idx,
            step_type=s.step_type,
            target_resource_id=s.target_resource_id,
            configuration=s.configuration,
            depends_on_step_ids=s.depends_on_step_ids,
            timeout_seconds=s.timeout_seconds,
            max_retries=s.max_retries,
        )
        db.add(step)

    await db.commit()
    await db.refresh(wf)

    # Reload with steps
    stmt = select(Workflow).where(Workflow.id == wf.id).options(selectinload(Workflow.steps))
    reloaded = (await db.execute(stmt)).scalar_one()

    return WorkflowResponse.model_validate(reloaded)


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> WorkflowResponse:
    """Get workflow with all steps."""
    stmt = (
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.steps))
    )
    wf = (await db.execute(stmt)).scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await _assert_workspace_access(db, wf.workspace_id, current_user)
    return WorkflowResponse.model_validate(wf)


@router.post("/workflows/{workflow_id}/validate", response_model=WorkflowValidationResponse)
async def validate_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> WorkflowValidationResponse:
    """Verify that workflow dependencies form a valid DAG without circular cycles."""
    stmt = (
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.steps))
    )
    wf = (await db.execute(stmt)).scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await _assert_workspace_access(db, wf.workspace_id, current_user)
    return WorkflowDAGService.validate_and_sort_steps(wf.steps)


@router.post("/workflows/{workflow_id}/trigger", response_model=BackgroundJobResponse)
async def trigger_workflow_execution(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> BackgroundJobResponse:
    """Trigger ad-hoc execution of a workflow as a background job."""
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await _assert_workspace_access(db, wf.workspace_id, current_user, "transformation:execute")

    job = await BackgroundJobService.enqueue_job(
        db=db,
        workspace_id=wf.workspace_id,
        job_type="workflow",
        payload={"workflow_id": str(wf.id), "workflow_name": wf.name},
        priority=8,
        created_by=current_user.id,
    )
    return BackgroundJobResponse.model_validate(job)


@router.get("/workflows/{workflow_id}/executions", response_model=WorkflowExecutionListResponse)
async def list_workflow_executions(
    workflow_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> WorkflowExecutionListResponse:
    """List historical executions of a workflow."""
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await _assert_workspace_access(db, wf.workspace_id, current_user)

    stmt = (
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .options(selectinload(WorkflowExecution.step_executions))
        .order_by(desc(WorkflowExecution.created_at))
        .limit(limit)
    )
    execs = (await db.execute(stmt)).scalars().all()

    return WorkflowExecutionListResponse(
        executions=[WorkflowExecutionResponse.model_validate(e) for e in execs],
        total=len(execs),
    )


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> WorkflowExecutionResponse:
    """Get detailed step-by-step status and metrics for a workflow execution."""
    stmt = (
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id)
        .options(
            selectinload(WorkflowExecution.step_executions).selectinload(
                WorkflowStepExecution.step
            )
        )
    )
    wf_exec = (await db.execute(stmt)).scalar_one_or_none()
    if not wf_exec:
        raise HTTPException(status_code=404, detail="Execution not found")

    await _assert_workspace_access(db, wf_exec.workspace_id, current_user)

    resp = WorkflowExecutionResponse.model_validate(wf_exec)
    # Populate step_name and step_type on step executions
    for s_exec, orm_s_exec in zip(resp.step_executions, wf_exec.step_executions, strict=False):
        if orm_s_exec.step:
            s_exec.step_name = orm_s_exec.step.step_name
            s_exec.step_type = orm_s_exec.step.step_type

    return resp
