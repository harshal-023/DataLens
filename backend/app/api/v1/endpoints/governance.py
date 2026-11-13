"""FastAPI endpoints for Phase 5C Enterprise Governance, RBAC, Audit, and Security Policies."""

import csv
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.common import SuccessEnvelope
from app.schemas.governance import (
    AuditLogListResponse,
    CustomRoleCreate,
    CustomRoleDuplicateRequest,
    CustomRoleResponse,
    CustomRoleUpdate,
    DatasetGovernanceResponse,
    DatasetGovernanceUpdate,
    PermissionsCatalogResponse,
    ResourceAccessPolicyCreate,
    ResourceAccessPolicyResponse,
    SecurityEventResponse,
    SecurityEventStatusUpdate,
    UserSessionResponse,
    WorkspaceSecurityPolicyResponse,
    WorkspaceSecurityPolicyUpdate,
)
from app.services.governance_service import GovernanceService
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["Enterprise Governance & Security"])

# ---------------------------------------------------------------------------
# Permissions Catalog
# ---------------------------------------------------------------------------


@router.get(
    "/permissions/catalog",
    response_model=SuccessEnvelope[PermissionsCatalogResponse],
    summary="Get Permissions Catalog",
)
async def get_permissions_catalog():
    catalog = GovernanceService.get_permissions_catalog()
    return SuccessEnvelope(data=catalog)


# ---------------------------------------------------------------------------
# Custom Roles Management
# ---------------------------------------------------------------------------


@router.get(
    "/roles",
    response_model=SuccessEnvelope[list[CustomRoleResponse]],
    summary="List Workspace Custom Roles",
)
async def list_roles(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    roles = await GovernanceService.list_custom_roles(db, workspace_id)
    return SuccessEnvelope(data=roles)


@router.post(
    "/roles",
    response_model=SuccessEnvelope[CustomRoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Role",
)
async def create_role(
    req: CustomRoleCreate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    role = await GovernanceService.create_custom_role(db, workspace_id, current_user, req)
    return SuccessEnvelope(data=role, message="Custom role created successfully.")


@router.patch(
    "/roles/{role_id}",
    response_model=SuccessEnvelope[CustomRoleResponse],
    summary="Update Custom Role",
)
async def update_role(
    role_id: uuid.UUID,
    req: CustomRoleUpdate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    role = await GovernanceService.update_custom_role(db, workspace_id, role_id, current_user, req)
    return SuccessEnvelope(data=role, message="Custom role updated.")


@router.post(
    "/roles/{role_id}/duplicate",
    response_model=SuccessEnvelope[CustomRoleResponse],
    summary="Duplicate Custom Role",
)
async def duplicate_role(
    role_id: uuid.UUID,
    req: CustomRoleDuplicateRequest,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    clone = await GovernanceService.duplicate_custom_role(
        db, workspace_id, role_id, current_user, req.new_name
    )
    return SuccessEnvelope(data=clone, message="Custom role duplicated.")


@router.delete(
    "/roles/{role_id}",
    response_model=SuccessEnvelope[dict],
    summary="Delete Custom Role",
)
async def delete_role(
    role_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await GovernanceService.delete_custom_role(db, workspace_id, role_id, current_user)
    return SuccessEnvelope(data={"deleted": True}, message="Custom role deleted.")


@router.post(
    "/roles/assign",
    response_model=SuccessEnvelope[dict],
    summary="Assign Custom Role to Member",
)
async def assign_custom_role(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    target_user_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    custom_role_id: uuid.UUID | None = None,
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await GovernanceService.assign_custom_role_to_member(
        db, workspace_id, target_user_id, custom_role_id, current_user
    )
    return SuccessEnvelope(data={"assigned": True}, message="Role assigned successfully.")


# ---------------------------------------------------------------------------
# Resource-Level Access Policies (RLAC)
# ---------------------------------------------------------------------------


@router.get(
    "/permissions/resources",
    response_model=SuccessEnvelope[list[ResourceAccessPolicyResponse]],
    summary="List Resource Access Policies",
)
async def list_resource_policies(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    resource_type: Annotated[str, Query(...)],
    resource_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    policies = await GovernanceService.list_resource_policies(
        db, workspace_id, resource_type, resource_id
    )
    return SuccessEnvelope(data=policies)


@router.post(
    "/permissions/resources",
    response_model=SuccessEnvelope[ResourceAccessPolicyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Resource Access Policy",
)
async def create_resource_policy(
    req: ResourceAccessPolicyCreate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    policy = await GovernanceService.create_resource_policy(
        db, workspace_id, current_user, req
    )
    return SuccessEnvelope(data=policy, message="Resource access policy created.")


@router.delete(
    "/permissions/resources/{policy_id}",
    response_model=SuccessEnvelope[dict],
    summary="Delete Resource Access Policy",
)
async def delete_resource_policy(
    policy_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    await GovernanceService.delete_resource_policy(db, workspace_id, policy_id, current_user)
    return SuccessEnvelope(data={"deleted": True}, message="Resource policy revoked.")


# ---------------------------------------------------------------------------
# Data Governance & Sensitivity
# ---------------------------------------------------------------------------


@router.get(
    "/governance/datasets/{dataset_id}",
    response_model=SuccessEnvelope[DatasetGovernanceResponse],
    summary="Get Dataset Governance Details",
)
async def get_dataset_governance(
    dataset_id: uuid.UUID,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    gov = await GovernanceService.get_or_create_dataset_governance(db, workspace_id, dataset_id)
    return SuccessEnvelope(
        data=DatasetGovernanceResponse(
            id=gov.id,
            workspace_id=gov.workspace_id,
            dataset_id=gov.dataset_id,
            sensitivity_level=gov.sensitivity_level,
            export_restricted=gov.export_restricted,
            column_masks=gov.column_masks,
            approved_by=gov.approved_by,
            approved_at=gov.approved_at,
            updated_at=gov.updated_at,
        )
    )


@router.put(
    "/governance/datasets/{dataset_id}",
    response_model=SuccessEnvelope[DatasetGovernanceResponse],
    summary="Update Dataset Governance & Column Masking",
)
async def update_dataset_governance(
    dataset_id: uuid.UUID,
    req: DatasetGovernanceUpdate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    res = await GovernanceService.update_dataset_governance(
        db, workspace_id, dataset_id, current_user, req
    )
    return SuccessEnvelope(data=res, message="Data governance policies updated.")


# ---------------------------------------------------------------------------
# Immutable Enterprise Audit Logs
# ---------------------------------------------------------------------------


@router.get(
    "/audit-logs",
    response_model=SuccessEnvelope[AuditLogListResponse],
    summary="List Enterprise Audit Logs",
)
async def list_audit_logs(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    outcome: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    logs = await GovernanceService.list_audit_logs(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        outcome=outcome,
        page=page,
        page_size=page_size,
    )
    return SuccessEnvelope(data=logs)


@router.get(
    "/audit-logs/verify",
    summary="Cryptographically verify enterprise audit log chain integrity",
)
async def verify_audit_chain(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    verification = await GovernanceService.verify_audit_chain(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
    )
    return SuccessEnvelope(data=verification)


@router.get(
    "/audit-logs/export",
    summary="Export Enterprise Audit Logs to CSV",
)
async def export_audit_logs(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    logs = await GovernanceService.list_audit_logs(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        page=1,
        page_size=1000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Timestamp", "Actor Email", "Action", "Resource Type",
        "Resource ID", "Outcome", "IP Address", "Correlation ID", "Chained Hash"
    ])
    for item in logs.items:
        writer.writerow([
            str(item.id),
            item.timestamp.isoformat(),
            item.actor_email or "System",
            item.action,
            item.resource_type,
            str(item.resource_id) if item.resource_id else "",
            item.outcome,
            item.ip_address or "",
            item.correlation_id or "",
            item.chained_hash,
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_logs_{workspace_id}.csv"'},
    )


# ---------------------------------------------------------------------------
# Security Events & Monitoring
# ---------------------------------------------------------------------------


@router.get(
    "/security-events",
    response_model=SuccessEnvelope[list[SecurityEventResponse]],
    summary="List Security Incident Events",
)
async def list_security_events(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    severity: str | None = None,
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    events = await GovernanceService.list_security_events(
        db=db,
        workspace_id=workspace_id,
        actor=current_user,
        status_filter=status,
        severity_filter=severity,
    )
    return SuccessEnvelope(data=events)


@router.patch(
    "/security-events/{event_id}",
    response_model=SuccessEnvelope[SecurityEventResponse],
    summary="Update Security Event Status",
)
async def update_security_event_status(
    event_id: uuid.UUID,
    req: SecurityEventStatusUpdate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    res = await GovernanceService.update_security_event_status(
        db=db,
        workspace_id=workspace_id,
        event_id=event_id,
        actor=current_user,
        status=req.status,
        notes=req.notes,
    )
    return SuccessEnvelope(data=res, message="Security incident status updated.")


# ---------------------------------------------------------------------------
# User Sessions Management
# ---------------------------------------------------------------------------


@router.get(
    "/sessions",
    response_model=SuccessEnvelope[list[UserSessionResponse]],
    summary="List Active User Sessions",
)
async def list_sessions(
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    sessions = await GovernanceService.list_active_sessions(db, current_user.id)
    return SuccessEnvelope(data=sessions)


@router.delete(
    "/sessions/{session_id}",
    response_model=SuccessEnvelope[dict],
    summary="Revoke Specific User Session",
)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await GovernanceService.revoke_session(db, current_user.id, session_id)
    return SuccessEnvelope(data={"revoked": True}, message="Session revoked successfully.")


@router.post(
    "/sessions/revoke-others",
    response_model=SuccessEnvelope[dict],
    summary="Revoke All Other User Sessions",
)
async def revoke_all_other_sessions(
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count = await GovernanceService.revoke_all_other_sessions(db, current_user.id, current_token_hash="CURRENT")
    return SuccessEnvelope(
        data={"revoked_count": count},
        message=f"Successfully signed out of {count} other sessions.",
    )


# ---------------------------------------------------------------------------
# Workspace Security Policies
# ---------------------------------------------------------------------------


@router.get(
    "/workspace-security",
    response_model=SuccessEnvelope[WorkspaceSecurityPolicyResponse],
    summary="Get Workspace Security Policies",
)
async def get_security_policies(
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    policy = await GovernanceService.get_or_create_policy(db, workspace_id)
    return SuccessEnvelope(data=WorkspaceSecurityPolicyResponse.model_validate(policy))


@router.put(
    "/workspace-security",
    response_model=SuccessEnvelope[WorkspaceSecurityPolicyResponse],
    summary="Update Workspace Security Policies",
)
async def update_security_policies(
    req: WorkspaceSecurityPolicyUpdate,
    workspace_id: Annotated[uuid.UUID, Query(...)],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await WorkspaceService.get_workspace(workspace_id, current_user.id, db)
    updated = await GovernanceService.update_security_policy(
        db, workspace_id, current_user, req
    )
    return SuccessEnvelope(data=updated, message="Security policies updated.")
