import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.transformation import (
    PreviewRequest,
    PreviewResponse,
    ReorderStepsRequest,
    RunPipelineRequest,
    TransformationPipelineCreate,
    TransformationPipelineResponse,
    TransformationPipelineSummary,
    TransformationPipelineUpdate,
    TransformationRunResponse,
    TransformationStepCreate,
    TransformationStepResponse,
    TransformationStepUpdate,
    ValidateFormulaRequest,
    ValidateFormulaResponse,
)
from app.services.transformation.transformation_service import TransformationService

router = APIRouter(prefix="/transformations", tags=["Data Transformation"])


# ---------------------------------------------------------------------------
# Pipeline CRUD
# ---------------------------------------------------------------------------

@router.post("/pipelines", response_model=TransformationPipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    req: TransformationPipelineCreate,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransformationPipelineResponse:
    workspace, _ = ws_context
    return await TransformationService.create_pipeline(
        workspace_id=workspace.id,
        user_id=current_user.id,
        data=req,
        db=db,
    )


@router.get("/pipelines", response_model=list[TransformationPipelineSummary])
async def list_pipelines(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TransformationPipelineSummary]:
    workspace, _ = ws_context
    return await TransformationService.list_pipelines(
        workspace_id=workspace.id,
        db=db,
    )


@router.get("/pipelines/{pipeline_id}", response_model=TransformationPipelineResponse)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransformationPipelineResponse:
    workspace, _ = ws_context
    return await TransformationService.get_pipeline(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        db=db,
    )


@router.put("/pipelines/{pipeline_id}", response_model=TransformationPipelineResponse)
async def update_pipeline(
    pipeline_id: uuid.UUID,
    req: TransformationPipelineUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransformationPipelineResponse:
    workspace, _ = ws_context
    return await TransformationService.update_pipeline(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        data=req,
        db=db,
    )


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    await TransformationService.delete_pipeline(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# Step CRUD
# ---------------------------------------------------------------------------

@router.post("/pipelines/{pipeline_id}/steps", response_model=TransformationStepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(
    pipeline_id: uuid.UUID,
    req: TransformationStepCreate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransformationStepResponse:
    workspace, _ = ws_context
    return await TransformationService.add_step(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        data=req,
        db=db,
    )


@router.put("/pipelines/{pipeline_id}/steps/{step_id}", response_model=TransformationStepResponse)
async def update_step(
    pipeline_id: uuid.UUID,
    step_id: uuid.UUID,
    req: TransformationStepUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransformationStepResponse:
    workspace, _ = ws_context
    return await TransformationService.update_step(
        pipeline_id=pipeline_id,
        step_id=step_id,
        workspace_id=workspace.id,
        data=req,
        db=db,
    )


@router.delete("/pipelines/{pipeline_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    pipeline_id: uuid.UUID,
    step_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    await TransformationService.delete_step(
        pipeline_id=pipeline_id,
        step_id=step_id,
        workspace_id=workspace.id,
        db=db,
    )


@router.post("/pipelines/{pipeline_id}/reorder", response_model=list[TransformationStepResponse])
async def reorder_steps(
    pipeline_id: uuid.UUID,
    req: ReorderStepsRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TransformationStepResponse]:
    workspace, _ = ws_context
    return await TransformationService.reorder_steps(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        step_ids=req.step_ids,
        db=db,
    )


# ---------------------------------------------------------------------------
# Preview, Execution, and Validation
# ---------------------------------------------------------------------------

@router.post("/pipelines/{pipeline_id}/preview", response_model=PreviewResponse)
async def preview_pipeline(
    pipeline_id: uuid.UUID,
    req: PreviewRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PreviewResponse:
    workspace, _ = ws_context
    return await TransformationService.preview_pipeline(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        step_index=req.step_index,
        limit=req.limit,
        db=db,
    )


@router.post("/pipelines/{pipeline_id}/run", response_model=TransformationRunResponse)
async def run_pipeline(
    pipeline_id: uuid.UUID,
    req: RunPipelineRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransformationRunResponse:
    workspace, _ = ws_context
    return await TransformationService.run_pipeline(
        pipeline_id=pipeline_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        output_name=req.output_dataset_name,
        output_desc=req.output_dataset_description,
        db=db,
    )


@router.post("/validate-formula", response_model=ValidateFormulaResponse)
async def validate_formula(
    req: ValidateFormulaRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
) -> ValidateFormulaResponse:
    return TransformationService.validate_formula(
        expression=req.expression,
        columns=req.columns,
    )
