import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import require_active_user, require_workspace_role
from app.models.conversational_analytics import (
    NLAMessage,
    NLASession,
    SavedAnalysis,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.services.nla.schemas import (
    NLAClarifyRequest,
    NLAFollowUpRequest,
    NLAMessageResponse,
    NLAQueryRequest,
    NLASessionResponse,
    SavedAnalysisCreateRequest,
    SavedAnalysisResponse,
)
from app.services.nla.session_service import NLASessionService

router = APIRouter(prefix="/analytics", tags=["Natural Language Analytics & Conversational BI"])


@router.post(
    "/query",
    response_model=NLAMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def execute_natural_language_query(
    req: NLAQueryRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NLAMessageResponse:
    """
    Submits a natural-language business question, formulates a semantic analytical plan,
    executes deterministically via DuckDB, and returns evidence-backed findings and visualizations.
    """
    workspace, _ = ws_context
    msg = await NLASessionService.execute_nl_query(
        req=req,
        workspace_id=workspace.id,
        user_id=current_user.id,
        db=db,
    )
    return NLAMessageResponse.model_validate(msg)


@router.post(
    "/clarify",
    response_model=NLAMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_clarification(
    req: NLAClarifyRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NLAMessageResponse:
    """
    Resumes an analytical session by applying the user's targeted clarification option.
    """
    workspace, _ = ws_context
    query_req = NLAQueryRequest(
        question=req.chosen_option,
        session_id=req.session_id,
        dataset_id=req.dataset_id,
        version_id=req.version_id,
    )
    msg = await NLASessionService.execute_nl_query(
        req=query_req,
        workspace_id=workspace.id,
        user_id=current_user.id,
        db=db,
    )
    return NLAMessageResponse.model_validate(msg)


@router.post(
    "/follow-up",
    response_model=NLAMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_follow_up(
    req: NLAFollowUpRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NLAMessageResponse:
    """
    Executes a contextual follow-up question within an active conversation session.
    """
    workspace, _ = ws_context
    # Fetch session to determine active dataset
    s_stmt = select(NLASession).where(
        NLASession.id == req.session_id,
        NLASession.workspace_id == workspace.id,
    )
    session = (await db.execute(s_stmt)).scalar_one_or_none()
    if not session or not session.dataset_id:
        raise DataLensException("Active conversational session not found.", code="NOT_FOUND")

    dataset_id = req.dataset_id or session.dataset_id
    version_id = req.version_id or session.dataset_version_id

    query_req = NLAQueryRequest(
        question=req.question,
        session_id=req.session_id,
        dataset_id=dataset_id,
        version_id=version_id,
    )
    msg = await NLASessionService.execute_nl_query(
        req=query_req,
        workspace_id=workspace.id,
        user_id=current_user.id,
        db=db,
    )
    return NLAMessageResponse.model_validate(msg)


@router.get(
    "/sessions",
    response_model=list[NLASessionResponse],
)
async def list_conversational_sessions(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NLASessionResponse]:
    """
    Lists recent conversational analytics sessions in the workspace for the active user.
    """
    workspace, _ = ws_context
    stmt = (
        select(NLASession)
        .options(selectinload(NLASession.messages))
        .where(
            NLASession.workspace_id == workspace.id,
            NLASession.user_id == current_user.id,
        )
        .order_by(desc(NLASession.updated_at))
        .limit(50)
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()
    return [NLASessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/sessions/{session_id}",
    response_model=NLASessionResponse,
)
async def get_session_details(
    session_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NLASessionResponse:
    """
    Retrieves conversational session details with full message turn history.
    """
    workspace, _ = ws_context
    stmt = (
        select(NLASession)
        .options(selectinload(NLASession.messages))
        .where(
            NLASession.id == session_id,
            NLASession.workspace_id == workspace.id,
        )
    )
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise DataLensException("Session not found.", code="NOT_FOUND")
    return NLASessionResponse.model_validate(session)


@router.get(
    "/history",
    response_model=list[NLAMessageResponse],
)
async def get_query_history(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NLAMessageResponse]:
    """
    Retrieves global query execution history within the workspace.
    """
    workspace, _ = ws_context
    stmt = (
        select(NLAMessage)
        .join(NLASession, NLAMessage.session_id == NLASession.id)
        .where(
            NLASession.workspace_id == workspace.id,
            NLAMessage.sender == "assistant",
        )
        .order_by(desc(NLAMessage.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()
    return [NLAMessageResponse.model_validate(m) for m in messages]


@router.post(
    "/saved",
    response_model=SavedAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_analysis(
    req: SavedAnalysisCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SavedAnalysisResponse:
    """
    Saves an analytical finding for rapid retrieval and dashboard pinning.
    """
    workspace, _ = ws_context
    saved = await NLASessionService.create_saved_analysis(
        req=req,
        workspace_id=workspace.id,
        user_id=current_user.id,
        db=db,
    )
    return SavedAnalysisResponse.model_validate(saved)


@router.get(
    "/saved",
    response_model=list[SavedAnalysisResponse],
)
async def list_saved_analyses(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SavedAnalysisResponse]:
    """
    Lists saved analyses in the active workspace.
    """
    workspace, _ = ws_context
    stmt = (
        select(SavedAnalysis)
        .where(SavedAnalysis.workspace_id == workspace.id)
        .order_by(desc(SavedAnalysis.created_at))
    )
    res = await db.execute(stmt)
    analyses = res.scalars().all()
    return [SavedAnalysisResponse.model_validate(a) for a in analyses]


@router.delete(
    "/saved/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_saved_analysis(
    saved_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Deletes a saved analysis.
    """
    workspace, _ = ws_context
    stmt = select(SavedAnalysis).where(
        SavedAnalysis.id == saved_id,
        SavedAnalysis.workspace_id == workspace.id,
    )
    saved = (await db.execute(stmt)).scalar_one_or_none()
    if not saved:
        raise DataLensException("Saved analysis not found.", code="NOT_FOUND")
    await db.delete(saved)
    await db.commit()

