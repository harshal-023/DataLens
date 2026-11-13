import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.prompt_lab import PromptTemplate
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.prompt_lab import (
    PromptCreateRequest,
    PromptDetailResponse,
    PromptExecuteRequest,
    PromptExecuteResponse,
    PromptListItemResponse,
    PromptUpdateRequest,
    PromptVersionComparisonResponse,
    PromptVersionCreateRequest,
    PromptVersionResponse,
)
from app.services.prompt_lab.execution_service import PromptExecutionService
from app.services.prompt_lab.template_engine import PromptTemplateEngine
from app.services.prompt_lab.version_service import PromptVersionService

router = APIRouter(prefix="/prompts", tags=["Prompt Lab - Library & Playground"])


@router.post("", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptDetailResponse:
    """
    Creates a new prompt template and automatically publishes Version 1.
    """
    workspace, _ = ws_context

    # 1. Create prompt template
    prompt = PromptTemplate(
        workspace_id=workspace.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        category=payload.category,
        tags=payload.tags,
        created_by=current_user.id,
    )
    db.add(prompt)
    await db.flush()

    # 2. Extract detected variables if none provided
    vars_to_store = [v.model_dump() for v in payload.variables]
    if not vars_to_store:
        detected = PromptTemplateEngine.extract_variables(payload.user_prompt_template) + PromptTemplateEngine.extract_variables(payload.system_prompt)
        vars_to_store = [{"name": var, "description": f"Variable {var}", "required": True, "default": None} for var in detected]

    # 3. Create initial version 1
    v1 = await PromptVersionService.create_version(
        db=db,
        prompt=prompt,
        system_prompt=payload.system_prompt,
        user_prompt_template=payload.user_prompt_template,
        variables=vars_to_store,
        model_config_snapshot=payload.model_config_snapshot.model_dump(),
        change_description=payload.change_description or "Initial version",
        created_by_user_id=current_user.id,
    )

    return PromptDetailResponse(
        id=prompt.id,
        workspace_id=prompt.workspace_id,
        name=prompt.name,
        description=prompt.description,
        category=prompt.category,
        tags=prompt.tags,
        created_by=prompt.created_by,
        is_archived=prompt.is_archived,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        current_version=PromptVersionResponse(
            id=v1.id,
            prompt_id=v1.prompt_id,
            version_number=v1.version_number,
            system_prompt=v1.system_prompt,
            user_prompt_template=v1.user_prompt_template,
            variables=v1.variables,
            model_config_snapshot=v1.model_config_snapshot,
            change_description=v1.change_description,
            created_by=v1.created_by,
            created_at=v1.created_at,
        ),
        versions_count=1,
    )


@router.get("", response_model=list[PromptListItemResponse])
async def list_prompts(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None, description="Search by name or description"),
    category: str | None = Query(None, description="Filter by category"),
    include_archived: bool = Query(False, description="Include archived prompts"),
) -> list[PromptListItemResponse]:
    """
    List prompt templates for the current workspace with search and filtering.
    """
    workspace, _ = ws_context

    stmt = (
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.workspace_id == workspace.id)
    )

    if not include_archived:
        stmt = stmt.where(PromptTemplate.is_archived.is_(False))

    if category:
        stmt = stmt.where(PromptTemplate.category == category)

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(PromptTemplate.name.ilike(term) | PromptTemplate.description.ilike(term))

    stmt = stmt.order_by(desc(PromptTemplate.updated_at))
    result = await db.execute(stmt)
    prompts = result.scalars().all()

    items = []
    for p in prompts:
        v_count = len(p.versions)
        latest_v = max([v.version_number for v in p.versions], default=1)
        items.append(
            PromptListItemResponse(
                id=p.id,
                workspace_id=p.workspace_id,
                name=p.name,
                description=p.description,
                category=p.category,
                tags=p.tags,
                is_archived=p.is_archived,
                created_at=p.created_at,
                updated_at=p.updated_at,
                versions_count=v_count,
                latest_version_number=latest_v,
            )
        )
    return items


@router.get("/{prompt_id}", response_model=PromptDetailResponse)
async def get_prompt_detail(
    prompt_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptDetailResponse:
    """
    Retrieves full details of a prompt template including its latest version.
    """
    workspace, _ = ws_context
    stmt = (
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    )
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    latest_version = prompt.versions[0] if prompt.versions else None
    v_resp = None
    if latest_version:
        v_resp = PromptVersionResponse(
            id=latest_version.id,
            prompt_id=latest_version.prompt_id,
            version_number=latest_version.version_number,
            system_prompt=latest_version.system_prompt,
            user_prompt_template=latest_version.user_prompt_template,
            variables=latest_version.variables,
            model_config_snapshot=latest_version.model_config_snapshot,
            change_description=latest_version.change_description,
            created_by=latest_version.created_by,
            created_at=latest_version.created_at,
        )

    return PromptDetailResponse(
        id=prompt.id,
        workspace_id=prompt.workspace_id,
        name=prompt.name,
        description=prompt.description,
        category=prompt.category,
        tags=prompt.tags,
        created_by=prompt.created_by,
        is_archived=prompt.is_archived,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        current_version=v_resp,
        versions_count=len(prompt.versions),
    )


@router.patch("/{prompt_id}", response_model=PromptDetailResponse)
async def update_prompt_metadata(
    prompt_id: uuid.UUID,
    payload: PromptUpdateRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptDetailResponse:
    """
    Updates mutable prompt metadata (name, description, category, tags).
    Does NOT mutate prompt versions.
    """
    workspace, _ = ws_context
    stmt = (
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    )
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    if payload.name is not None:
        prompt.name = payload.name.strip()
    if payload.description is not None:
        prompt.description = payload.description.strip()
    if payload.category is not None:
        prompt.category = payload.category
    if payload.tags is not None:
        prompt.tags = payload.tags

    await db.commit()
    await db.refresh(prompt)

    latest_version = prompt.versions[0] if prompt.versions else None
    v_resp = None
    if latest_version:
        v_resp = PromptVersionResponse(
            id=latest_version.id,
            prompt_id=latest_version.prompt_id,
            version_number=latest_version.version_number,
            system_prompt=latest_version.system_prompt,
            user_prompt_template=latest_version.user_prompt_template,
            variables=latest_version.variables,
            model_config_snapshot=latest_version.model_config_snapshot,
            change_description=latest_version.change_description,
            created_by=latest_version.created_by,
            created_at=latest_version.created_at,
        )

    return PromptDetailResponse(
        id=prompt.id,
        workspace_id=prompt.workspace_id,
        name=prompt.name,
        description=prompt.description,
        category=prompt.category,
        tags=prompt.tags,
        created_by=prompt.created_by,
        is_archived=prompt.is_archived,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        current_version=v_resp,
        versions_count=len(prompt.versions),
    )


@router.post("/{prompt_id}/duplicate", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_prompt(
    prompt_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptDetailResponse:
    """
    Duplicates an existing prompt template into a new template with Version 1.
    """
    workspace, _ = ws_context
    stmt = (
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    )
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    latest_v = prompt.versions[0] if prompt.versions else None
    if not latest_v:
        raise DataLensException("Prompt template has no published versions to duplicate.", code="INVALID_STATE")

    dup_prompt = PromptTemplate(
        workspace_id=workspace.id,
        name=f"{prompt.name} (Copy)",
        description=prompt.description,
        category=prompt.category,
        tags=list(prompt.tags),
        created_by=current_user.id,
    )
    db.add(dup_prompt)
    await db.flush()

    v1 = await PromptVersionService.create_version(
        db=db,
        prompt=dup_prompt,
        system_prompt=latest_v.system_prompt,
        user_prompt_template=latest_v.user_prompt_template,
        variables=latest_v.variables,
        model_config_snapshot=latest_v.model_config_snapshot,
        change_description=f"Duplicated from {prompt.name} (v{latest_v.version_number})",
        created_by_user_id=current_user.id,
    )

    return PromptDetailResponse(
        id=dup_prompt.id,
        workspace_id=dup_prompt.workspace_id,
        name=dup_prompt.name,
        description=dup_prompt.description,
        category=dup_prompt.category,
        tags=dup_prompt.tags,
        created_by=dup_prompt.created_by,
        is_archived=dup_prompt.is_archived,
        created_at=dup_prompt.created_at,
        updated_at=dup_prompt.updated_at,
        current_version=PromptVersionResponse(
            id=v1.id,
            prompt_id=v1.prompt_id,
            version_number=v1.version_number,
            system_prompt=v1.system_prompt,
            user_prompt_template=v1.user_prompt_template,
            variables=v1.variables,
            model_config_snapshot=v1.model_config_snapshot,
            change_description=v1.change_description,
            created_by=v1.created_by,
            created_at=v1.created_at,
        ),
        versions_count=1,
    )


@router.delete("/{prompt_id}", status_code=status.HTTP_200_OK)
async def archive_prompt(
    prompt_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Soft-archives a prompt template.
    """
    workspace, _ = ws_context
    stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    prompt.is_archived = True
    await db.commit()
    return {"message": f"Prompt '{prompt.name}' archived successfully.", "id": str(prompt_id)}


# =========================================================================
# PROMPT VERSIONS
# =========================================================================

@router.post("/{prompt_id}/versions", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt_version(
    prompt_id: uuid.UUID,
    payload: PromptVersionCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptVersionResponse:
    """
    Creates a new immutable revision for a prompt template.
    Never overwrites existing versions.
    """
    workspace, _ = ws_context
    stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    vars_to_store = [v.model_dump() for v in payload.variables]
    if not vars_to_store:
        detected = PromptTemplateEngine.extract_variables(payload.user_prompt_template) + PromptTemplateEngine.extract_variables(payload.system_prompt)
        vars_to_store = [{"name": var, "description": f"Variable {var}", "required": True, "default": None} for var in detected]

    v = await PromptVersionService.create_version(
        db=db,
        prompt=prompt,
        system_prompt=payload.system_prompt,
        user_prompt_template=payload.user_prompt_template,
        variables=vars_to_store,
        model_config_snapshot=payload.model_config_snapshot.model_dump(),
        change_description=payload.change_description,
        created_by_user_id=current_user.id,
    )

    return PromptVersionResponse(
        id=v.id,
        prompt_id=v.prompt_id,
        version_number=v.version_number,
        system_prompt=v.system_prompt,
        user_prompt_template=v.user_prompt_template,
        variables=v.variables,
        model_config_snapshot=v.model_config_snapshot,
        change_description=v.change_description,
        created_by=v.created_by,
        created_at=v.created_at,
    )


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionResponse])
async def list_prompt_versions(
    prompt_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PromptVersionResponse]:
    """
    Retrieves the complete immutable version history for a prompt template.
    """
    workspace, _ = ws_context
    stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    versions = await PromptVersionService.get_versions_for_prompt(db, prompt_id)
    return [
        PromptVersionResponse(
            id=v.id,
            prompt_id=v.prompt_id,
            version_number=v.version_number,
            system_prompt=v.system_prompt,
            user_prompt_template=v.user_prompt_template,
            variables=v.variables,
            model_config_snapshot=v.model_config_snapshot,
            change_description=v.change_description,
            created_by=v.created_by,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.get("/{prompt_id}/versions/{version_id}", response_model=PromptVersionResponse)
async def get_prompt_version_by_id(
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptVersionResponse:
    workspace, _ = ws_context
    stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    v = await PromptVersionService.get_version_by_id(db, version_id)
    if not v or v.prompt_id != prompt.id:
        raise DataLensException("Prompt version not found.", code="NOT_FOUND")

    return PromptVersionResponse(
        id=v.id,
        prompt_id=v.prompt_id,
        version_number=v.version_number,
        system_prompt=v.system_prompt,
        user_prompt_template=v.user_prompt_template,
        variables=v.variables,
        model_config_snapshot=v.model_config_snapshot,
        change_description=v.change_description,
        created_by=v.created_by,
        created_at=v.created_at,
    )


@router.post("/{prompt_id}/versions/{version_id}/restore", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED)
async def restore_prompt_version(
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptVersionResponse:
    """
    Restores an older version by creating a new version with the content of the selected version.
    Never overwrites or deletes historical versions.
    """
    workspace, _ = ws_context
    stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    target_v = await PromptVersionService.get_version_by_id(db, version_id)
    if not target_v or target_v.prompt_id != prompt.id:
        raise DataLensException("Prompt version to restore was not found.", code="NOT_FOUND")

    new_v = await PromptVersionService.restore_version(db, prompt, target_v, current_user.id)
    return PromptVersionResponse(
        id=new_v.id,
        prompt_id=new_v.prompt_id,
        version_number=new_v.version_number,
        system_prompt=new_v.system_prompt,
        user_prompt_template=new_v.user_prompt_template,
        variables=new_v.variables,
        model_config_snapshot=new_v.model_config_snapshot,
        change_description=new_v.change_description,
        created_by=new_v.created_by,
        created_at=new_v.created_at,
    )


@router.get("/{prompt_id}/compare", response_model=PromptVersionComparisonResponse)
async def compare_prompt_versions(
    prompt_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_a: Annotated[uuid.UUID, Query(..., description="First version ID to compare")],
    version_b: Annotated[uuid.UUID, Query(..., description="Second version ID to compare")],
) -> PromptVersionComparisonResponse:
    """
    Side-by-side structural comparison of two prompt versions.
    """
    workspace, _ = ws_context
    stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.workspace_id == workspace.id)
    prompt = (await db.execute(stmt)).scalar_one_or_none()
    if not prompt:
        raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    return await PromptVersionService.compare_versions(db, prompt_id, version_a, version_b)


# =========================================================================
# PLAYGROUND EXECUTION
# =========================================================================

@router.post("/execute", response_model=PromptExecuteResponse)
async def execute_playground_prompt(
    payload: PromptExecuteRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptExecuteResponse:
    """
    Executes a prompt template with provided variables in the interactive playground.
    Reports latency, token usage, cost estimate, and simulation status.
    """
    # If prompt_version_id provided, verify workspace ownership
    version_label = None
    if payload.prompt_version_id:
        v = await PromptVersionService.get_version_by_id(db, payload.prompt_version_id)
        if v:
            version_label = f"v{v.version_number}"

    result = await PromptExecutionService.execute_prompt(
        system_prompt=payload.system_prompt,
        user_prompt_template=payload.user_prompt_template,
        variables=payload.variables,
        provider=payload.provider,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    return PromptExecuteResponse(
        rendered_system_prompt=result["rendered_system_prompt"],
        rendered_user_prompt=result["rendered_user_prompt"],
        response_text=result["response_text"],
        provider=result["provider"],
        model=result["model"],
        prompt_version=version_label,
        execution_timestamp=result["execution_timestamp"],
        latency_ms=result["latency_ms"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        estimated_cost_usd=result["estimated_cost_usd"],
        provider_status=result["provider_status"],
        is_simulated=result["is_simulated"],
    )
