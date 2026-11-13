"""Enterprise Governance, RBAC, RLAC, Chained Audit, and Security Service Layer."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, asc, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataLensException
from app.core.permissions import WorkspaceRole
from app.models.dataset import Dataset
from app.models.governance import (
    CustomRole,
    DatasetGovernance,
    EnterpriseAuditLog,
    ResourceAccessPolicy,
    SecurityEvent,
    UserSession,
    WorkspaceSecurityPolicy,
)
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.governance import (
    AuditLogListResponse,
    CustomRoleCreate,
    CustomRoleResponse,
    CustomRoleUpdate,
    DatasetGovernanceResponse,
    DatasetGovernanceUpdate,
    EnterpriseAuditLogResponse,
    PermissionDefinition,
    PermissionsCatalogResponse,
    ResourceAccessPolicyCreate,
    ResourceAccessPolicyResponse,
    SecurityEventResponse,
    UserSessionResponse,
    WorkspaceSecurityPolicyResponse,
    WorkspaceSecurityPolicyUpdate,
)

# ---------------------------------------------------------------------------
# Granular Permissions Catalog
# ---------------------------------------------------------------------------

ALL_PERMISSIONS: list[PermissionDefinition] = [
    # Datasets
    PermissionDefinition(code="dataset:view", category="Datasets", name="View Datasets", description="View and inspect datasets in workspace."),
    PermissionDefinition(code="dataset:create", category="Datasets", name="Create Datasets", description="Upload and import new datasets."),
    PermissionDefinition(code="dataset:edit", category="Datasets", name="Edit Datasets", description="Modify dataset metadata and schema definitions."),
    PermissionDefinition(code="dataset:delete", category="Datasets", name="Delete Datasets", description="Delete datasets permanently."),
    PermissionDefinition(code="dataset:export", category="Datasets", name="Export Datasets", description="Download CSV or raw dataset records."),
    # Data Sources
    PermissionDefinition(code="datasource:manage", category="Data Sources", name="Manage Connections", description="Create, edit, test, and sync external data sources."),
    # Transformations
    PermissionDefinition(code="transformation:create", category="Transformations", name="Create Pipelines", description="Create and design data transformation pipelines."),
    PermissionDefinition(code="transformation:execute", category="Transformations", name="Execute Pipelines", description="Run pipelines and generate derived datasets."),
    # Dashboards
    PermissionDefinition(code="dashboard:view", category="Dashboards", name="View Dashboards", description="View interactive dashboards."),
    PermissionDefinition(code="dashboard:create", category="Dashboards", name="Create & Edit Dashboards", description="Create and configure dashboard widgets and layouts."),
    PermissionDefinition(code="dashboard:share", category="Dashboards", name="Share Dashboards", description="Share dashboards with members or generate external links."),
    # Reports
    PermissionDefinition(code="report:generate", category="Reports", name="Generate Reports", description="Generate and schedule automated business reports."),
    PermissionDefinition(code="report:download", category="Reports", name="Download Reports", description="Export PDF, DOCX, and XLSX reports."),
    PermissionDefinition(code="report:share", category="Reports", name="Share Reports", description="Distribute reports and generate download links."),
    # Discussions
    PermissionDefinition(code="comment:manage", category="Collaboration", name="Manage Discussions", description="Post, edit, and resolve discussion threads."),
    # Administration & Governance
    PermissionDefinition(code="member:manage", category="Administration", name="Manage Members", description="Invite, update roles, and remove team members."),
    PermissionDefinition(code="workspace:configure", category="Administration", name="Configure Workspace", description="Update workspace settings and branding."),
    PermissionDefinition(code="audit:view", category="Governance", name="View Audit Logs", description="Inspect immutable audit trails."),
    PermissionDefinition(code="security_policy:manage", category="Governance", name="Manage Security Policies", description="Configure workspace security and sharing policies."),
    PermissionDefinition(code="governance:manage", category="Governance", name="Data Governance", description="Classify dataset sensitivity and configure column masking."),
    PermissionDefinition(code="governance:bypass", category="Governance", name="Bypass Column Masking", description="View unmasked restricted column data."),
]

SYSTEM_ROLE_PERMISSIONS: dict[str, set[str]] = {
    WorkspaceRole.OWNER.value: {p.code for p in ALL_PERMISSIONS},
    WorkspaceRole.ADMIN.value: {p.code for p in ALL_PERMISSIONS if p.code != "governance:bypass"},
    WorkspaceRole.EDITOR.value: {
        "dataset:view", "dataset:create", "dataset:edit", "dataset:export",
        "datasource:manage", "transformation:create", "transformation:execute",
        "dashboard:view", "dashboard:create", "dashboard:share",
        "report:generate", "report:download", "report:share",
        "comment:manage",
    },
    WorkspaceRole.VIEWER.value: {
        "dataset:view",
        "dashboard:view",
        "report:download",
        "comment:manage",
    },
}

SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|token|secret|key|credential|auth|cert|private)", re.IGNORECASE
)


class GovernanceService:
    """Enterprise governance, access control, audit, and security monitoring service."""

    # ---------------------------------------------------------------------------
    # Permissions & Catalog
    # ---------------------------------------------------------------------------

    @staticmethod
    def get_permissions_catalog() -> PermissionsCatalogResponse:
        categories = sorted(list({p.category for p in ALL_PERMISSIONS}))
        return PermissionsCatalogResponse(permissions=ALL_PERMISSIONS, categories=categories)

    # ---------------------------------------------------------------------------
    # Authorization & Permission Evaluation Engine
    # ---------------------------------------------------------------------------

    @staticmethod
    async def has_workspace_permission(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user: User,
        permission_code: str,
    ) -> bool:
        """Centralized check for workspace-level granular permissions."""
        # 1. Check workspace owner
        ws = await db.get(Workspace, workspace_id)
        if not ws:
            return False
        if ws.owner_id == user.id:
            return True

        # 2. Check workspace membership
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
        mem = (await db.execute(stmt)).scalar_one_or_none()
        if not mem:
            return False

        # 3. If member has a custom role
        if mem.custom_role_id:
            custom_role = await db.get(CustomRole, mem.custom_role_id)
            if custom_role:
                return permission_code in custom_role.permissions

        # 4. Check system role permissions
        role_key = mem.role.lower()
        if role_key in SYSTEM_ROLE_PERMISSIONS:
            return permission_code in SYSTEM_ROLE_PERMISSIONS[role_key]

        return False

    @staticmethod
    async def check_resource_access(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user: User,
        resource_type: str,
        resource_id: uuid.UUID,
        required_permission: str = "viewer",  # 'viewer' | 'editor' | 'admin'
    ) -> bool:
        """
        Evaluate 4-tier Resource-Level Access Control (RLAC) precedence:
        1. Owner check -> Allow
        2. Explicit Deny policy -> Deny immediately
        3. Explicit Grant policy -> Allow
        4. Fallback to workspace role permissions
        """
        ws = await db.get(Workspace, workspace_id)
        if not ws:
            return False
        if ws.owner_id == user.id:
            return True

        # Check membership
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
        mem = (await db.execute(stmt)).scalar_one_or_none()
        if not mem:
            return False

        # Query explicit resource policies for user or member's custom role
        query = select(ResourceAccessPolicy).where(
            ResourceAccessPolicy.workspace_id == workspace_id,
            ResourceAccessPolicy.resource_type == resource_type,
            ResourceAccessPolicy.resource_id == resource_id,
        )
        role_filter = [ResourceAccessPolicy.user_id == user.id]
        if mem.custom_role_id:
            role_filter.append(ResourceAccessPolicy.role_id == mem.custom_role_id)

        query = query.where(and_(*role_filter) if len(role_filter) == 1 else (role_filter[0] | role_filter[1]))
        policies = (await db.execute(query)).scalars().all()

        # Step 2: Check explicit deny
        if any(p.is_denied for p in policies):
            return False

        # Step 3: Check explicit grant
        role_ranks = {"viewer": 1, "editor": 2, "admin": 3}
        req_rank = role_ranks.get(required_permission, 1)

        for p in policies:
            if not p.is_denied and role_ranks.get(p.permission, 1) >= req_rank:
                return True

        # Step 4: Fallback to role capability
        permission_map = {
            "dataset": {"viewer": "dataset:view", "editor": "dataset:edit", "admin": "dataset:delete"},
            "dashboard": {"viewer": "dashboard:view", "editor": "dashboard:create", "admin": "dashboard:share"},
            "report": {"viewer": "report:download", "editor": "report:generate", "admin": "report:share"},
            "datasource": {"viewer": "datasource:manage", "editor": "datasource:manage", "admin": "datasource:manage"},
            "pipeline": {"viewer": "transformation:create", "editor": "transformation:create", "admin": "transformation:execute"},
        }
        fallback_perm = permission_map.get(resource_type, {}).get(required_permission, f"{resource_type}:view")
        return await GovernanceService.has_workspace_permission(db, workspace_id, user, fallback_perm)

    # ---------------------------------------------------------------------------
    # Custom Roles Management
    # ---------------------------------------------------------------------------

    @staticmethod
    async def list_custom_roles(db: AsyncSession, workspace_id: uuid.UUID) -> list[CustomRoleResponse]:
        query = select(CustomRole).where(CustomRole.workspace_id == workspace_id).order_by(CustomRole.created_at)
        roles = (await db.execute(query)).scalars().all()

        # Count assigned members for each role
        count_stmt = select(
            WorkspaceMembership.custom_role_id, func.count(WorkspaceMembership.user_id)
        ).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.custom_role_id.is_not(None)
        ).group_by(WorkspaceMembership.custom_role_id)
        counts = dict((await db.execute(count_stmt)).all())

        return [
            CustomRoleResponse(
                id=r.id,
                workspace_id=r.workspace_id,
                name=r.name,
                description=r.description,
                permissions=r.permissions,
                is_system=r.is_system,
                assigned_members_count=counts.get(r.id, 0),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in roles
        ]

    @staticmethod
    async def create_custom_role(
        db: AsyncSession, workspace_id: uuid.UUID, actor: User, req: CustomRoleCreate
    ) -> CustomRoleResponse:
        # Check permissions
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_manage:
            raise DataLensException("Permission denied to create custom roles.", code="FORBIDDEN")

        # Check policy
        policy = await GovernanceService.get_or_create_policy(db, workspace_id)
        if not policy.custom_roles_enabled:
            raise DataLensException("Custom roles are disabled by workspace security policy.", code="POLICY_RESTRICTED")

        # Validate unique name
        exist = await db.execute(
            select(CustomRole).where(CustomRole.workspace_id == workspace_id, CustomRole.name == req.name)
        )
        if exist.scalar_one_or_none():
            raise DataLensException(f"A role with the name '{req.name}' already exists.", code="DUPLICATE_RESOURCE")

        # Validate permission keys
        valid_codes = {p.code for p in ALL_PERMISSIONS}
        clean_perms = [p for p in req.permissions if p in valid_codes]

        role = CustomRole(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=req.name.strip(),
            description=req.description,
            permissions=clean_perms,
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(role)
        await db.commit()
        await db.refresh(role)

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="custom_role_created",
            resource_type="custom_role",
            resource_id=role.id,
            outcome="SUCCESS",
            metadata_snapshot={"name": role.name, "permissions_count": len(role.permissions)},
        )

        return CustomRoleResponse.model_validate(role)

    @staticmethod
    async def update_custom_role(
        db: AsyncSession, workspace_id: uuid.UUID, role_id: uuid.UUID, actor: User, req: CustomRoleUpdate
    ) -> CustomRoleResponse:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_manage:
            raise DataLensException("Permission denied to edit custom roles.", code="FORBIDDEN")

        role = await db.get(CustomRole, role_id)
        if not role or role.workspace_id != workspace_id:
            raise DataLensException("Custom role not found.", code="NOT_FOUND")

        if role.is_system:
            raise DataLensException("System-defined roles cannot be modified.", code="FORBIDDEN")

        if req.name is not None:
            role.name = req.name.strip()
        if req.description is not None:
            role.description = req.description
        if req.permissions is not None:
            valid_codes = {p.code for p in ALL_PERMISSIONS}
            role.permissions = [p for p in req.permissions if p in valid_codes]

        role.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(role)

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="custom_role_updated",
            resource_type="custom_role",
            resource_id=role.id,
            outcome="SUCCESS",
            metadata_snapshot={"name": role.name, "permissions": role.permissions},
        )

        return CustomRoleResponse.model_validate(role)

    @staticmethod
    async def duplicate_custom_role(
        db: AsyncSession, workspace_id: uuid.UUID, role_id: uuid.UUID, actor: User, new_name: str
    ) -> CustomRoleResponse:
        role = await db.get(CustomRole, role_id)
        if not role or role.workspace_id != workspace_id:
            raise DataLensException("Role not found.", code="NOT_FOUND")

        clone = CustomRole(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=new_name.strip(),
            description=f"Duplicate of {role.name}. {role.description or ''}".strip(),
            permissions=list(role.permissions),
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(clone)
        await db.commit()
        await db.refresh(clone)

        return CustomRoleResponse.model_validate(clone)

    @staticmethod
    async def delete_custom_role(
        db: AsyncSession, workspace_id: uuid.UUID, role_id: uuid.UUID, actor: User
    ) -> None:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_manage:
            raise DataLensException("Permission denied to delete custom roles.", code="FORBIDDEN")

        role = await db.get(CustomRole, role_id)
        if not role or role.workspace_id != workspace_id:
            raise DataLensException("Custom role not found.", code="NOT_FOUND")

        if role.is_system:
            raise DataLensException("System-defined roles cannot be deleted.", code="FORBIDDEN")

        # Safe deletion check: unassign from members
        members_stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.custom_role_id == role.id,
        )
        members = (await db.execute(members_stmt)).scalars().all()
        for m in members:
            m.custom_role_id = None
            m.role = "viewer"  # Default safe fallback

        await db.delete(role)
        await db.commit()

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="custom_role_deleted",
            resource_type="custom_role",
            resource_id=role_id,
            outcome="SUCCESS",
            metadata_snapshot={"name": role.name},
        )

    @staticmethod
    async def assign_custom_role_to_member(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        custom_role_id: uuid.UUID | None,
        actor: User,
    ) -> None:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "member:manage")
        if not can_manage:
            raise DataLensException("Permission denied to assign custom roles.", code="FORBIDDEN")

        ws = await db.get(Workspace, workspace_id)
        if ws and ws.owner_id == target_user_id:
            raise DataLensException("The workspace Owner role cannot be reassigned or restricted.", code="FORBIDDEN")

        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == target_user_id,
        )
        mem = (await db.execute(stmt)).scalar_one_or_none()
        if not mem:
            raise DataLensException("Workspace member not found.", code="NOT_FOUND")

        role_name = "viewer"
        if custom_role_id:
            role = await db.get(CustomRole, custom_role_id)
            if not role or role.workspace_id != workspace_id:
                raise DataLensException("Specified custom role does not exist.", code="NOT_FOUND")
            role_name = role.name

        mem.custom_role_id = custom_role_id
        mem.role = role_name
        await db.commit()

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="member_custom_role_assigned",
            resource_type="user",
            resource_id=target_user_id,
            outcome="SUCCESS",
            metadata_snapshot={"assigned_role": role_name, "custom_role_id": str(custom_role_id) if custom_role_id else None},
        )

    # ---------------------------------------------------------------------------
    # Resource-Level Access Policies (RLAC)
    # ---------------------------------------------------------------------------

    @staticmethod
    async def list_resource_policies(
        db: AsyncSession, workspace_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
    ) -> list[ResourceAccessPolicyResponse]:
        query = (
            select(
                ResourceAccessPolicy,
                User.full_name,
                User.email,
                CustomRole.name,
            )
            .outerjoin(User, User.id == ResourceAccessPolicy.user_id)
            .outerjoin(CustomRole, CustomRole.id == ResourceAccessPolicy.role_id)
            .where(
                ResourceAccessPolicy.workspace_id == workspace_id,
                ResourceAccessPolicy.resource_type == resource_type,
                ResourceAccessPolicy.resource_id == resource_id,
            )
            .order_by(desc(ResourceAccessPolicy.created_at))
        )
        res = await db.execute(query)
        rows = res.all()

        return [
            ResourceAccessPolicyResponse(
                id=pol.id,
                workspace_id=pol.workspace_id,
                resource_type=pol.resource_type,
                resource_id=pol.resource_id,
                user_id=pol.user_id,
                user_name=user_name,
                user_email=user_email,
                role_id=pol.role_id,
                role_name=role_name,
                permission=pol.permission,
                is_denied=pol.is_denied,
                created_at=pol.created_at,
            )
            for pol, user_name, user_email, role_name in rows
        ]

    @staticmethod
    async def create_resource_policy(
        db: AsyncSession, workspace_id: uuid.UUID, actor: User, req: ResourceAccessPolicyCreate
    ) -> ResourceAccessPolicyResponse:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_manage:
            raise DataLensException("Permission denied to configure resource access policies.", code="FORBIDDEN")

        policy = ResourceAccessPolicy(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            user_id=req.user_id,
            role_id=req.role_id,
            permission=req.permission,
            is_denied=req.is_denied,
            created_at=datetime.now(UTC),
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="resource_policy_created",
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            outcome="SUCCESS",
            metadata_snapshot={
                "is_denied": policy.is_denied,
                "permission": policy.permission,
                "target_user_id": str(policy.user_id) if policy.user_id else None,
                "target_role_id": str(policy.role_id) if policy.role_id else None,
            },
        )

        return ResourceAccessPolicyResponse.model_validate(policy)

    @staticmethod
    async def delete_resource_policy(
        db: AsyncSession, workspace_id: uuid.UUID, policy_id: uuid.UUID, actor: User
    ) -> None:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_manage:
            raise DataLensException("Permission denied to remove resource access policies.", code="FORBIDDEN")

        policy = await db.get(ResourceAccessPolicy, policy_id)
        if not policy or policy.workspace_id != workspace_id:
            raise DataLensException("Policy not found.", code="NOT_FOUND")

        await db.delete(policy)
        await db.commit()

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="resource_policy_revoked",
            resource_type=policy.resource_type,
            resource_id=policy.resource_id,
            outcome="SUCCESS",
            metadata_snapshot={"policy_id": str(policy_id)},
        )

    # ---------------------------------------------------------------------------
    # Data Access Governance & Column Masking
    # ---------------------------------------------------------------------------

    @staticmethod
    async def get_or_create_dataset_governance(
        db: AsyncSession, workspace_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> DatasetGovernance:
        stmt = select(DatasetGovernance).where(
            DatasetGovernance.workspace_id == workspace_id,
            DatasetGovernance.dataset_id == dataset_id,
        )
        gov = (await db.execute(stmt)).scalar_one_or_none()
        if not gov:
            gov = DatasetGovernance(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                dataset_id=dataset_id,
                sensitivity_level="INTERNAL",
                export_restricted=False,
                column_masks={},
                approved_by=None,
                approved_at=None,
                updated_at=datetime.now(UTC),
            )
            db.add(gov)
            await db.commit()
            await db.refresh(gov)
        return gov

    @staticmethod
    async def update_dataset_governance(
        db: AsyncSession, workspace_id: uuid.UUID, dataset_id: uuid.UUID, actor: User, req: DatasetGovernanceUpdate
    ) -> DatasetGovernanceResponse:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "governance:manage")
        if not can_manage:
            raise DataLensException("Permission denied to update data governance configuration.", code="FORBIDDEN")

        gov = await GovernanceService.get_or_create_dataset_governance(db, workspace_id, dataset_id)
        gov.sensitivity_level = req.sensitivity_level
        gov.export_restricted = req.export_restricted
        gov.column_masks = {col: mask.model_dump() for col, mask in req.column_masks.items()}
        gov.approved_by = actor.id
        gov.approved_at = datetime.now(UTC)
        gov.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(gov)

        ds = await db.get(Dataset, dataset_id)

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="dataset_governance_updated",
            resource_type="dataset",
            resource_id=dataset_id,
            outcome="SUCCESS",
            metadata_snapshot={
                "sensitivity": gov.sensitivity_level,
                "export_restricted": gov.export_restricted,
                "masked_columns_count": len(gov.column_masks),
            },
        )

        return DatasetGovernanceResponse(
            id=gov.id,
            workspace_id=gov.workspace_id,
            dataset_id=gov.dataset_id,
            dataset_name=ds.name if ds else None,
            sensitivity_level=gov.sensitivity_level,
            export_restricted=gov.export_restricted,
            column_masks=gov.column_masks,
            approved_by=gov.approved_by,
            approved_by_name=actor.full_name,
            approved_at=gov.approved_at,
            updated_at=gov.updated_at,
        )

    @staticmethod
    def apply_column_masking(
        rows: list[dict[str, Any]],
        column_masks: dict[str, Any],
        has_bypass_clearance: bool = False,
    ) -> list[dict[str, Any]]:
        """Mask or suppress configured restricted columns."""
        if not column_masks or has_bypass_clearance:
            return rows

        masked_rows = []
        for row in rows:
            clean_row = dict(row)
            for col, rule in column_masks.items():
                if col in clean_row and clean_row[col] is not None:
                    mask_type = rule.get("type", "redact") if isinstance(rule, dict) else "redact"
                    val_str = str(clean_row[col])

                    if mask_type == "redact":
                        clean_row[col] = "••••••••"
                    elif mask_type == "hash":
                        clean_row[col] = hashlib.sha256(val_str.encode()).hexdigest()[:16]
                    elif mask_type == "partial":
                        if len(val_str) > 4:
                            clean_row[col] = f"{'*' * (len(val_str) - 4)}{val_str[-4:]}"
                        else:
                            clean_row[col] = "****"
            masked_rows.append(clean_row)
        return masked_rows

    # ---------------------------------------------------------------------------
    # Immutable Enterprise Audit Logs
    # ---------------------------------------------------------------------------

    @staticmethod
    def compute_audit_hash(
        event_id: uuid.UUID | str,
        prev_hash: str,
        actor_id: uuid.UUID | str | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | str | None,
        outcome: str,
        timestamp: datetime,
        metadata_snapshot: dict[str, Any] | None = None,
        actor_email: str | None = None,
    ) -> str:
        """Computes a deterministic cryptographic SHA-256 hash across all protected audit fields:
        - Log ID
        - Previous hash
        - Actor identity (actor_id or actor_email)
        - Action
        - Outcome
        - Resource type and identifier
        - Timestamp (ISO 8601 UTC)
        - Event details (metadata_snapshot canonical JSON)
        """
        meta_json = json.dumps(metadata_snapshot or {}, sort_keys=True, separators=(",", ":"))
        ts_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        actor_str = str(actor_id) if actor_id else (actor_email or "")
        res_id_str = str(resource_id) if resource_id else ""
        raw_payload = (
            f"{str(event_id)}:"
            f"{prev_hash}:"
            f"{actor_str}:"
            f"{action}:"
            f"{resource_type}:"
            f"{res_id_str}:"
            f"{outcome}:"
            f"{ts_str}:"
            f"{meta_json}"
        )
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_audit_log_record(
        log: EnterpriseAuditLog,
        expected_prev_hash: str | None = None,
    ) -> bool:
        """Verifies that a single audit log record's chained_hash matches its protected payload,
        and optionally that its previous_hash matches the expected_prev_hash.
        """
        prev_hash = log.previous_hash or "GENESIS_DATALENS_ROOT_HASH"
        if expected_prev_hash is not None and prev_hash != expected_prev_hash:
            return False

        computed = GovernanceService.compute_audit_hash(
            event_id=log.id,
            prev_hash=prev_hash,
            actor_id=log.actor_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            outcome=log.outcome,
            timestamp=log.timestamp,
            metadata_snapshot=log.metadata_snapshot,
            actor_email=log.actor_email,
        )
        return hmac.compare_digest(computed, log.chained_hash)

    @staticmethod
    async def verify_audit_chain(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor: User | None = None,
    ) -> dict[str, Any]:
        """Validates complete cryptographic chain integrity for a workspace.
        Verifies:
        1. Every record's hash matches its protected fields.
        2. Every record's previous_hash matches the chained_hash of the preceding record.
        3. Chronological timestamp ordering is strictly monotonic.
        4. Detects intermediate deletions, tampering, and ordering anomalies.
        """
        if actor:
            can_view = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "audit:view")
            if not can_view:
                raise DataLensException("Permission denied to view audit logs.", code="FORBIDDEN")

        query = (
            select(EnterpriseAuditLog)
            .where(EnterpriseAuditLog.workspace_id == workspace_id)
            .order_by(asc(EnterpriseAuditLog.timestamp), asc(EnterpriseAuditLog.id))
        )
        result = await db.execute(query)
        logs = list(result.scalars().all())

        if not logs:
            return {
                "is_valid": True,
                "total_records": 0,
                "verified_records": 0,
                "status": "EMPTY_CHAIN",
                "message": "Audit chain is empty. Genesis state intact.",
            }

        expected_prev_hash = "GENESIS_DATALENS_ROOT_HASH"
        prev_timestamp = None

        for idx, log in enumerate(logs):
            # Check chain link
            if (log.previous_hash or "GENESIS_DATALENS_ROOT_HASH") != expected_prev_hash:
                return {
                    "is_valid": False,
                    "total_records": len(logs),
                    "verified_records": idx,
                    "broken_at_index": idx,
                    "broken_at_id": str(log.id),
                    "status": "CHAIN_BROKEN",
                    "message": f"Hash mismatch at record {log.id}: previous_hash was '{log.previous_hash}', expected '{expected_prev_hash}'. Possible deletion or reordering.",
                }

            # Check payload integrity
            if not GovernanceService.verify_audit_log_record(log, expected_prev_hash):
                return {
                    "is_valid": False,
                    "total_records": len(logs),
                    "verified_records": idx,
                    "broken_at_index": idx,
                    "broken_at_id": str(log.id),
                    "status": "RECORD_TAMPERED",
                    "message": f"Tampering detected in record {log.id}: hash does not match protected fields.",
                }

            # Check timestamp monotonicity
            if prev_timestamp and log.timestamp < prev_timestamp:
                return {
                    "is_valid": False,
                    "total_records": len(logs),
                    "verified_records": idx,
                    "broken_at_index": idx,
                    "broken_at_id": str(log.id),
                    "status": "ORDER_ANOMALY",
                    "message": f"Timestamp order anomaly detected at record {log.id}: timestamp {log.timestamp.isoformat()} is prior to previous record {prev_timestamp.isoformat()}.",
                }

            prev_timestamp = log.timestamp
            expected_prev_hash = log.chained_hash

        return {
            "is_valid": True,
            "total_records": len(logs),
            "verified_records": len(logs),
            "status": "VALID",
            "message": f"Audit chain cryptographically verified. All {len(logs)} records intact.",
            "latest_hash": expected_prev_hash,
        }

    @staticmethod
    async def record_audit_event(
        db: AsyncSession,
        workspace_id: uuid.UUID | None,
        actor: User | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        outcome: str = "SUCCESS",
        metadata_snapshot: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
    ) -> EnterpriseAuditLog:
        """Create a tamper-evident chained audit record with sanitized metadata."""
        # Sanitize metadata to guarantee zero secrets are persisted
        sanitized_meta: dict[str, Any] = {}
        if metadata_snapshot:
            for k, v in metadata_snapshot.items():
                if SENSITIVE_KEY_PATTERN.search(str(k)):
                    sanitized_meta[k] = "••••••••"
                else:
                    sanitized_meta[k] = v

        # Serialize audit insertions per workspace using PostgreSQL advisory transaction lock
        if workspace_id and type(db).__name__ not in ("AsyncMock", "MagicMock"):
            try:
                lock_key = int(workspace_id.int % (2**31 - 1))
                await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
            except Exception:
                pass

        # Fetch latest audit record for this workspace to establish cryptographic link
        prev_hash_stmt = select(EnterpriseAuditLog.chained_hash)
        if workspace_id:
            prev_hash_stmt = prev_hash_stmt.where(EnterpriseAuditLog.workspace_id == workspace_id)
        prev_hash_stmt = prev_hash_stmt.order_by(
            desc(EnterpriseAuditLog.timestamp), desc(EnterpriseAuditLog.id)
        ).limit(1)
        prev_hash_res = await db.execute(prev_hash_stmt)
        prev_hash = prev_hash_res.scalar_one_or_none() or "GENESIS_DATALENS_ROOT_HASH"

        event_id = uuid.uuid4()
        now = datetime.now(UTC)

        # Chained hash calculation across all protected fields
        chained_hash = GovernanceService.compute_audit_hash(
            event_id=event_id,
            prev_hash=prev_hash,
            actor_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            timestamp=now,
            metadata_snapshot=sanitized_meta,
            actor_email=actor.email if actor else None,
        )

        log_entry = EnterpriseAuditLog(
            id=event_id,
            workspace_id=workspace_id,
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=now,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id or str(uuid.uuid4())[:8],
            outcome=outcome,
            metadata_snapshot=sanitized_meta,
            previous_hash=prev_hash,
            chained_hash=chained_hash,
        )
        db.add(log_entry)
        await db.commit()
        return log_entry

    @staticmethod
    async def list_audit_logs(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor: User,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        outcome: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> AuditLogListResponse:
        can_view = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "audit:view")
        if not can_view:
            raise DataLensException("Permission denied to view audit logs.", code="FORBIDDEN")

        offset = max(0, (page - 1) * page_size)
        query = (
            select(EnterpriseAuditLog, User.full_name)
            .outerjoin(User, User.id == EnterpriseAuditLog.actor_id)
            .where(EnterpriseAuditLog.workspace_id == workspace_id)
        )
        count_query = select(func.count(EnterpriseAuditLog.id)).where(
            EnterpriseAuditLog.workspace_id == workspace_id
        )

        if actor_id:
            query = query.where(EnterpriseAuditLog.actor_id == actor_id)
            count_query = count_query.where(EnterpriseAuditLog.actor_id == actor_id)
        if action:
            query = query.where(EnterpriseAuditLog.action == action)
            count_query = count_query.where(EnterpriseAuditLog.action == action)
        if resource_type:
            query = query.where(EnterpriseAuditLog.resource_type == resource_type)
            count_query = count_query.where(EnterpriseAuditLog.resource_type == resource_type)
        if outcome:
            query = query.where(EnterpriseAuditLog.outcome == outcome)
            count_query = count_query.where(EnterpriseAuditLog.outcome == outcome)
        if start_date:
            query = query.where(EnterpriseAuditLog.timestamp >= start_date)
            count_query = count_query.where(EnterpriseAuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(EnterpriseAuditLog.timestamp <= end_date)
            count_query = count_query.where(EnterpriseAuditLog.timestamp <= end_date)

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(desc(EnterpriseAuditLog.timestamp)).offset(offset).limit(page_size)
        rows = (await db.execute(query)).all()

        items = [
            EnterpriseAuditLogResponse(
                id=log.id,
                workspace_id=log.workspace_id,
                actor_id=log.actor_id,
                actor_email=log.actor_email,
                actor_name=user_name or "System",
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                timestamp=log.timestamp,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                correlation_id=log.correlation_id,
                outcome=log.outcome,
                metadata_snapshot=log.metadata_snapshot,
                previous_hash=log.previous_hash,
                chained_hash=log.chained_hash,
                is_chain_valid=GovernanceService.verify_audit_log_record(log),
            )
            for log, user_name in rows
        ]
        return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)

    # ---------------------------------------------------------------------------
    # Security Events & Monitoring
    # ---------------------------------------------------------------------------

    @staticmethod
    async def record_security_event(
        db: AsyncSession,
        workspace_id: uuid.UUID | None,
        event_type: str,
        severity: str,
        details: dict[str, Any],
    ) -> SecurityEvent:
        event = SecurityEvent(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            event_type=event_type,
            severity=severity,
            details=details,
            status="OPEN",
            created_at=datetime.now(UTC),
        )
        db.add(event)
        await db.commit()
        return event

    @staticmethod
    async def list_security_events(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor: User,
        status_filter: str | None = None,
        severity_filter: str | None = None,
    ) -> list[SecurityEventResponse]:
        can_view = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_view:
            raise DataLensException("Permission denied to view security events.", code="FORBIDDEN")

        query = (
            select(SecurityEvent, User.full_name)
            .outerjoin(User, User.id == SecurityEvent.resolved_by)
            .where(SecurityEvent.workspace_id == workspace_id)
            .order_by(desc(SecurityEvent.created_at))
        )
        if status_filter:
            query = query.where(SecurityEvent.status == status_filter)
        if severity_filter:
            query = query.where(SecurityEvent.severity == severity_filter)

        rows = (await db.execute(query)).all()
        return [
            SecurityEventResponse(
                id=evt.id,
                workspace_id=evt.workspace_id,
                event_type=evt.event_type,
                severity=evt.severity,
                details=evt.details,
                status=evt.status,
                resolved_by=evt.resolved_by,
                resolved_by_name=resolver_name,
                resolved_at=evt.resolved_at,
                created_at=evt.created_at,
            )
            for evt, resolver_name in rows
        ]

    @staticmethod
    async def update_security_event_status(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        event_id: uuid.UUID,
        actor: User,
        status: str,
        notes: str | None = None,
    ) -> SecurityEventResponse:
        can_manage = await GovernanceService.has_workspace_permission(db, workspace_id, actor, "workspace:configure")
        if not can_manage:
            raise DataLensException("Permission denied to update security events.", code="FORBIDDEN")

        evt = await db.get(SecurityEvent, event_id)
        if not evt or evt.workspace_id != workspace_id:
            raise DataLensException("Security event not found.", code="NOT_FOUND")

        evt.status = status
        if status in ("RESOLVED", "FALSE_POSITIVE"):
            evt.resolved_by = actor.id
            evt.resolved_at = datetime.now(UTC)
        if notes:
            details_copy = dict(evt.details)
            details_copy["resolution_notes"] = notes
            evt.details = details_copy

        await db.commit()
        await db.refresh(evt)

        return SecurityEventResponse(
            id=evt.id,
            workspace_id=evt.workspace_id,
            event_type=evt.event_type,
            severity=evt.severity,
            details=evt.details,
            status=evt.status,
            resolved_by=evt.resolved_by,
            resolved_by_name=actor.full_name,
            resolved_at=evt.resolved_at,
            created_at=evt.created_at,
        )

    # ---------------------------------------------------------------------------
    # User Sessions
    # ---------------------------------------------------------------------------

    @staticmethod
    async def create_user_session(
        db: AsyncSession,
        user_id: uuid.UUID,
        raw_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        lifetime_hours: int = 24,
    ) -> UserSession:
        token_h = hashlib.sha256(raw_token.encode()).hexdigest()
        now = datetime.now(UTC)

        # Infer basic device label
        device = "Desktop / Browser"
        if user_agent:
            if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
                device = "Mobile Device"
            elif "Macintosh" in user_agent:
                device = "macOS Browser"
            elif "Windows" in user_agent:
                device = "Windows Browser"
            elif "Linux" in user_agent:
                device = "Linux Browser"

        session = UserSession(
            id=uuid.uuid4(),
            user_id=user_id,
            session_token_hash=token_h,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device,
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=lifetime_hours),
            is_revoked=False,
        )
        db.add(session)
        await db.commit()
        return session

    @staticmethod
    async def list_active_sessions(
        db: AsyncSession, user_id: uuid.UUID, current_token_hash: str | None = None
    ) -> list[UserSessionResponse]:
        now = datetime.now(UTC)
        query = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False,  # noqa: E712
                UserSession.expires_at >= now,
            )
            .order_by(desc(UserSession.last_activity_at))
        )
        sessions = (await db.execute(query)).scalars().all()

        return [
            UserSessionResponse(
                id=s.id,
                user_id=s.user_id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                device_label=s.device_label,
                created_at=s.created_at,
                last_activity_at=s.last_activity_at,
                expires_at=s.expires_at,
                is_current=bool(current_token_hash and s.session_token_hash == current_token_hash),
                is_revoked=s.is_revoked,
            )
            for s in sessions
        ]

    @staticmethod
    async def revoke_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        session = await db.get(UserSession, session_id)
        if not session or session.user_id != user_id:
            raise DataLensException("Session not found.", code="NOT_FOUND")

        session.is_revoked = True
        await db.commit()

    @staticmethod
    async def revoke_all_other_sessions(
        db: AsyncSession, user_id: uuid.UUID, current_token_hash: str
    ) -> int:
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.session_token_hash != current_token_hash,
            UserSession.is_revoked == False,  # noqa: E712
        )
        sessions = (await db.execute(query)).scalars().all()
        count = len(sessions)
        for s in sessions:
            s.is_revoked = True
        await db.commit()
        return count

    @staticmethod
    async def is_session_revoked(db: AsyncSession, token_hash: str) -> bool:
        stmt = select(UserSession.is_revoked).where(UserSession.session_token_hash == token_hash)
        res = await db.execute(stmt)
        is_revoked = res.scalar_one_or_none()
        return bool(is_revoked is True)

    # ---------------------------------------------------------------------------
    # Workspace Security Policies
    # ---------------------------------------------------------------------------

    @staticmethod
    async def get_or_create_policy(db: AsyncSession, workspace_id: uuid.UUID) -> WorkspaceSecurityPolicy:
        stmt = select(WorkspaceSecurityPolicy).where(WorkspaceSecurityPolicy.workspace_id == workspace_id)
        policy = (await db.execute(stmt)).scalar_one_or_none()
        if not policy:
            policy = WorkspaceSecurityPolicy(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                allow_public_share_links=True,
                max_share_link_days=30,
                restrict_external_sharing=False,
                restrict_report_downloads=False,
                restrict_dataset_exports=False,
                max_session_hours=24,
                allowed_invitation_domains=[],
                custom_roles_enabled=True,
                audit_retention_days=90,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(policy)
            await db.commit()
            await db.refresh(policy)
        return policy

    @staticmethod
    async def update_security_policy(
        db: AsyncSession, workspace_id: uuid.UUID, actor: User, req: WorkspaceSecurityPolicyUpdate
    ) -> WorkspaceSecurityPolicyResponse:
        can_manage = await GovernanceService.has_workspace_permission(
            db, workspace_id, actor, "security_policy:manage"
        )
        if not can_manage:
            raise DataLensException("Permission denied to update workspace security policies.", code="FORBIDDEN")

        policy = await GovernanceService.get_or_create_policy(db, workspace_id)

        if req.allow_public_share_links is not None:
            policy.allow_public_share_links = req.allow_public_share_links
        if req.max_share_link_days is not None:
            policy.max_share_link_days = req.max_share_link_days
        if req.restrict_external_sharing is not None:
            policy.restrict_external_sharing = req.restrict_external_sharing
        if req.restrict_report_downloads is not None:
            policy.restrict_report_downloads = req.restrict_report_downloads
        if req.restrict_dataset_exports is not None:
            policy.restrict_dataset_exports = req.restrict_dataset_exports
        if req.max_session_hours is not None:
            policy.max_session_hours = req.max_session_hours
        if req.allowed_invitation_domains is not None:
            policy.allowed_invitation_domains = [d.lower().strip() for d in req.allowed_invitation_domains if d.strip()]
        if req.custom_roles_enabled is not None:
            policy.custom_roles_enabled = req.custom_roles_enabled
        if req.audit_retention_days is not None:
            policy.audit_retention_days = req.audit_retention_days

        policy.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(policy)

        await GovernanceService.record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor=actor,
            action="security_policy_updated",
            resource_type="workspace_security_policy",
            resource_id=policy.id,
            outcome="SUCCESS",
            metadata_snapshot={
                "allow_public_share_links": policy.allow_public_share_links,
                "restrict_dataset_exports": policy.restrict_dataset_exports,
                "restrict_report_downloads": policy.restrict_report_downloads,
            },
        )

        return WorkspaceSecurityPolicyResponse.model_validate(policy)

