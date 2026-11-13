import contextlib
import json
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import require_active_user, require_workspace_role
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.intelligence import (
    BusinessContext,
    ColumnSemanticMapping,
    DatasetProfile,
    DatasetRelationship,
    MetricDefinition,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.intelligence import (
    BusinessContextResponse,
    BusinessContextUpdateRequest,
    ColumnSemanticResponse,
    ColumnSemanticUpdateRequest,
    DatasetIntelligenceBundleResponse,
    DatasetProfileDetailResponse,
    RelationshipCreateRequest,
    RelationshipResponse,
    RelationshipUpdateRequest,
)
from app.services.intelligence.business_context_service import BusinessContextEngine
from app.services.intelligence.profiler import DatasetIntelligenceProfiler
from app.services.intelligence.relationship_service import RelationshipDiscoveryEngine
from app.services.intelligence.semantic_layer import SemanticLayerService

router = APIRouter(prefix="/datasets", tags=["Dataset Intelligence & Semantics"])


async def _resolve_dataset_version_and_parts(
    dataset_id: uuid.UUID,
    workspace_id: uuid.UUID,
    version_id: uuid.UUID | None,
    db: AsyncSession,
) -> tuple[Dataset, DatasetVersion, list[Path]]:
    stmt = (
        select(Dataset)
        .options(
            selectinload(Dataset.versions),
            selectinload(Dataset.current_version),
        )
        .where(
            Dataset.id == dataset_id,
            Dataset.workspace_id == workspace_id,
            Dataset.is_archived.is_(False),
        )
    )
    res = await db.execute(stmt)
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

    target_ver_id = version_id or dataset.current_version_id
    if not target_ver_id:
        raise DataLensException("Dataset has no active version to profile.", code="NOT_FOUND")

    ver_stmt = select(DatasetVersion).where(
        DatasetVersion.id == target_ver_id,
        DatasetVersion.dataset_id == dataset.id,
    )
    version = (await db.execute(ver_stmt)).scalar_one_or_none()
    if not version:
        raise DataLensException("Dataset version not found.", code="NOT_FOUND")

    storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
    manifest_path = storage_root / version.storage_key
    if not manifest_path.is_file():
        raise DataLensException("Dataset manifest not found on disk.", code="STORAGE_NOT_FOUND")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parquet_paths = [storage_root / p for p in manifest.get("parts", [])]

    return dataset, version, parquet_paths


@router.get(
    "/{dataset_id}/intelligence",
    response_model=DatasetIntelligenceBundleResponse,
)
async def get_dataset_intelligence(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> DatasetIntelligenceBundleResponse:
    """
    Returns the complete intelligence bundle: profile, column semantics,
    relationships, business context, and applicable metrics.
    """
    workspace, _ = ws_context
    dataset, version, _ = await _resolve_dataset_version_and_parts(
        dataset_id, workspace.id, version_id, db
    )

    # 1. Profile
    prof_stmt = select(DatasetProfile).where(DatasetProfile.dataset_version_id == version.id)
    prof = (await db.execute(prof_stmt)).scalar_one_or_none()

    # 2. Columns
    col_stmt = (
        select(ColumnSemanticMapping)
        .where(ColumnSemanticMapping.dataset_version_id == version.id)
        .order_by(ColumnSemanticMapping.column_name.asc())
    )
    cols = (await db.execute(col_stmt)).scalars().all()

    # 3. Relationships
    rel_stmt = select(DatasetRelationship).where(
        DatasetRelationship.workspace_id == workspace.id,
        (DatasetRelationship.source_dataset_id == dataset.id)
        | (DatasetRelationship.target_dataset_id == dataset.id),
    )
    rels = (await db.execute(rel_stmt)).scalars().all()

    # 4. Business Context
    bc_stmt = select(BusinessContext).where(BusinessContext.dataset_version_id == version.id)
    bcontext = (await db.execute(bc_stmt)).scalar_one_or_none()

    # 5. Metrics
    met_stmt = select(MetricDefinition).where(
        MetricDefinition.workspace_id == workspace.id,
        (MetricDefinition.dataset_id == dataset.id) | (MetricDefinition.dataset_id.is_(None)),
    )
    metrics = (await db.execute(met_stmt)).scalars().all()

    return DatasetIntelligenceBundleResponse(
        dataset_id=dataset.id,
        version_id=version.id,
        version_number=version.version_number,
        profile=DatasetProfileDetailResponse.model_validate(prof) if prof else None,
        columns=[ColumnSemanticResponse.model_validate(c) for c in cols],
        relationships=[RelationshipResponse.model_validate(r) for r in rels],
        business_context=BusinessContextResponse.model_validate(bcontext) if bcontext else None,
        metrics=[m for m in metrics],
    )


@router.post(
    "/{dataset_id}/intelligence/profile",
    response_model=DatasetIntelligenceBundleResponse,
    status_code=status.HTTP_200_OK,
)
async def run_intelligence_profiling(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> DatasetIntelligenceBundleResponse:
    """
    Executes deep dataset intelligence profiling over Parquet files, infers semantic types,
    persists column mappings, and synthesizes domain business context.
    """
    workspace, _ = ws_context
    dataset, version, parquet_paths = await _resolve_dataset_version_and_parts(
        dataset_id, workspace.id, version_id, db
    )

    # 1. Profile Parquet
    profile_data = DatasetIntelligenceProfiler.profile_parquet_dataset(parquet_paths)

    # 2. Persist Profile and Column Mappings
    db_profile, mappings = await SemanticLayerService.persist_profile_and_semantics(
        dataset=dataset,
        version=version,
        profile_data=profile_data,
        db=db,
    )

    # 3. Synthesize and Persist Business Context
    bcontext = await BusinessContextEngine.generate_and_persist_context(
        dataset=dataset,
        version=version,
        mappings=mappings,
        db=db,
    )

    # 4. Trigger Relationship Discovery in Workspace
    with contextlib.suppress(Exception):
        await RelationshipDiscoveryEngine.discover_workspace_relationships(
            workspace_id=workspace.id, db=db
        )

    await db.commit()

    # Re-fetch relationships and metrics
    rel_stmt = select(DatasetRelationship).where(
        DatasetRelationship.workspace_id == workspace.id,
        (DatasetRelationship.source_dataset_id == dataset.id)
        | (DatasetRelationship.target_dataset_id == dataset.id),
    )
    rels = (await db.execute(rel_stmt)).scalars().all()

    met_stmt = select(MetricDefinition).where(
        MetricDefinition.workspace_id == workspace.id,
        (MetricDefinition.dataset_id == dataset.id) | (MetricDefinition.dataset_id.is_(None)),
    )
    metrics = (await db.execute(met_stmt)).scalars().all()

    return DatasetIntelligenceBundleResponse(
        dataset_id=dataset.id,
        version_id=version.id,
        version_number=version.version_number,
        profile=DatasetProfileDetailResponse.model_validate(db_profile),
        columns=[ColumnSemanticResponse.model_validate(c) for c in mappings],
        relationships=[RelationshipResponse.model_validate(r) for r in rels],
        business_context=BusinessContextResponse.model_validate(bcontext),
        metrics=[m for m in metrics],
    )


@router.get(
    "/{dataset_id}/columns/semantics",
    response_model=list[ColumnSemanticResponse],
)
async def get_column_semantics(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[ColumnSemanticResponse]:
    workspace, _ = ws_context
    _, version, _ = await _resolve_dataset_version_and_parts(
        dataset_id, workspace.id, version_id, db
    )
    stmt = (
        select(ColumnSemanticMapping)
        .where(ColumnSemanticMapping.dataset_version_id == version.id)
        .order_by(ColumnSemanticMapping.column_name.asc())
    )
    cols = (await db.execute(stmt)).scalars().all()
    return [ColumnSemanticResponse.model_validate(c) for c in cols]


@router.patch(
    "/{dataset_id}/columns/semantics/{column_name}",
    response_model=ColumnSemanticResponse,
)
async def update_column_semantics(
    dataset_id: uuid.UUID,
    column_name: str,
    req: ColumnSemanticUpdateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ColumnSemanticResponse:
    workspace, _ = ws_context
    _, version, _ = await _resolve_dataset_version_and_parts(
        dataset_id, workspace.id, version_id, db
    )
    updates = req.model_dump(exclude_unset=True)
    mapping = await SemanticLayerService.update_column_mapping(
        version_id=version.id,
        column_name=column_name,
        updates=updates,
        user_id=current_user.id,
        db=db,
    )
    await db.commit()
    return ColumnSemanticResponse.model_validate(mapping)


@router.get(
    "/{dataset_id}/relationships",
    response_model=list[RelationshipResponse],
)
async def get_dataset_relationships(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RelationshipResponse]:
    workspace, _ = ws_context
    stmt = select(DatasetRelationship).where(
        DatasetRelationship.workspace_id == workspace.id,
        (DatasetRelationship.source_dataset_id == dataset_id)
        | (DatasetRelationship.target_dataset_id == dataset_id),
    )
    rels = (await db.execute(stmt)).scalars().all()
    return [RelationshipResponse.model_validate(r) for r in rels]


@router.post(
    "/{dataset_id}/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset_relationship(
    dataset_id: uuid.UUID,
    req: RelationshipCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RelationshipResponse:
    workspace, _ = ws_context
    rel = DatasetRelationship(
        workspace_id=workspace.id,
        source_dataset_id=req.source_dataset_id,
        source_column=req.source_column,
        target_dataset_id=req.target_dataset_id,
        target_column=req.target_column,
        relationship_type=req.relationship_type,
        confidence_score=1.0,
        status=req.status,
        evidence={"created_by": "USER_MANUAL"},
        confirmed_by_user_id=current_user.id,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return RelationshipResponse.model_validate(rel)


@router.post(
    "/{dataset_id}/relationships/discover",
    response_model=list[RelationshipResponse],
)
async def discover_relationships(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RelationshipResponse]:
    workspace, _ = ws_context
    rels = await RelationshipDiscoveryEngine.discover_workspace_relationships(
        workspace_id=workspace.id, db=db
    )
    await db.commit()
    return [RelationshipResponse.model_validate(r) for r in rels]


@router.patch(
    "/{dataset_id}/relationships/{relationship_id}",
    response_model=RelationshipResponse,
)
async def update_relationship(
    dataset_id: uuid.UUID,
    relationship_id: uuid.UUID,
    req: RelationshipUpdateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RelationshipResponse:
    workspace, _ = ws_context
    stmt = select(DatasetRelationship).where(
        DatasetRelationship.id == relationship_id,
        DatasetRelationship.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    rel = res.scalar_one_or_none()
    if not rel:
        raise DataLensException("Relationship not found.", code="NOT_FOUND")

    rel.status = req.status
    if req.relationship_type:
        rel.relationship_type = req.relationship_type
    rel.confirmed_by_user_id = current_user.id
    await db.commit()
    await db.refresh(rel)
    return RelationshipResponse.model_validate(rel)


@router.get(
    "/{dataset_id}/business-context",
    response_model=BusinessContextResponse,
)
async def get_business_context(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> BusinessContextResponse:
    workspace, _ = ws_context
    _, version, _ = await _resolve_dataset_version_and_parts(
        dataset_id, workspace.id, version_id, db
    )
    stmt = select(BusinessContext).where(BusinessContext.dataset_version_id == version.id)
    bc = (await db.execute(stmt)).scalar_one_or_none()
    if not bc:
        raise DataLensException("Business context not yet generated for this version.", code="NOT_FOUND")
    return BusinessContextResponse.model_validate(bc)


@router.patch(
    "/{dataset_id}/business-context",
    response_model=BusinessContextResponse,
)
async def update_business_context(
    dataset_id: uuid.UUID,
    req: BusinessContextUpdateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> BusinessContextResponse:
    workspace, _ = ws_context
    _, version, _ = await _resolve_dataset_version_and_parts(
        dataset_id, workspace.id, version_id, db
    )
    stmt = select(BusinessContext).where(BusinessContext.dataset_version_id == version.id)
    bc = (await db.execute(stmt)).scalar_one_or_none()
    if not bc:
        bc = BusinessContext(
            dataset_version_id=version.id,
            dataset_id=dataset_id,
            business_domain=req.business_domain or "GENERAL_BUSINESS",
            purpose=req.purpose or "",
            important_entities=req.important_entities or [],
            key_dimensions=req.key_dimensions or [],
            important_measures=req.important_measures or [],
            suggested_kpis=req.suggested_kpis or [],
            data_quality_limitations=[],
            business_assumptions=[],
            is_user_confirmed=True,
            confirmed_by_user_id=current_user.id,
        )
        db.add(bc)
    else:
        if req.business_domain:
            bc.business_domain = req.business_domain
        if req.purpose is not None:
            bc.purpose = req.purpose
        if req.important_entities is not None:
            bc.important_entities = req.important_entities
        if req.key_dimensions is not None:
            bc.key_dimensions = req.key_dimensions
        if req.important_measures is not None:
            bc.important_measures = req.important_measures
        if req.suggested_kpis is not None:
            bc.suggested_kpis = req.suggested_kpis
        bc.is_user_confirmed = req.is_user_confirmed
        bc.confirmed_by_user_id = current_user.id

    await db.commit()
    await db.refresh(bc)
    return BusinessContextResponse.model_validate(bc)
