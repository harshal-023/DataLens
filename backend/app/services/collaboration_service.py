"""Comprehensive Collaboration, Sharing, Discussions, and Notifications Service."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import html
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.permissions import is_role_at_least
from app.core.security import hash_token
from app.models.collaboration import (
    Comment,
    Notification,
    NotificationPreference,
    ResourceShare,
    ShareAccessToken,
    WorkspaceActivity,
)
from app.models.dashboard import Dashboard, DashboardFilter, DashboardWidget
from app.models.invitation import WorkspaceInvitation
from app.models.report import Report
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.collaboration import (
    ActivityListResponse,
    ActivityResponse,
    CommentResponse,
    InvitationDetailResponse,
    InvitationResponse,
    MemberShareResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    PublicDashboardResponse,
    ShareLinkResponse,
)
from app.services.email_adapter import dev_email_adapter


class CollaborationService:
    """Manages workspace team collaboration, resource sharing, threaded discussions, and notifications."""

    _notification_listeners: dict[uuid.UUID, set[asyncio.Queue]] = {}

    @classmethod
    def subscribe_notifications(cls, user_id: uuid.UUID) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        cls._notification_listeners.setdefault(user_id, set()).add(q)
        return q

    @classmethod
    def unsubscribe_notifications(cls, user_id: uuid.UUID, q: asyncio.Queue) -> None:
        if user_id in cls._notification_listeners:
            cls._notification_listeners[user_id].discard(q)
            if not cls._notification_listeners[user_id]:
                del cls._notification_listeners[user_id]

    # ---------------------------------------------------------------------------
    # Activity Logging
    # ---------------------------------------------------------------------------

    @staticmethod
    async def log_activity(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        event_type: str,
        resource_type: str,
        resource_id: uuid.UUID | None,
        summary: str,
        metadata_snapshot: dict[str, Any] | None = None,
    ) -> WorkspaceActivity:
        """Record an immutable workspace audit activity."""
        # Sanitize metadata to guarantee zero secret leakage
        clean_meta = {}
        if metadata_snapshot:
            for k, v in metadata_snapshot.items():
                if any(sec in k.lower() for sec in ["pass", "token", "secret", "key"]):
                    clean_meta[k] = "••••••••"
                else:
                    clean_meta[k] = v

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            summary=summary[:500],
            metadata_snapshot=clean_meta,
            created_at=datetime.now(UTC),
        )
        db.add(activity)
        await db.commit()
        return activity

    @staticmethod
    async def list_workspace_activity(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        event_type: str | None = None,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityResponse]:
        """Fetch timeline of workspace events with pagination and filters."""
        query = (
            select(WorkspaceActivity, User.full_name)
            .outerjoin(User, User.id == WorkspaceActivity.actor_id)
            .where(WorkspaceActivity.workspace_id == workspace_id)
            .order_by(desc(WorkspaceActivity.created_at))
            .offset(offset)
            .limit(limit)
        )
        if event_type:
            query = query.where(WorkspaceActivity.event_type == event_type)
        if resource_type:
            query = query.where(WorkspaceActivity.resource_type == resource_type)

        res = await db.execute(query)
        rows = res.all()

        return [
            ActivityResponse(
                id=act.id,
                workspace_id=act.workspace_id,
                actor_id=act.actor_id,
                actor_name=actor_name or "System",
                event_type=act.event_type,
                resource_type=act.resource_type,
                resource_id=act.resource_id,
                summary=act.summary,
                metadata_snapshot=act.metadata_snapshot,
                created_at=act.created_at,
            )
            for act, actor_name in rows
        ]

    @staticmethod
    async def get_workspace_activity(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ActivityListResponse:
        offset = max(0, (page - 1) * page_size)
        query = (
            select(WorkspaceActivity, User.full_name)
            .outerjoin(User, User.id == WorkspaceActivity.actor_id)
            .where(WorkspaceActivity.workspace_id == workspace_id)
        )
        if actor_id:
            query = query.where(WorkspaceActivity.actor_id == actor_id)
        if resource_type:
            query = query.where(WorkspaceActivity.resource_type == resource_type)
        if event_type:
            query = query.where(WorkspaceActivity.event_type == event_type)

        # Count total
        count_query = select(func.count(WorkspaceActivity.id)).where(WorkspaceActivity.workspace_id == workspace_id)
        if actor_id:
            count_query = count_query.where(WorkspaceActivity.actor_id == actor_id)
        if resource_type:
            count_query = count_query.where(WorkspaceActivity.resource_type == resource_type)
        if event_type:
            count_query = count_query.where(WorkspaceActivity.event_type == event_type)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        # Execute paginated query
        query = query.order_by(desc(WorkspaceActivity.created_at)).offset(offset).limit(page_size)
        res = await db.execute(query)
        rows = res.all()

        items = [
            ActivityResponse(
                id=act.id,
                workspace_id=act.workspace_id,
                actor_id=act.actor_id,
                actor_name=actor_name or "System",
                event_type=act.event_type,
                resource_type=act.resource_type,
                resource_id=act.resource_id,
                summary=act.summary,
                metadata_snapshot=act.metadata_snapshot,
                created_at=act.created_at,
            )
            for act, actor_name in rows
        ]
        return ActivityListResponse(items=items, total=total)

    # ---------------------------------------------------------------------------
    # Notifications & Preferences
    # ---------------------------------------------------------------------------

    @staticmethod
    async def get_or_create_preferences(
        db: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> NotificationPreference:
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        pref = res.scalar_one_or_none()
        if not pref:
            pref = NotificationPreference(
                id=uuid.uuid4(),
                user_id=user_id,
                workspace_id=workspace_id,
                email_notifications=True,
                in_app_notifications=True,
                mention_notifications=True,
                share_notifications=True,
            )
            db.add(pref)
            await db.commit()
            await db.refresh(pref)
        return pref

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: NotificationPreferenceUpdate,
    ) -> NotificationPreferenceResponse:
        pref = await CollaborationService.get_or_create_preferences(db, user_id, workspace_id)
        if req.email_notifications is not None:
            pref.email_notifications = req.email_notifications
        if req.in_app_notifications is not None:
            pref.in_app_notifications = req.in_app_notifications
        if req.mention_notifications is not None:
            pref.mention_notifications = req.mention_notifications
        if req.share_notifications is not None:
            pref.share_notifications = req.share_notifications

        pref.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(pref)
        return NotificationPreferenceResponse.model_validate(pref)

    @classmethod
    async def dispatch_notification(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        recipient_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        event_type: str,
        title: str,
        message: str,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        data: dict[str, Any] | None = None,
        action_url: str | None = None,
    ) -> Notification | None:
        """Create in-app notification and optionally trigger email delivery based on user preferences."""
        # Don't notify self
        if actor_id and recipient_id == actor_id:
            return None

        pref = await CollaborationService.get_or_create_preferences(db, recipient_id, workspace_id)

        notification = None
        if pref.in_app_notifications:
            notification = Notification(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                recipient_id=recipient_id,
                actor_id=actor_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                title=title,
                message=message,
                data=data or {},
                is_read=False,
                created_at=datetime.now(UTC),
            )
            db.add(notification)
            await db.commit()

            # Broadcast to real-time SSE listeners
            payload = {
                "id": str(notification.id),
                "workspace_id": str(workspace_id),
                "event_type": event_type,
                "title": title,
                "message": message,
                "created_at": notification.created_at.isoformat(),
                "is_read": False,
                "action_url": action_url,
            }
            for q in cls._notification_listeners.get(recipient_id, set()).copy():
                with contextlib.suppress(Exception):
                    q.put_nowait(payload)

        # Email dispatch if enabled
        if pref.email_notifications:
            recipient_user = await db.get(User, recipient_id)
            if recipient_user and recipient_user.email:
                dev_email_adapter.send_notification_email(
                    to_email=recipient_user.email,
                    subject=title,
                    message=message,
                    action_url=action_url,
                )

        return notification

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationResponse]:
        query = (
            select(Notification, User.full_name)
            .outerjoin(User, User.id == Notification.actor_id)
            .where(
                Notification.recipient_id == user_id,
                Notification.workspace_id == workspace_id,
            )
            .order_by(desc(Notification.created_at))
            .offset(offset)
            .limit(limit)
        )
        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        res = await db.execute(query)
        rows = res.all()

        return [
            NotificationResponse(
                id=n.id,
                workspace_id=n.workspace_id,
                actor_id=n.actor_id,
                actor_name=actor_name,
                event_type=n.event_type,
                resource_type=n.resource_type,
                resource_id=n.resource_id,
                title=n.title,
                message=n.message,
                data=n.data,
                is_read=n.is_read,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n, actor_name in rows
        ]

    @staticmethod
    async def get_unread_count(
        db: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> int:
        query = select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id,
            Notification.workspace_id == workspace_id,
            Notification.is_read.is_(False),
        )
        return (await db.execute(query)).scalar_one()

    @staticmethod
    async def mark_notification_read(
        db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> NotificationResponse:
        n = await db.get(Notification, notification_id)
        if not n or n.recipient_id != user_id:
            raise DataLensException("Notification not found or access denied.", code="NOT_FOUND")

        n.is_read = True
        n.read_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(n)

        actor_name = None
        if n.actor_id:
            actor = await db.get(User, n.actor_id)
            actor_name = actor.full_name if actor else None

        return NotificationResponse(
            id=n.id,
            workspace_id=n.workspace_id,
            actor_id=n.actor_id,
            actor_name=actor_name,
            event_type=n.event_type,
            resource_type=n.resource_type,
            resource_id=n.resource_id,
            title=n.title,
            message=n.message,
            data=n.data,
            is_read=n.is_read,
            read_at=n.read_at,
            created_at=n.created_at,
        )

    @staticmethod
    async def mark_all_notifications_read(
        db: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.workspace_id == workspace_id,
                Notification.is_read.is_(False),
            )
        )
        res = await db.execute(stmt)
        unreads = res.scalars().all()
        for n in unreads:
            n.is_read = True
            n.read_at = now
        await db.commit()
        return len(unreads)

    @staticmethod
    async def dismiss_notification(
        db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        n = await db.get(Notification, notification_id)
        if not n or n.recipient_id != user_id:
            raise DataLensException("Notification not found or access denied.", code="NOT_FOUND")
        await db.delete(n)
        await db.commit()

    # ---------------------------------------------------------------------------
    # Member-Level Resource Sharing (Dashboards & Reports)
    # ---------------------------------------------------------------------------

    @staticmethod
    async def share_resource_with_member(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor: User,
        resource_type: str,
        resource_id: uuid.UUID,
        target_user_id: uuid.UUID,
        permission: str = "viewer",
    ) -> MemberShareResponse:
        """Grant specific workspace member viewer or editor permission to a dashboard or report."""
        # 1. Verify target user is in workspace
        target_mem = (
            await db.execute(
                select(WorkspaceMembership, User)
                .join(User, User.id == WorkspaceMembership.user_id)
                .where(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_id == target_user_id,
                )
            )
        ).first()
        if not target_mem:
            raise DataLensException("Target user is not a member of this workspace.", code="NOT_FOUND")
        _, target_user = target_mem

        # 2. Get resource name
        resource_name = "Resource"
        if resource_type == "dashboard":
            d = await db.get(Dashboard, resource_id)
            if not d or d.workspace_id != workspace_id:
                raise DataLensException("Dashboard not found.", code="NOT_FOUND")
            resource_name = d.name
        elif resource_type == "report":
            r = await db.get(Report, resource_id)
            if not r or r.workspace_id != workspace_id:
                raise DataLensException("Report not found.", code="NOT_FOUND")
            resource_name = r.title

        # 3. Insert or update share
        stmt = select(ResourceShare).where(
            ResourceShare.workspace_id == workspace_id,
            ResourceShare.resource_type == resource_type,
            ResourceShare.resource_id == resource_id,
            ResourceShare.shared_with_user_id == target_user_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.permission = permission
            existing.shared_by_user_id = actor.id
            existing.updated_at = datetime.now(UTC)
            share_record = existing
        else:
            share_record = ResourceShare(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_id=resource_id,
                shared_with_user_id=target_user_id,
                shared_by_user_id=actor.id,
                permission=permission,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(share_record)

        await db.commit()
        await db.refresh(share_record)

        # 4. Log activity
        await CollaborationService.log_activity(
            db=db,
            workspace_id=workspace_id,
            actor_id=actor.id,
            event_type=f"{resource_type}_shared",
            resource_type=resource_type,
            resource_id=resource_id,
            summary=f"{actor.full_name} shared {resource_type} '{resource_name}' with {target_user.full_name} ({permission})",
        )

        # 5. Dispatch notification
        action_url = (
            f"http://localhost:5173/dashboards/{resource_id}"
            if resource_type == "dashboard"
            else f"http://localhost:5173/reports/{resource_id}"
        )
        await CollaborationService.dispatch_notification(
            db=db,
            workspace_id=workspace_id,
            recipient_id=target_user_id,
            actor_id=actor.id,
            event_type=f"{resource_type}_shared",
            title=f"{actor.full_name} shared a {resource_type} with you",
            message=f"You have been granted {permission} access to '{resource_name}'.",
            resource_type=resource_type,
            resource_id=resource_id,
            action_url=action_url,
        )

        return MemberShareResponse(
            id=share_record.id,
            workspace_id=share_record.workspace_id,
            resource_type=share_record.resource_type,
            resource_id=share_record.resource_id,
            shared_with_user_id=target_user.id,
            shared_with_name=target_user.full_name,
            shared_with_email=target_user.email,
            shared_by_user_id=share_record.shared_by_user_id,
            permission=share_record.permission,
            created_at=share_record.created_at,
        )

    @staticmethod
    async def list_resource_shares(
        db: AsyncSession, workspace_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
    ) -> list[MemberShareResponse]:
        query = (
            select(ResourceShare, User)
            .join(User, User.id == ResourceShare.shared_with_user_id)
            .where(
                ResourceShare.workspace_id == workspace_id,
                ResourceShare.resource_type == resource_type,
                ResourceShare.resource_id == resource_id,
            )
            .order_by(desc(ResourceShare.created_at))
        )
        res = await db.execute(query)
        rows = res.all()

        return [
            MemberShareResponse(
                id=share.id,
                workspace_id=share.workspace_id,
                resource_type=share.resource_type,
                resource_id=share.resource_id,
                shared_with_user_id=target_user.id,
                shared_with_name=target_user.full_name,
                shared_with_email=target_user.email,
                shared_by_user_id=share.shared_by_user_id,
                permission=share.permission,
                created_at=share.created_at,
            )
            for share, target_user in rows
        ]

    @staticmethod
    async def revoke_resource_share(
        db: AsyncSession, workspace_id: uuid.UUID, share_id: uuid.UUID, actor: User
    ) -> None:
        share = await db.get(ResourceShare, share_id)
        if not share or share.workspace_id != workspace_id:
            raise DataLensException("Share record not found.", code="NOT_FOUND")

        await db.delete(share)
        await db.commit()

        await CollaborationService.log_activity(
            db=db,
            workspace_id=workspace_id,
            actor_id=actor.id,
            event_type=f"{share.resource_type}_share_revoked",
            resource_type=share.resource_type,
            resource_id=share.resource_id,
            summary=f"{actor.full_name} revoked member share for {share.resource_type}",
        )

    # ---------------------------------------------------------------------------
    # Controlled / Public Share Links
    # ---------------------------------------------------------------------------

    @staticmethod
    async def create_share_link(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor: User,
        resource_type: str,
        resource_id: uuid.UUID,
        permission: str = "viewer",
        allow_download: bool = True,
        expires_in_days: int | None = None,
        password: str | None = None,
    ) -> tuple[ShareLinkResponse, str]:
        """Generate a cryptographically secure share link."""
        raw_token = secrets.token_urlsafe(32)
        token_h = hash_token(raw_token)

        pwd_h = None
        if password:
            pwd_h = hashlib.sha256(password.encode("utf-8")).hexdigest()

        expires = None
        if expires_in_days:
            expires = datetime.now(UTC) + timedelta(days=expires_in_days)

        token_record = ShareAccessToken(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            token_hash=token_h,
            password_hash=pwd_h,
            permission=permission,
            allow_download=allow_download,
            expires_at=expires,
            is_revoked=False,
            access_count=0,
            created_by=actor.id,
            created_at=datetime.now(UTC),
        )
        db.add(token_record)
        await db.commit()
        await db.refresh(token_record)

        share_url = f"http://localhost:5173/shared/{resource_type}s/{raw_token}"

        await CollaborationService.log_activity(
            db=db,
            workspace_id=workspace_id,
            actor_id=actor.id,
            event_type=f"{resource_type}_link_created",
            resource_type=resource_type,
            resource_id=resource_id,
            summary=f"{actor.full_name} generated a {permission} share link for {resource_type}",
        )

        resp = ShareLinkResponse(
            id=token_record.id,
            workspace_id=token_record.workspace_id,
            resource_type=token_record.resource_type,
            resource_id=token_record.resource_id,
            permission=token_record.permission,
            allow_download=token_record.allow_download,
            has_password=bool(pwd_h),
            expires_at=token_record.expires_at,
            is_revoked=token_record.is_revoked,
            access_count=token_record.access_count,
            last_accessed_at=token_record.last_accessed_at,
            share_url=share_url,
            created_at=token_record.created_at,
        )
        return resp, raw_token

    @staticmethod
    async def list_share_links(
        db: AsyncSession, workspace_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
    ) -> list[ShareLinkResponse]:
        stmt = (
            select(ShareAccessToken)
            .where(
                ShareAccessToken.workspace_id == workspace_id,
                ShareAccessToken.resource_type == resource_type,
                ShareAccessToken.resource_id == resource_id,
            )
            .order_by(desc(ShareAccessToken.created_at))
        )
        res = await db.execute(stmt)
        tokens = res.scalars().all()

        return [
            ShareLinkResponse(
                id=t.id,
                workspace_id=t.workspace_id,
                resource_type=t.resource_type,
                resource_id=t.resource_id,
                permission=t.permission,
                allow_download=t.allow_download,
                has_password=bool(t.password_hash),
                expires_at=t.expires_at,
                is_revoked=t.is_revoked,
                access_count=t.access_count,
                last_accessed_at=t.last_accessed_at,
                share_url=f"http://localhost:5173/shared/{t.resource_type}s/token_{t.id.hex[:8]}",
                created_at=t.created_at,
            )
            for t in tokens
        ]

    @staticmethod
    async def revoke_share_link(
        db: AsyncSession, workspace_id: uuid.UUID, link_id: uuid.UUID, actor: User
    ) -> None:
        t = await db.get(ShareAccessToken, link_id)
        if not t or t.workspace_id != workspace_id:
            raise DataLensException("Share link not found.", code="NOT_FOUND")

        t.is_revoked = True
        await db.commit()

        await CollaborationService.log_activity(
            db=db,
            workspace_id=workspace_id,
            actor_id=actor.id,
            event_type=f"{t.resource_type}_link_revoked",
            resource_type=t.resource_type,
            resource_id=t.resource_id,
            summary=f"{actor.full_name} revoked public share link for {t.resource_type}",
        )

    @staticmethod
    async def verify_and_resolve_share_link(
        db: AsyncSession, raw_token: str, password: str | None = None
    ) -> ShareAccessToken:
        """Validate token hash, revocation, expiration, and password protection."""
        token_h = hash_token(raw_token)
        stmt = select(ShareAccessToken).where(ShareAccessToken.token_hash == token_h)
        t = (await db.execute(stmt)).scalar_one_or_none()

        if not t:
            raise DataLensException("Invalid or non-existent share link.", code="NOT_FOUND")

        if t.is_revoked:
            raise DataLensException("This share link has been revoked by an administrator.", code="FORBIDDEN")

        if t.expires_at and t.expires_at < datetime.now(UTC):
            raise DataLensException("This share link has expired.", code="EXPIRED_LINK")

        if t.password_hash:
            if not password:
                raise DataLensException("Password required to access this resource.", code="PASSWORD_REQUIRED")
            req_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if req_hash != t.password_hash:
                raise DataLensException("Incorrect password for shared link.", code="INVALID_CREDENTIALS")

        # Increment access count
        t.access_count += 1
        t.last_accessed_at = datetime.now(UTC)
        await db.commit()

        return t

    @staticmethod
    async def resolve_shared_dashboard(
        db: AsyncSession, raw_token: str, password: str | None = None
    ) -> PublicDashboardResponse:
        """Validate share link and resolve public dashboard view."""
        token_record = await CollaborationService.verify_and_resolve_share_link(
            db, raw_token, password
        )
        if token_record.resource_type != "dashboard":
            raise DataLensException("Invalid link resource type.", code="NOT_FOUND")

        from sqlalchemy.orm import selectinload

        stmt = (
            select(Dashboard)
            .where(Dashboard.id == token_record.resource_id)
            .options(
                selectinload(Dashboard.widgets),
                selectinload(Dashboard.filters),
            )
        )
        res = await db.execute(stmt)
        dashboard = res.scalar_one_or_none()
        if not dashboard:
            raise DataLensException("Dashboard not found.", code="NOT_FOUND")

        widgets_data = [
            {
                "id": str(w.id),
                "title": w.title,
                "widget_type": w.widget_type,
                "query_config": w.query_config or {},
                "grid_x": w.grid_x,
                "grid_y": w.grid_y,
                "grid_w": w.grid_w,
                "grid_h": w.grid_h,
            }
            for w in dashboard.widgets
        ]
        filters_data = [
            {
                "id": str(f.id),
                "name": f.name,
                "column_name": f.column_name,
                "filter_type": f.filter_type,
                "default_value": f.default_value,
            }
            for f in dashboard.filters
        ]

        return PublicDashboardResponse(
            id=dashboard.id,
            name=dashboard.title,
            description=dashboard.description,
            layout_config=dashboard.layout_config or {},
            widgets=widgets_data,
            filters=filters_data,
            allow_download=token_record.allow_download,
            permission=token_record.permission,
        )

    @staticmethod
    async def resolve_shared_report_download(
        db: AsyncSession, raw_token: str, password: str | None = None
    ) -> tuple[bytes, str, str]:
        """Validate share link and resolve report artifact download."""
        token_record = await CollaborationService.verify_and_resolve_share_link(
            db, raw_token, password
        )
        if token_record.resource_type != "report":
            raise DataLensException("Invalid link resource type.", code="NOT_FOUND")

        from app.services.reports.business_report_service import BusinessReportService

        runs = await BusinessReportService.list_report_runs(
            token_record.resource_id, token_record.workspace_id, db
        )
        if not runs:
            raise DataLensException("No generated report files available for download.", code="NOT_FOUND")
        latest_run = runs[0]
        return await BusinessReportService.get_run_file(
            latest_run.id, token_record.workspace_id, db, format_type="pdf"
        )

    # ---------------------------------------------------------------------------
    # Dashboard Cloning / Duplication
    # ---------------------------------------------------------------------------

    @staticmethod
    async def duplicate_dashboard(
        db: AsyncSession,
        dashboard_id: uuid.UUID,
        target_workspace_id: uuid.UUID,
        actor: User,
        new_name: str | None = None,
    ) -> Dashboard:
        """Clone an authorized dashboard and all associated widgets/filters into target workspace."""
        original = await db.get(Dashboard, dashboard_id)
        if not original:
            raise DataLensException("Dashboard not found.", code="NOT_FOUND")

        cloned = Dashboard(
            id=uuid.uuid4(),
            workspace_id=target_workspace_id,
            owner_id=actor.id,
            name=new_name.strip() if new_name else f"{original.name} (Copy)",
            description=original.description,
            layout_config=original.layout_config,
            visibility="workspace",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(cloned)
        await db.flush()

        # Duplicate widgets
        w_stmt = select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id)
        widgets = (await db.execute(w_stmt)).scalars().all()
        for w in widgets:
            cw = DashboardWidget(
                id=uuid.uuid4(),
                dashboard_id=cloned.id,
                dataset_id=w.dataset_id,
                dataset_version_id=w.dataset_version_id,
                widget_type=w.widget_type,
                title=w.title,
                description=w.description,
                grid_x=w.grid_x,
                grid_y=w.grid_y,
                grid_w=w.grid_w,
                grid_h=w.grid_h,
                query_config=w.query_config,
                visual_config=w.visual_config,
            )
            db.add(cw)

        # Duplicate filters
        f_stmt = select(DashboardFilter).where(DashboardFilter.dashboard_id == dashboard_id)
        filters = (await db.execute(f_stmt)).scalars().all()
        for f in filters:
            cf = DashboardFilter(
                id=uuid.uuid4(),
                dashboard_id=cloned.id,
                name=f.name,
                column=f.column,
                operator=f.operator,
                default_value=f.default_value,
                filter_type=f.filter_type,
            )
            db.add(cf)

        await db.commit()
        await db.refresh(cloned)

        await CollaborationService.log_activity(
            db=db,
            workspace_id=target_workspace_id,
            actor_id=actor.id,
            event_type="dashboard_duplicated",
            resource_type="dashboard",
            resource_id=cloned.id,
            summary=f"{actor.full_name} duplicated dashboard '{original.name}' as '{cloned.name}'",
        )

        return cloned

    # ---------------------------------------------------------------------------
    # Threaded Comments & Discussions
    # ---------------------------------------------------------------------------

    @staticmethod
    def sanitize_comment_content(raw: str) -> str:
        """Escape HTML and strip unsafe tags to guarantee XSS prevention."""
        escaped = html.escape(raw.strip())
        return escaped

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        actor: User,
        resource_type: str,
        resource_id: uuid.UUID,
        content: str,
        parent_id: uuid.UUID | None = None,
        mentions: list[str] | None = None,
    ) -> CommentResponse:
        """Create a new top-level comment or threaded reply."""
        clean_content = CollaborationService.sanitize_comment_content(content)
        if not clean_content:
            raise DataLensException("Comment content cannot be empty.", code="BAD_REQUEST")

        # Parse inline @mentions (e.g. @username or @email)
        extracted_mentions = list(mentions or [])
        inline_tags = re.findall(r"@([a-zA-Z0-9_.-]+)", clean_content)
        for tag in inline_tags:
            if tag not in extracted_mentions:
                extracted_mentions.append(tag)

        comment = Comment(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            parent_id=parent_id,
            author_id=actor.id,
            content=clean_content,
            mentions=extracted_mentions,
            is_resolved=False,
            is_deleted=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        # Activity log
        await CollaborationService.log_activity(
            db=db,
            workspace_id=workspace_id,
            actor_id=actor.id,
            event_type="comment_added",
            resource_type=resource_type,
            resource_id=resource_id,
            summary=f"{actor.full_name} commented on {resource_type}: \"{clean_content[:60]}...\"",
        )

        # Notify mentioned users
        action_url = (
            f"http://localhost:5173/dashboards/{resource_id}"
            if resource_type == "dashboard"
            else f"http://localhost:5173/reports/{resource_id}"
        )
        if extracted_mentions:
            # Resolve mentioned users
            m_users = (
                await db.execute(
                    select(User)
                    .join(WorkspaceMembership, WorkspaceMembership.user_id == User.id)
                    .where(
                        WorkspaceMembership.workspace_id == workspace_id,
                        (User.email.in_(extracted_mentions))
                        | (User.full_name.in_(extracted_mentions)),
                    )
                )
            ).scalars().all()

            for mu in m_users:
                await CollaborationService.dispatch_notification(
                    db=db,
                    workspace_id=workspace_id,
                    recipient_id=mu.id,
                    actor_id=actor.id,
                    event_type="mention",
                    title=f"{actor.full_name} mentioned you in a discussion",
                    message=f"\"{clean_content[:150]}\"",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action_url=action_url,
                )

        # If this is a reply, notify parent author
        if parent_id:
            parent_comment = await db.get(Comment, parent_id)
            if parent_comment and parent_comment.author_id != actor.id:
                await CollaborationService.dispatch_notification(
                    db=db,
                    workspace_id=workspace_id,
                    recipient_id=parent_comment.author_id,
                    actor_id=actor.id,
                    event_type="comment_reply",
                    title=f"{actor.full_name} replied to your comment",
                    message=f"\"{clean_content[:150]}\"",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action_url=action_url,
                )

        return CommentResponse(
            id=comment.id,
            workspace_id=comment.workspace_id,
            resource_type=comment.resource_type,
            resource_id=comment.resource_id,
            parent_id=comment.parent_id,
            author_id=actor.id,
            author_name=actor.full_name,
            author_email=actor.email,
            content=comment.content,
            mentions=comment.mentions,
            is_resolved=comment.is_resolved,
            resolved_by_id=None,
            resolved_by_name=None,
            resolved_at=None,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[],
        )

    @staticmethod
    async def list_comments(
        db: AsyncSession, workspace_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
    ) -> list[CommentResponse]:
        """Fetch all comments for a resource and assemble parent-child threaded replies."""
        query = (
            select(Comment, User.full_name, User.email)
            .join(User, User.id == Comment.author_id)
            .where(
                Comment.workspace_id == workspace_id,
                Comment.resource_type == resource_type,
                Comment.resource_id == resource_id,
                Comment.is_deleted.is_(False),
            )
            .order_by(Comment.created_at.asc())
        )
        res = await db.execute(query)
        rows = res.all()

        comment_map: dict[uuid.UUID, CommentResponse] = {}
        top_level: list[CommentResponse] = []

        for c, author_name, author_email in rows:
            c_resp = CommentResponse(
                id=c.id,
                workspace_id=c.workspace_id,
                resource_type=c.resource_type,
                resource_id=c.resource_id,
                parent_id=c.parent_id,
                author_id=c.author_id,
                author_name=author_name,
                author_email=author_email,
                content=c.content,
                mentions=c.mentions,
                is_resolved=c.is_resolved,
                resolved_by_id=c.resolved_by_id,
                resolved_by_name=None,
                resolved_at=c.resolved_at,
                is_deleted=c.is_deleted,
                created_at=c.created_at,
                updated_at=c.updated_at,
                replies=[],
            )
            comment_map[c.id] = c_resp

        # Link parent/child replies
        for _c_id, c_resp in comment_map.items():
            if c_resp.parent_id and c_resp.parent_id in comment_map:
                comment_map[c_resp.parent_id].replies.append(c_resp)
            else:
                top_level.append(c_resp)

        return top_level

    @staticmethod
    async def update_comment(
        db: AsyncSession, comment_id: uuid.UUID, actor: User, new_content: str
    ) -> CommentResponse:
        c = await db.get(Comment, comment_id)
        if not c or c.is_deleted:
            raise DataLensException("Comment not found.", code="NOT_FOUND")
        if c.author_id != actor.id:
            raise DataLensException("You can only edit your own comments.", code="FORBIDDEN")

        c.content = CollaborationService.sanitize_comment_content(new_content)
        c.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(c)

        return CommentResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            resource_type=c.resource_type,
            resource_id=c.resource_id,
            parent_id=c.parent_id,
            author_id=actor.id,
            author_name=actor.full_name,
            author_email=actor.email,
            content=c.content,
            mentions=c.mentions,
            is_resolved=c.is_resolved,
            resolved_by_id=c.resolved_by_id,
            resolved_by_name=None,
            resolved_at=c.resolved_at,
            is_deleted=c.is_deleted,
            created_at=c.created_at,
            updated_at=c.updated_at,
            replies=[],
        )

    @staticmethod
    async def delete_comment(db: AsyncSession, comment_id: uuid.UUID, actor: User) -> None:
        c = await db.get(Comment, comment_id)
        if not c or c.is_deleted:
            raise DataLensException("Comment not found.", code="NOT_FOUND")
        if c.author_id != actor.id:
            # Check if workspace admin
            mem = (
                await db.execute(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == c.workspace_id,
                        WorkspaceMembership.user_id == actor.id,
                    )
                )
            ).scalar_one_or_none()
            if not mem or not is_role_at_least(mem.role, "admin"):
                raise DataLensException("You do not have permission to delete this comment.", code="FORBIDDEN")

        c.is_deleted = True
        c.updated_at = datetime.now(UTC)
        await db.commit()

    @staticmethod
    async def resolve_discussion(
        db: AsyncSession, comment_id: uuid.UUID, actor: User
    ) -> CommentResponse:
        c = await db.get(Comment, comment_id)
        if not c or c.is_deleted:
            raise DataLensException("Comment not found.", code="NOT_FOUND")

        c.is_resolved = True
        c.resolved_by_id = actor.id
        c.resolved_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(c)

        await CollaborationService.log_activity(
            db=db,
            workspace_id=c.workspace_id,
            actor_id=actor.id,
            event_type="discussion_resolved",
            resource_type=c.resource_type,
            resource_id=c.resource_id,
            summary=f"{actor.full_name} marked discussion as resolved",
        )

        return CommentResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            resource_type=c.resource_type,
            resource_id=c.resource_id,
            parent_id=c.parent_id,
            author_id=c.author_id,
            author_name=actor.full_name,
            author_email=actor.email,
            content=c.content,
            mentions=c.mentions,
            is_resolved=c.is_resolved,
            resolved_by_id=actor.id,
            resolved_by_name=actor.full_name,
            resolved_at=c.resolved_at,
            is_deleted=c.is_deleted,
            created_at=c.created_at,
            updated_at=c.updated_at,
            replies=[],
        )

    @staticmethod
    async def reopen_discussion(
        db: AsyncSession, comment_id: uuid.UUID, actor: User
    ) -> CommentResponse:
        c = await db.get(Comment, comment_id)
        if not c or c.is_deleted:
            raise DataLensException("Comment not found.", code="NOT_FOUND")

        c.is_resolved = False
        c.resolved_by_id = None
        c.resolved_at = None
        await db.commit()
        await db.refresh(c)

        return CommentResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            resource_type=c.resource_type,
            resource_id=c.resource_id,
            parent_id=c.parent_id,
            author_id=c.author_id,
            author_name=actor.full_name,
            author_email=actor.email,
            content=c.content,
            mentions=c.mentions,
            is_resolved=c.is_resolved,
            resolved_by_id=None,
            resolved_by_name=None,
            resolved_at=None,
            is_deleted=c.is_deleted,
            created_at=c.created_at,
            updated_at=c.updated_at,
            replies=[],
        )

    # ---------------------------------------------------------------------------
    # Extended Workspace Invitations Management
    # ---------------------------------------------------------------------------

    @staticmethod
    async def list_workspace_invitations(
        db: AsyncSession, workspace_id: uuid.UUID, status_filter: str | None = None
    ) -> list[InvitationResponse]:
        query = (
            select(WorkspaceInvitation, User.full_name)
            .outerjoin(User, User.id == WorkspaceInvitation.inviter_id)
            .where(WorkspaceInvitation.workspace_id == workspace_id)
            .order_by(desc(WorkspaceInvitation.created_at))
        )
        if status_filter:
            query = query.where(WorkspaceInvitation.status == status_filter)

        res = await db.execute(query)
        rows = res.all()

        now = datetime.now(UTC)
        out = []
        for inv, inviter_name in rows:
            # Check auto-expiration status
            current_status = inv.status
            if current_status == "pending" and inv.expires_at < now:
                current_status = "expired"

            out.append(
                InvitationResponse(
                    id=inv.id,
                    workspace_id=inv.workspace_id,
                    email=inv.email,
                    role=inv.role,
                    status=current_status,
                    expires_at=inv.expires_at,
                    resend_count=inv.resend_count,
                    created_at=inv.created_at,
                    inviter_id=inv.inviter_id,
                    inviter_name=inviter_name,
                    invitation_url=f"http://localhost:5173/invitations/accept?invitation_id={inv.id}",
                )
            )
        return out

    @staticmethod
    async def resend_invitation(
        db: AsyncSession, workspace_id: uuid.UUID, invitation_id: uuid.UUID, actor: User
    ) -> InvitationResponse:
        inv = await db.get(WorkspaceInvitation, invitation_id)
        if not inv or inv.workspace_id != workspace_id:
            raise DataLensException("Invitation not found.", code="NOT_FOUND")

        if inv.status in ("accepted", "revoked"):
            raise DataLensException(f"Cannot resend an invitation in '{inv.status}' status.", code="BAD_REQUEST")

        raw_token = secrets.token_urlsafe(32)
        inv.token_hash = hash_token(raw_token)
        inv.expires_at = datetime.now(UTC) + timedelta(days=settings.INVITATION_TOKEN_EXPIRE_DAYS)
        inv.status = "pending"
        inv.resend_count += 1
        inv.inviter_id = actor.id

        await db.commit()
        await db.refresh(inv)

        ws = await db.get(Workspace, workspace_id)
        dev_email_adapter.send_workspace_invitation(
            to_email=inv.email,
            workspace_name=ws.name if ws else "DataLens Workspace",
            invitation_token=raw_token,
            inviter_name=actor.full_name,
        )

        return InvitationResponse(
            id=inv.id,
            workspace_id=inv.workspace_id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            expires_at=inv.expires_at,
            resend_count=inv.resend_count,
            created_at=inv.created_at,
            inviter_id=inv.inviter_id,
            inviter_name=actor.full_name,
            invitation_url=f"http://localhost:5173/invitations/accept?token={raw_token}",
        )

    @staticmethod
    async def revoke_invitation(
        db: AsyncSession, workspace_id: uuid.UUID, invitation_id: uuid.UUID, actor: User
    ) -> None:
        inv = await db.get(WorkspaceInvitation, invitation_id)
        if not inv or inv.workspace_id != workspace_id:
            raise DataLensException("Invitation not found.", code="NOT_FOUND")

        inv.status = "revoked"
        inv.revoked_at = datetime.now(UTC)
        await db.commit()

        await CollaborationService.log_activity(
            db=db,
            workspace_id=workspace_id,
            actor_id=actor.id,
            event_type="invitation_revoked",
            resource_type="workspace",
            resource_id=workspace_id,
            summary=f"{actor.full_name} revoked invitation to {inv.email}",
        )

    @staticmethod
    async def get_invitation_detail(db: AsyncSession, token: str) -> InvitationDetailResponse:
        """Fetch invitation metadata for the public acceptance UI."""
        token_h = hash_token(token)
        stmt = (
            select(WorkspaceInvitation, Workspace.name, User.full_name)
            .join(Workspace, Workspace.id == WorkspaceInvitation.workspace_id)
            .outerjoin(User, User.id == WorkspaceInvitation.inviter_id)
            .where(WorkspaceInvitation.token_hash == token_h)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise DataLensException("Invalid invitation token.", code="NOT_FOUND")

        inv, ws_name, inviter_name = row
        now = datetime.now(UTC)
        is_valid = inv.status == "pending" and inv.expires_at >= now

        return InvitationDetailResponse(
            id=inv.id,
            workspace_id=inv.workspace_id,
            workspace_name=ws_name,
            inviter_name=inviter_name or "A team member",
            email=inv.email,
            role=inv.role,
            status="expired" if (inv.status == "pending" and inv.expires_at < now) else inv.status,
            expires_at=inv.expires_at,
            is_valid=is_valid,
        )

    @staticmethod
    async def decline_invitation(db: AsyncSession, token: str, user: User | None = None) -> None:
        token_h = hash_token(token)
        stmt = select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == token_h)
        inv = (await db.execute(stmt)).scalar_one_or_none()
        if not inv:
            raise DataLensException("Invalid invitation token.", code="NOT_FOUND")

        inv.status = "declined"
        inv.declined_at = datetime.now(UTC)
        await db.commit()

    get_invitation_by_token = get_invitation_detail

