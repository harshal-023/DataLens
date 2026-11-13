import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import require_active_user, require_workspace_role
from app.models.business_analyst import (
    BusinessInsight,
    InsightComment,
    InsightGenerationRun,
    InsightGenerationSchedule,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.services.business_analyst.insight_engine import BusinessInsightEngine
from app.services.business_analyst.schemas import (
    BusinessInsightResponse,
    ExecutiveOverviewResponse,
    InsightAssignRequest,
    InsightCommentCreateRequest,
    InsightCommentResponse,
    InsightGenerateRequest,
    InsightStatusUpdateRequest,
    ScheduleCreateRequest,
    ScheduleResponse,
)

router = APIRouter(prefix="/business-analyst", tags=["AI Business Analyst"])


@router.get(
    "/overview",
    response_model=ExecutiveOverviewResponse,
    status_code=status.HTTP_200_OK,
)
async def get_business_overview(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None, description="Optional dataset filter"),
) -> ExecutiveOverviewResponse:
    workspace, _ = ws_context
    overview_data = await BusinessInsightEngine.get_executive_overview(
        workspace_id=workspace.id,
        db=db,
        dataset_id=dataset_id,
    )
    return ExecutiveOverviewResponse(**overview_data)


@router.get(
    "/insights",
    response_model=list[BusinessInsightResponse],
    status_code=status.HTTP_200_OK,
)
async def list_insights(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    insight_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> list[BusinessInsightResponse]:
    workspace, _ = ws_context
    stmt = (
        select(BusinessInsight)
        .options(
            selectinload(BusinessInsight.evidence_items),
            selectinload(BusinessInsight.comments).selectinload(InsightComment.author),
        )
        .where(BusinessInsight.workspace_id == workspace.id)
        .order_by(desc(BusinessInsight.score), desc(BusinessInsight.created_at))
        .limit(limit)
    )
    if dataset_id:
        stmt = stmt.where(BusinessInsight.dataset_id == dataset_id)
    if category:
        stmt = stmt.where(BusinessInsight.category == category)
    if severity:
        stmt = stmt.where(BusinessInsight.severity == severity)
    if insight_status:
        stmt = stmt.where(BusinessInsight.status == insight_status)

    res = await db.execute(stmt)
    insights = res.scalars().all()

    out: list[BusinessInsightResponse] = []
    for ins in insights:
        comments_resp = [
            InsightCommentResponse(
                id=c.id,
                insight_id=c.insight_id,
                user_id=c.user_id,
                author_name=c.author.full_name if c.author else "Team Member",
                content=c.content,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in ins.comments
        ]
        ins_dict = {
            "id": ins.id,
            "workspace_id": ins.workspace_id,
            "dataset_id": ins.dataset_id,
            "dataset_version_id": ins.dataset_version_id,
            "title": ins.title,
            "category": ins.category,
            "severity": ins.severity,
            "status": ins.status,
            "summary": ins.summary,
            "detailed_explanation": ins.detailed_explanation,
            "affected_metric": ins.affected_metric,
            "affected_dimension": ins.affected_dimension,
            "affected_segment": ins.affected_segment,
            "score": ins.score,
            "priority_reason": ins.priority_reason,
            "recommended_action": ins.recommended_action,
            "suggested_investigation": ins.suggested_investigation,
            "assigned_to_user_id": ins.assigned_to_user_id,
            "acknowledged_at": ins.acknowledged_at,
            "acknowledged_by_user_id": ins.acknowledged_by_user_id,
            "resolved_at": ins.resolved_at,
            "resolved_by_user_id": ins.resolved_by_user_id,
            "ai_provider": ins.ai_provider,
            "fingerprint": ins.fingerprint,
            "created_at": ins.created_at,
            "updated_at": ins.updated_at,
            "evidence_items": ins.evidence_items,
            "comments": comments_resp,
        }
        out.append(BusinessInsightResponse(**ins_dict))
    return out


@router.get(
    "/insights/{insight_id}",
    response_model=BusinessInsightResponse,
    status_code=status.HTTP_200_OK,
)
async def get_insight(
    insight_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessInsightResponse:
    workspace, _ = ws_context
    stmt = (
        select(BusinessInsight)
        .options(
            selectinload(BusinessInsight.evidence_items),
            selectinload(BusinessInsight.comments).selectinload(InsightComment.author),
        )
        .where(
            BusinessInsight.id == insight_id,
            BusinessInsight.workspace_id == workspace.id,
        )
    )
    res = await db.execute(stmt)
    ins = res.scalar_one_or_none()
    if not ins:
        raise DataLensException("Business insight not found.", code="NOT_FOUND")

    comments_resp = [
        InsightCommentResponse(
            id=c.id,
            insight_id=c.insight_id,
            user_id=c.user_id,
            author_name=c.author.full_name if c.author else "Team Member",
            content=c.content,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in ins.comments
    ]
    return BusinessInsightResponse(
        id=ins.id,
        workspace_id=ins.workspace_id,
        dataset_id=ins.dataset_id,
        dataset_version_id=ins.dataset_version_id,
        title=ins.title,
        category=ins.category,  # type: ignore
        severity=ins.severity,  # type: ignore
        status=ins.status,  # type: ignore
        summary=ins.summary,
        detailed_explanation=ins.detailed_explanation,
        affected_metric=ins.affected_metric,
        affected_dimension=ins.affected_dimension,
        affected_segment=ins.affected_segment,
        score=ins.score,
        priority_reason=ins.priority_reason,
        recommended_action=ins.recommended_action,
        suggested_investigation=ins.suggested_investigation,
        assigned_to_user_id=ins.assigned_to_user_id,
        acknowledged_at=ins.acknowledged_at,
        acknowledged_by_user_id=ins.acknowledged_by_user_id,
        resolved_at=ins.resolved_at,
        resolved_by_user_id=ins.resolved_by_user_id,
        ai_provider=ins.ai_provider,
        fingerprint=ins.fingerprint,
        created_at=ins.created_at,
        updated_at=ins.updated_at,
        evidence_items=ins.evidence_items,
        comments=comments_resp,
    )


@router.post(
    "/insights/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_insights(
    req: InsightGenerateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    workspace, _ = ws_context
    run = await BusinessInsightEngine.run_autonomous_analysis(
        workspace_id=workspace.id,
        dataset_id=req.dataset_id,
        db=db,
        version_id=req.version_id,
        trigger_type="manual",
        ai_provider=req.ai_provider,
    )
    return {
        "status": "success",
        "run_id": run.id,
        "insights_generated_count": run.insights_generated_count,
        "execution_duration_ms": run.execution_duration_ms,
    }


@router.patch(
    "/insights/{insight_id}/status",
    response_model=BusinessInsightResponse,
    status_code=status.HTTP_200_OK,
)
async def update_insight_status(
    insight_id: uuid.UUID,
    req: InsightStatusUpdateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessInsightResponse:
    workspace, _ = ws_context
    ins = await BusinessInsightEngine.update_status(
        insight_id=insight_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        new_status=req.status,
        db=db,
        notes=req.notes,
    )
    # Refresh with evidence
    stmt = (
        select(BusinessInsight)
        .options(selectinload(BusinessInsight.evidence_items), selectinload(BusinessInsight.comments))
        .where(BusinessInsight.id == ins.id)
    )
    res = await db.execute(stmt)
    full_ins = res.scalar_one()
    return BusinessInsightResponse.model_validate(full_ins)


@router.post(
    "/insights/{insight_id}/assign",
    response_model=BusinessInsightResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_insight(
    insight_id: uuid.UUID,
    req: InsightAssignRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessInsightResponse:
    workspace, _ = ws_context
    ins = await BusinessInsightEngine.assign_insight(
        insight_id=insight_id,
        workspace_id=workspace.id,
        assigned_by_user_id=current_user.id,
        assigned_to_user_id=req.assigned_to_user_id,
        db=db,
        note=req.note,
    )
    stmt = (
        select(BusinessInsight)
        .options(selectinload(BusinessInsight.evidence_items), selectinload(BusinessInsight.comments))
        .where(BusinessInsight.id == ins.id)
    )
    res = await db.execute(stmt)
    full_ins = res.scalar_one()
    return BusinessInsightResponse.model_validate(full_ins)


@router.post(
    "/insights/{insight_id}/comments",
    response_model=InsightCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_insight_comment(
    insight_id: uuid.UUID,
    req: InsightCommentCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InsightCommentResponse:
    workspace, _ = ws_context
    comment = await BusinessInsightEngine.add_comment(
        insight_id=insight_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        content=req.content,
        db=db,
    )
    return InsightCommentResponse(
        id=comment.id,
        insight_id=comment.insight_id,
        user_id=comment.user_id,
        author_name=current_user.full_name or "Team Member",
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# Specialized Category Filters
@router.get("/trends", response_model=list[BusinessInsightResponse])
async def list_trends(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
) -> list[BusinessInsightResponse]:
    return await list_insights(
        current_user=current_user,
        ws_context=ws_context,
        db=db,
        dataset_id=dataset_id,
        category="trend",
    )


@router.get("/anomalies", response_model=list[BusinessInsightResponse])
async def list_anomalies(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
) -> list[BusinessInsightResponse]:
    return await list_insights(
        current_user=current_user,
        ws_context=ws_context,
        db=db,
        dataset_id=dataset_id,
        category="anomaly",
    )


@router.get("/risks", response_model=list[BusinessInsightResponse])
async def list_risks(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
) -> list[BusinessInsightResponse]:
    return await list_insights(
        current_user=current_user,
        ws_context=ws_context,
        db=db,
        dataset_id=dataset_id,
        category="risk",
    )


@router.get("/opportunities", response_model=list[BusinessInsightResponse])
async def list_opportunities(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
) -> list[BusinessInsightResponse]:
    return await list_insights(
        current_user=current_user,
        ws_context=ws_context,
        db=db,
        dataset_id=dataset_id,
        category="opportunity",
    )


@router.get("/history", status_code=status.HTTP_200_OK)
async def list_run_history(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    workspace, _ = ws_context
    stmt = (
        select(InsightGenerationRun)
        .where(InsightGenerationRun.workspace_id == workspace.id)
        .order_by(desc(InsightGenerationRun.created_at))
        .limit(limit)
    )
    if dataset_id:
        stmt = stmt.where(InsightGenerationRun.dataset_id == dataset_id)

    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [
        {
            "id": r.id,
            "dataset_id": r.dataset_id,
            "dataset_version_id": r.dataset_version_id,
            "trigger_type": r.trigger_type,
            "status": r.status,
            "insights_generated_count": r.insights_generated_count,
            "execution_duration_ms": r.execution_duration_ms,
            "error_message": r.error_message,
            "created_at": r.created_at,
            "completed_at": r.completed_at,
        }
        for r in runs
    ]


# Schedules CRUD
@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    req: ScheduleCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduleResponse:
    workspace, _ = ws_context
    sched = InsightGenerationSchedule(
        workspace_id=workspace.id,
        dataset_id=req.dataset_id,
        name=req.name,
        frequency=req.frequency,
        cron_expression=req.cron_expression,
        timezone=req.timezone,
        is_active=True,
        config=req.config,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return ScheduleResponse.model_validate(sched)


@router.get("/schedules", response_model=list[ScheduleResponse], status_code=status.HTTP_200_OK)
async def list_schedules(
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ScheduleResponse]:
    workspace, _ = ws_context
    stmt = (
        select(InsightGenerationSchedule)
        .where(InsightGenerationSchedule.workspace_id == workspace.id)
        .order_by(desc(InsightGenerationSchedule.created_at))
    )
    res = await db.execute(stmt)
    scheds = res.scalars().all()
    return [ScheduleResponse.model_validate(s) for s in scheds]


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_200_OK)
async def delete_schedule(
    schedule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool]:
    workspace, _ = ws_context
    stmt = select(InsightGenerationSchedule).where(
        InsightGenerationSchedule.id == schedule_id,
        InsightGenerationSchedule.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    sched = res.scalar_one_or_none()
    if not sched:
        raise DataLensException("Schedule not found.", code="NOT_FOUND")
    await db.delete(sched)
    await db.commit()
    return {"success": True}

