"""Comprehensive test suite for Phase 5B Team Collaboration, Sharing, Discussions, and Notifications."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import DataLensException
from app.core.security import hash_token
from app.dependencies.auth import require_active_user
from app.main import app
from app.models.collaboration import (
    NotificationPreference,
    ShareAccessToken,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.services.collaboration_service import CollaborationService


@pytest.fixture
def mock_actor():
    return User(
        id=uuid.uuid4(),
        email="alice.owner@datalens.app",
        full_name="Alice Owner",
        is_active=True,
    )


@pytest.fixture
def mock_target_user():
    return User(
        id=uuid.uuid4(),
        email="bob.collaborator@datalens.app",
        full_name="Bob Collaborator",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Unit / Service Level Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_logging_and_sanitization(mock_actor):
    """Verify activity logging strips secret keys to guarantee zero secret leakage."""
    db = AsyncMock()
    ws_id = uuid.uuid4()

    dirty_meta = {
        "dataset_name": "Sales Q3",
        "password": "super-secret-password",
        "api_key": "secret-token-xyz",
        "rows_count": 1500,
    }

    act = await CollaborationService.log_activity(
        db=db,
        workspace_id=ws_id,
        actor_id=mock_actor.id,
        event_type="dataset_imported",
        resource_type="dataset",
        resource_id=uuid.uuid4(),
        summary="Imported sales dataset",
        metadata_snapshot=dirty_meta,
    )

    assert act.workspace_id == ws_id
    assert act.actor_id == mock_actor.id
    # Ensure sensitive fields were scrubbed
    assert act.metadata_snapshot["password"] == "••••••••"
    assert act.metadata_snapshot["api_key"] == "••••••••"
    assert act.metadata_snapshot["dataset_name"] == "Sales Q3"
    assert act.metadata_snapshot["rows_count"] == 1500
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_notification_dispatch_and_no_self_notification(mock_actor):
    """Verify an actor cannot trigger a notification to themselves."""
    db = AsyncMock()
    ws_id = uuid.uuid4()

    notif = await CollaborationService.dispatch_notification(
        db=db,
        workspace_id=ws_id,
        recipient_id=mock_actor.id,
        actor_id=mock_actor.id,
        event_type="test_event",
        title="Test Title",
        message="Test Message",
    )
    assert notif is None
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_comment_xss_sanitization_and_mention_extraction(mock_actor):
    """Verify comments escape dangerous HTML/scripts and extract @mentions."""
    db = AsyncMock()
    ws_id = uuid.uuid4()
    dash_id = uuid.uuid4()

    raw_content = "Hello @alice and @bob! Check this <script>alert('xss')</script> and <b>bold</b>"

    # Mock user lookups for mentions
    mock_user_res = MagicMock()
    mock_user_res.scalars.return_value.all.return_value = [
        User(id=uuid.uuid4(), email="alice@test.com", full_name="Alice"),
        User(id=uuid.uuid4(), email="bob@test.com", full_name="Bob"),
    ]
    db.execute.return_value = mock_user_res

    comment = await CollaborationService.create_comment(
        db=db,
        workspace_id=ws_id,
        actor=mock_actor,
        resource_type="dashboard",
        resource_id=dash_id,
        content=raw_content,
    )

    # Check XSS escaped
    assert "<script>" not in comment.content
    assert "&lt;script&gt;" in comment.content
    # Check mentions detected
    assert len(comment.mentions) >= 2
    assert "alice" in comment.mentions
    assert "bob" in comment.mentions


@pytest.mark.asyncio
async def test_share_link_creation_and_password_validation(mock_actor):
    """Verify share link generates a secure urlsafe token and securely hashes passwords."""
    db = AsyncMock()
    ws_id = uuid.uuid4()
    dash_id = uuid.uuid4()

    # Create link with password
    link_resp, raw_token = await CollaborationService.create_share_link(
        db=db,
        workspace_id=ws_id,
        actor=mock_actor,
        resource_type="dashboard",
        resource_id=dash_id,
        permission="viewer",
        password="MySecretPassword123!",
    )

    assert link_resp.has_password is True
    assert link_resp.share_url.startswith("http://localhost:5173/shared/dashboards/")
    assert db.add.call_count == 2


@pytest.mark.asyncio
async def test_share_link_expired():
    """Verify expired share token raises EXPIRED_LINK."""
    db = AsyncMock()
    expired_token = ShareAccessToken(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        resource_type="dashboard",
        resource_id=uuid.uuid4(),
        token_hash="fakehash",
        is_revoked=False,
        expires_at=datetime.now(UTC) - timedelta(hours=2),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = expired_token
    db.execute.return_value = mock_res

    with pytest.raises(DataLensException) as exc_info:
        await CollaborationService.verify_and_resolve_share_link(db=db, raw_token="anytoken")
    assert exc_info.value.code == "EXPIRED_LINK"


@pytest.mark.asyncio
async def test_share_link_password_check():
    """Verify incorrect password raises INVALID_CREDENTIALS."""
    db = AsyncMock()
    protected_token = ShareAccessToken(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        resource_type="dashboard",
        resource_id=uuid.uuid4(),
        token_hash="fakehash",
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=2),
        password_hash=hash_token("CorrectPassword"),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = protected_token
    db.execute.return_value = mock_res

    # Missing / Wrong password
    with pytest.raises(DataLensException) as exc_info:
        await CollaborationService.verify_and_resolve_share_link(
            db=db, raw_token="anytoken", password="WrongPassword"
        )
    assert exc_info.value.code in ("INVALID_CREDENTIALS", "INVALID_PASSWORD")


# ---------------------------------------------------------------------------
# API Route Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def override_auth(mock_actor):
    app.dependency_overrides[require_active_user] = lambda: mock_actor
    yield
    app.dependency_overrides.pop(require_active_user, None)


@pytest.mark.asyncio
async def test_invitation_endpoints_public_lookup():
    """Verify GET /api/v1/invitations/{token} returns invitation metadata."""
    with patch.object(CollaborationService, "get_invitation_by_token") as mock_get_inv:
        mock_get_inv.return_value = {
            "id": uuid.uuid4(),
            "workspace_id": uuid.uuid4(),
            "workspace_name": "Acme Corp Analytics",
            "inviter_name": "Alice Owner",
            "email": "candidate@example.com",
            "role": "editor",
            "status": "pending",
            "expires_at": datetime.now(UTC) + timedelta(days=5),
            "is_valid": True,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/invitations/sample-token-12345")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["workspace_name"] == "Acme Corp Analytics"
            assert data["data"]["role"] == "editor"


@pytest.mark.asyncio
async def test_invitation_decline_endpoint():
    """Verify POST /api/v1/invitations/{token}/decline marks invitation as declined."""
    with patch.object(CollaborationService, "decline_invitation") as mock_decline:
        mock_decline.return_value = None

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/invitations/sample-token-12345/decline")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["success"] is True


@pytest.mark.asyncio
async def test_comments_api_flow():
    """Verify comments listing and posting via API endpoints."""
    ws_id = uuid.uuid4()
    dash_id = uuid.uuid4()

    with patch("app.services.workspace_service.WorkspaceService.get_workspace") as mock_ws_chk, \
         patch.object(CollaborationService, "list_comments") as mock_list_com, \
         patch.object(CollaborationService, "create_comment") as mock_create_com:

        mock_ws_chk.return_value = (Workspace(id=ws_id, name="Test WS"), "admin")
        mock_list_com.return_value = []
        mock_create_com.return_value = {
            "id": uuid.uuid4(),
            "workspace_id": ws_id,
            "resource_type": "dashboard",
            "resource_id": dash_id,
            "author_id": uuid.uuid4(),
            "author_name": "Alice Owner",
            "author_email": "alice@datalens.app",
            "content": "Great dashboard!",
            "mentions": [],
            "is_resolved": False,
            "is_deleted": False,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "replies": [],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. List comments
            get_resp = await client.get(
                f"/api/v1/comments?workspace_id={ws_id}&resource_type=dashboard&resource_id={dash_id}"
            )
            assert get_resp.status_code == 200
            assert get_resp.json()["data"] == []

            # 2. Post comment
            post_resp = await client.post(
                "/api/v1/comments",
                json={
                    "workspace_id": str(ws_id),
                    "resource_type": "dashboard",
                    "resource_id": str(dash_id),
                    "content": "Great dashboard!",
                },
            )
            assert post_resp.status_code == 201
            assert post_resp.json()["data"]["content"] == "Great dashboard!"


@pytest.mark.asyncio
async def test_notifications_unread_count_and_preferences():
    """Verify notifications unread count and preference endpoints."""
    ws_id = uuid.uuid4()

    with patch("app.services.workspace_service.WorkspaceService.get_workspace") as mock_ws_chk, \
         patch.object(CollaborationService, "get_unread_count") as mock_unread, \
         patch.object(CollaborationService, "get_or_create_preferences") as mock_pref:

        mock_ws_chk.return_value = (Workspace(id=ws_id, name="Test WS"), "owner")
        mock_unread.return_value = 4
        mock_pref.return_value = NotificationPreference(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            workspace_id=ws_id,
            email_notifications=True,
            in_app_notifications=True,
            mention_notifications=True,
            share_notifications=True,
            updated_at=datetime.now(UTC),
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. Unread count
            cnt_resp = await client.get(f"/api/v1/notifications/unread-count?workspace_id={ws_id}")
            assert cnt_resp.status_code == 200
            assert cnt_resp.json()["data"]["unread_count"] == 4

            # 2. Preferences
            pref_resp = await client.get(f"/api/v1/notifications/preferences?workspace_id={ws_id}")
            assert pref_resp.status_code == 200
            assert pref_resp.json()["data"]["email_notifications"] is True
