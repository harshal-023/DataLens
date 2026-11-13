import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.permissions import (
    WorkspaceRole,
    can_invite_role,
    can_manage_member,
    is_role_at_least,
    normalize_role,
)
from app.core.security import generate_secure_token, hash_token
from app.models.invitation import WorkspaceInvitation
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.workspace import (
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.services.email_adapter import dev_email_adapter


class WorkspaceService:
    @staticmethod
    async def list_user_workspaces(user_id: uuid.UUID, db: AsyncSession) -> list[WorkspaceResponse]:
        query = (
            select(Workspace, WorkspaceMembership.role)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(WorkspaceMembership.user_id == user_id)
            .order_by(Workspace.created_at.asc())
        )
        result = await db.execute(query)
        rows = result.all()

        return [
            WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                owner_id=ws.owner_id,
                current_user_role=role,
                created_at=ws.created_at,
            )
            for ws, role in rows
        ]

    @staticmethod
    async def create_workspace(
        user: User, req: WorkspaceCreateRequest, db: AsyncSession
    ) -> WorkspaceResponse:
        ws = Workspace(
            name=req.name.strip(),
            owner_id=user.id,
        )
        db.add(ws)
        await db.flush()

        membership = WorkspaceMembership(
            workspace_id=ws.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER.value,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(ws)

        return WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            current_user_role=WorkspaceRole.OWNER.value,
            created_at=ws.created_at,
        )

    @staticmethod
    async def get_workspace(
        workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> tuple[Workspace, str]:
        query = (
            select(Workspace, WorkspaceMembership.role)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(Workspace.id == workspace_id, WorkspaceMembership.user_id == user_id)
        )
        result = await db.execute(query)
        row = result.first()
        if row is None:
            raise DataLensException("Workspace not found or access denied.", code="NOT_FOUND")
        ws, role = row
        return ws, role

    @staticmethod
    async def update_workspace(
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        req: WorkspaceUpdateRequest,
        db: AsyncSession,
    ) -> WorkspaceResponse:
        ws, role = await WorkspaceService.get_workspace(workspace_id, user_id, db)
        if not is_role_at_least(role, WorkspaceRole.ADMIN.value):
            raise DataLensException("Only workspace Owners and Admins can update workspace details.", code="FORBIDDEN")

        ws.name = req.name.strip()
        await db.commit()
        await db.refresh(ws)

        return WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            current_user_role=role,
            created_at=ws.created_at,
        )

    @staticmethod
    async def delete_workspace(
        workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> None:
        ws, role = await WorkspaceService.get_workspace(workspace_id, user_id, db)
        if normalize_role(role) != WorkspaceRole.OWNER.value:
            raise DataLensException("Only the workspace Owner can delete this workspace.", code="FORBIDDEN")

        # Prevent accidental deletion of a user's only workspace
        count_query = (
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == user_id)
        )
        total_workspaces = (await db.execute(count_query)).scalar_one()
        if total_workspaces <= 1:
            raise DataLensException(
                message="Cannot delete your only workspace. You must belong to at least one workspace.",
                code="BAD_REQUEST",
            )

        await db.delete(ws)
        await db.commit()

    @staticmethod
    async def list_members(
        workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> list[WorkspaceMemberResponse]:
        # Validate caller membership
        await WorkspaceService.get_workspace(workspace_id, user_id, db)

        query = (
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.created_at.asc())
        )
        rows = (await db.execute(query)).all()

        return [
            WorkspaceMemberResponse(
                user_id=member.user_id,
                full_name=user.full_name,
                email=user.email,
                role=member.role,
                joined_at=member.created_at,
            )
            for member, user in rows
        ]

    @staticmethod
    async def invite_member(
        workspace_id: uuid.UUID,
        inviter: User,
        req: InviteMemberRequest,
        db: AsyncSession,
    ) -> tuple[WorkspaceInvitation, str]:
        ws, role = await WorkspaceService.get_workspace(workspace_id, inviter.id, db)

        # Check if inviter has permission to invite this role
        target_role = normalize_role(req.role)
        if not can_invite_role(role, target_role):
            raise DataLensException(
                message=f"Your role ({role}) does not have permission to invite members with the '{target_role}' role.",
                code="FORBIDDEN",
            )

        invite_email = req.email.strip().lower()

        # Check if user with this email is already a member
        member_query = (
            select(WorkspaceMembership)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                User.email == invite_email,
            )
        )
        if (await db.execute(member_query)).scalar_one_or_none() is not None:
            raise DataLensException(
                message="A user with this email is already a member of this workspace.",
                code="DUPLICATE_MEMBERSHIP",
            )

        # Generate secure invitation token
        raw_token = generate_secure_token()
        token_hash = hash_token(raw_token)
        expires = datetime.now(UTC) + timedelta(days=settings.INVITATION_TOKEN_EXPIRE_DAYS)

        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            inviter_id=inviter.id,
            email=invite_email,
            role=target_role,
            token_hash=token_hash,
            expires_at=expires,
            is_accepted=False,
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        dev_email_adapter.send_workspace_invitation(
            to_email=invite_email,
            workspace_name=ws.name,
            invitation_token=raw_token,
            inviter_name=inviter.full_name,
        )

        return invitation, raw_token

    @staticmethod
    async def accept_invitation(
        token: str, user: User, db: AsyncSession
    ) -> WorkspaceResponse:
        token_hash = hash_token(token)
        query = select(WorkspaceInvitation).where(
            WorkspaceInvitation.token_hash == token_hash,
            WorkspaceInvitation.is_accepted == False,  # noqa: E712
        )
        invitation = (await db.execute(query)).scalar_one_or_none()

        if invitation is None:
            raise DataLensException("Invalid or already accepted invitation link.", code="INVALID_INVITATION")

        if invitation.expires_at < datetime.now(UTC):
            raise DataLensException("This invitation link has expired.", code="EXPIRED_INVITATION")

        # Check if already a member
        existing = await db.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == invitation.workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            invitation.is_accepted = True
            await db.commit()
            raise DataLensException("You are already a member of this workspace.", code="DUPLICATE_MEMBERSHIP")

        # Add membership and mark accepted
        membership = WorkspaceMembership(
            workspace_id=invitation.workspace_id,
            user_id=user.id,
            role=invitation.role,
        )
        db.add(membership)
        invitation.is_accepted = True
        await db.commit()

        ws = await db.get(Workspace, invitation.workspace_id)
        return WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            current_user_role=invitation.role,
            created_at=ws.created_at,
        )

    @staticmethod
    async def update_member_role(
        workspace_id: uuid.UUID,
        actor: User,
        target_user_id: uuid.UUID,
        req: UpdateMemberRoleRequest,
        db: AsyncSession,
    ) -> WorkspaceMemberResponse:
        _, actor_role = await WorkspaceService.get_workspace(workspace_id, actor.id, db)

        # Get target member
        query = (
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == target_user_id,
            )
        )
        row = (await db.execute(query)).first()
        if row is None:
            raise DataLensException("Target member not found in this workspace.", code="NOT_FOUND")

        target_membership, target_user = row
        new_role = normalize_role(req.role)

        # Check permissions to manage this member
        if not can_manage_member(actor_role, target_membership.role):
            raise DataLensException("You do not have permission to modify this member's role.", code="FORBIDDEN")

        # Prevent demoting the last Owner
        if target_membership.role == WorkspaceRole.OWNER.value and new_role != WorkspaceRole.OWNER.value:
            owner_count_query = select(func.count()).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role == WorkspaceRole.OWNER.value,
            )
            total_owners = (await db.execute(owner_count_query)).scalar_one()
            if total_owners <= 1:
                raise DataLensException(
                    message="Cannot demote the last Owner of the workspace. Transfer ownership or assign another Owner first.",
                    code="BAD_REQUEST",
                )

        target_membership.role = new_role
        await db.commit()
        await db.refresh(target_membership)

        return WorkspaceMemberResponse(
            user_id=target_user.id,
            full_name=target_user.full_name,
            email=target_user.email,
            role=target_membership.role,
            joined_at=target_membership.created_at,
        )

    @staticmethod
    async def remove_member(
        workspace_id: uuid.UUID,
        actor: User,
        target_user_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        _, actor_role = await WorkspaceService.get_workspace(workspace_id, actor.id, db)

        query = (
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == target_user_id,
            )
        )
        membership = (await db.execute(query)).scalar_one_or_none()
        if membership is None:
            raise DataLensException("Member not found in this workspace.", code="NOT_FOUND")

        # Self-removal (leaving workspace) vs removing another member
        is_self_removal = actor.id == target_user_id
        if not is_self_removal and not can_manage_member(actor_role, membership.role):
            raise DataLensException("You do not have permission to remove this member.", code="FORBIDDEN")

        # Prevent removing the last Owner
        if membership.role == WorkspaceRole.OWNER.value:
            owner_count_query = select(func.count()).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role == WorkspaceRole.OWNER.value,
            )
            total_owners = (await db.execute(owner_count_query)).scalar_one()
            if total_owners <= 1:
                raise DataLensException(
                    message="Cannot remove the last Owner of the workspace.",
                    code="BAD_REQUEST",
                )

        await db.delete(membership)
        await db.commit()
