import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.dataset import (
    DatasetDetailResponse,
    DatasetResponse,
    DatasetStatusResponse,
    DatasetVersionResponse,
    PaginatedDatasetListResponse,
    PaginatedRowsResponse,
)
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: Annotated[UploadFile, File(...)],
    name: Annotated[str, Form(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    selected_worksheet: Annotated[str | None, Form()] = None,
) -> DatasetResponse:
    workspace, _ = ws_context
    dataset = await DatasetService.create_dataset_from_upload(
        workspace_id=workspace.id,
        uploader_id=current_user.id,
        name=name,
        upload_file=file,
        selected_worksheet=selected_worksheet,
        db=db,
    )
    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=PaginatedDatasetListResponse)
async def list_datasets(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_dir: Annotated[str, Query()] = "desc",
) -> PaginatedDatasetListResponse:
    workspace, _ = ws_context
    result = await DatasetService.list_datasets(
        workspace_id=workspace.id,
        page=page,
        page_size=page_size,
        search=search,
        status=status_filter,
        sort_by=sort_by,
        sort_dir=sort_dir,
        db=db,
    )
    return PaginatedDatasetListResponse(
        items=[DatasetResponse.model_validate(d) for d in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset_detail(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetDetailResponse:
    workspace, _ = ws_context
    dataset = await DatasetService.get_dataset(dataset_id, workspace.id, db)
    versions = [DatasetVersionResponse.model_validate(v) for v in dataset.versions]
    curr_v = (
        DatasetVersionResponse.model_validate(dataset.current_version)
        if dataset.current_version
        else None
    )
    schema_meta = dataset.current_version.schema_metadata if dataset.current_version else {}

    resp = DatasetDetailResponse.model_validate(dataset)
    resp.versions = versions
    resp.current_version = curr_v
    resp.schema_metadata = schema_meta
    return resp


@router.get("/{dataset_id}/status", response_model=DatasetStatusResponse)
async def get_dataset_status(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetStatusResponse:
    workspace, _ = ws_context
    status_dict = await DatasetService.get_dataset_status(dataset_id, workspace.id, db)
    return DatasetStatusResponse(**status_dict)


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionResponse])
async def list_dataset_versions(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DatasetVersionResponse]:
    workspace, _ = ws_context
    versions = await DatasetService.get_dataset_versions(dataset_id, workspace.id, db)
    return [DatasetVersionResponse.model_validate(v) for v in versions]


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
async def get_dataset_version_detail(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetVersionResponse:
    workspace, _ = ws_context
    version = await DatasetService.get_version(dataset_id, version_id, workspace.id, db)
    return DatasetVersionResponse.model_validate(version)


@router.get("/{dataset_id}/rows", response_model=PaginatedRowsResponse)
async def get_dataset_rows(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
    sort_by: Annotated[str | None, Query()] = None,
    sort_dir: Annotated[str, Query()] = "asc",
    columns: Annotated[list[str] | None, Query()] = None,
) -> PaginatedRowsResponse:
    workspace, _ = ws_context
    result = await DatasetService.get_dataset_rows(
        dataset_id=dataset_id,
        workspace_id=workspace.id,
        version_id=version_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        columns=columns,
        db=db,
    )
    return PaginatedRowsResponse(**result)


@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_replacement_version(
    dataset_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    selected_worksheet: Annotated[str | None, Form()] = None,
) -> DatasetVersionResponse:
    workspace, _ = ws_context
    version = await DatasetService.create_replacement_version(
        dataset_id=dataset_id,
        workspace_id=workspace.id,
        upload_file=file,
        selected_worksheet=selected_worksheet,
        db=db,
    )
    return DatasetVersionResponse.model_validate(version)


@router.get("/{dataset_id}/versions/{version_id}/download")
async def download_original_version_file(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    workspace, _ = ws_context
    data, filename, mime = await DatasetService.download_original_file(
        dataset_id=dataset_id,
        version_id=version_id,
        workspace_id=workspace.id,
        db=db,
    )
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    permanent: Annotated[bool, Query()] = False,
) -> dict[str, str]:
    workspace, _ = ws_context
    await DatasetService.delete_dataset(
        dataset_id=dataset_id,
        workspace_id=workspace.id,
        permanent=permanent,
        db=db,
    )
    return {"message": "Dataset deleted successfully" if permanent else "Dataset archived successfully"}
