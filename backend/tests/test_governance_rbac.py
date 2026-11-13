"""Comprehensive test suite for Phase 5C Enterprise Governance, Advanced RBAC, and Security Audit."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies.auth import require_active_user
from app.main import app
from app.models.governance import (
    CustomRole,
    ResourceAccessPolicy,
    SecurityEvent,
    WorkspaceSecurityPolicy,
)
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.governance_service import GovernanceService


@pytest.fixture
def mock_owner():
    return User(
        id=uuid.uuid4(),
        email="owner@datalens.app",
        full_name="Workspace Owner",
        is_active=True,
    )


@pytest.fixture
def mock_analyst():
    return User(
        id=uuid.uuid4(),
        email="analyst@datalens.app",
        full_name="Data Analyst",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 1. Permissions Catalog & Hierarchy
# ---------------------------------------------------------------------------


def test_permissions_catalog():
    """Verify system permissions catalog contains all governance categories."""
    catalog = GovernanceService.get_permissions_catalog()
    assert len(catalog.permissions) >= 20
    assert "Datasets" in catalog.categories
    assert "Dashboards" in catalog.categories
    assert "Reports" in catalog.categories
    assert "Governance" in catalog.categories


# ---------------------------------------------------------------------------
# 2. Authorization Evaluation Engine (RBAC)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorization_owner_universal_access(mock_owner):
    """Verify workspace owner always passes permission checks."""
    db = AsyncMock()
    ws_id = uuid.uuid4()

    mock_ws = Workspace(id=ws_id, name="Corporate Analytics", owner_id=mock_owner.id)
    db.get.return_value = mock_ws

    has_perm = await GovernanceService.has_workspace_permission(
        db=db,
        workspace_id=ws_id,
        user=mock_owner,
        permission_code="governance:manage",
    )
    assert has_perm is True


@pytest.mark.asyncio
async def test_authorization_custom_role_evaluation(mock_analyst):
    """Verify custom role permissions are strictly evaluated."""
    db = AsyncMock()
    ws_id = uuid.uuid4()
    custom_role_id = uuid.uuid4()

    mock_ws = Workspace(id=ws_id, name="Corporate Analytics", owner_id=uuid.uuid4())
    mock_membership = WorkspaceMembership(
        workspace_id=ws_id,
        user_id=mock_analyst.id,
        role="custom_analyst",
        custom_role_id=custom_role_id,
    )
    mock_custom_role = CustomRole(
        id=custom_role_id,
        workspace_id=ws_id,
        name="Custom Analyst",
        permissions=["dataset:view", "report:download"],
        is_system=False,
    )

    db.get.side_effect = lambda model, obj_id: (
        mock_ws if model == Workspace else (mock_custom_role if model == CustomRole else None)
    )

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = mock_membership
    db.execute.return_value = mock_exec

    # Permitted code
    assert (
        await GovernanceService.has_workspace_permission(
            db=db, workspace_id=ws_id, user=mock_analyst, permission_code="dataset:view"
        )
        is True
    )

    # Denied code
    assert (
        await GovernanceService.has_workspace_permission(
            db=db, workspace_id=ws_id, user=mock_analyst, permission_code="dataset:delete"
        )
        is False
    )


# ---------------------------------------------------------------------------
# 3. Resource-Level Access Control (RLAC) Precedence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rlac_explicit_deny_precedence(mock_analyst):
    """Verify explicit resource DENY overrides any granted role permission."""
    db = AsyncMock()
    ws_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_ws = Workspace(id=ws_id, name="Test WS", owner_id=uuid.uuid4())
    mock_mem = WorkspaceMembership(
        workspace_id=ws_id, user_id=mock_analyst.id, role="editor"
    )

    # Explicit deny on this specific report
    deny_policy = ResourceAccessPolicy(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        resource_type="report",
        resource_id=report_id,
        user_id=mock_analyst.id,
        is_denied=True,
    )

    db.get.return_value = mock_ws
    mock_mem_res = MagicMock()
    mock_mem_res.scalar_one_or_none.return_value = mock_mem
    mock_pol_res = MagicMock()
    mock_pol_res.scalars.return_value.all.return_value = [deny_policy]

    db.execute.side_effect = [mock_mem_res, mock_pol_res]

    can_access = await GovernanceService.check_resource_access(
        db=db,
        workspace_id=ws_id,
        user=mock_analyst,
        resource_type="report",
        resource_id=report_id,
        required_permission="viewer",
    )
    assert can_access is False


# ---------------------------------------------------------------------------
# 4. Data Governance & Column Masking
# ---------------------------------------------------------------------------


def test_column_masking_schemes():
    """Verify redact, hash, and partial column masking transformations."""
    rows = [
        {"customer_id": 101, "ssn": "123-45-6789", "salary": 95000, "email": "alice@corp.com"},
        {"customer_id": 102, "ssn": "987-65-4321", "salary": 120000, "email": "bob@corp.com"},
    ]

    masks = {
        "ssn": {"type": "redact"},
        "salary": {"type": "hash"},
        "email": {"type": "partial"},
    }

    masked = GovernanceService.apply_column_masking(rows, masks, has_bypass_clearance=False)

    # Redacted
    assert masked[0]["ssn"] == "••••••••"
    # Hashed
    assert masked[0]["salary"] != 95000
    assert len(masked[0]["salary"]) == 16
    # Partial
    assert masked[0]["email"].startswith("*******")
    assert masked[0]["email"].endswith(".com")
    # Unmasked column left intact
    assert masked[0]["customer_id"] == 101


# ---------------------------------------------------------------------------
# 5. Immutable Enterprise Audit Logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chained_audit_log_and_secret_redaction(mock_owner):
    """Verify audit log redacts sensitive keys and calculates chained hash."""
    db = AsyncMock()
    ws_id = uuid.uuid4()

    mock_prev_res = MagicMock()
    mock_prev_res.scalar_one_or_none.return_value = "PREV_CHAIN_HASH_XYZ"
    db.execute.return_value = mock_prev_res

    dirty_meta = {
        "user_email": "target@example.com",
        "db_password": "supersecretpassword",
        "api_token": "bearer-token-1234",
    }

    log = await GovernanceService.record_audit_event(
        db=db,
        workspace_id=ws_id,
        actor=mock_owner,
        action="datasource_connection_created",
        resource_type="datasource",
        resource_id=uuid.uuid4(),
        outcome="SUCCESS",
        metadata_snapshot=dirty_meta,
    )

    assert log.metadata_snapshot["db_password"] == "••••••••"
    assert log.metadata_snapshot["api_token"] == "••••••••"
    assert log.metadata_snapshot["user_email"] == "target@example.com"
    assert log.previous_hash == "PREV_CHAIN_HASH_XYZ"
    assert len(log.chained_hash) == 64
    db.add.assert_called_once()


# ---------------------------------------------------------------------------
# 6. Security Events Monitoring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_event_lifecycle(mock_owner):
    """Verify security event recording and administrative resolution."""
    db = AsyncMock()
    ws_id = uuid.uuid4()
    evt_id = uuid.uuid4()

    event = SecurityEvent(
        id=evt_id,
        workspace_id=ws_id,
        event_type="UNAUTHORIZED_ACCESS_BURST",
        severity="HIGH",
        details={"attempted_path": "/api/v1/audit-logs", "attempts": 12},
        status="OPEN",
        created_at=datetime.now(UTC),
    )
    db.get.return_value = event

    with patch.object(GovernanceService, "has_workspace_permission", return_value=True):
        updated = await GovernanceService.update_security_event_status(
            db=db,
            workspace_id=ws_id,
            event_id=evt_id,
            actor=mock_owner,
            status="RESOLVED",
            notes="Investigated and verified legitimate external scanner probe.",
        )

        assert updated.status == "RESOLVED"
        assert updated.resolved_by == mock_owner.id
        assert updated.details["resolution_notes"] == "Investigated and verified legitimate external scanner probe."


# ---------------------------------------------------------------------------
# 7. User Sessions Management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_creation_and_revocation():
    """Verify session creation and revocation enforcement."""
    db = AsyncMock()
    user_id = uuid.uuid4()
    raw_token = "secure_user_token_12345"

    session = await GovernanceService.create_user_session(
        db=db,
        user_id=user_id,
        raw_token=raw_token,
        ip_address="192.168.1.50",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    )

    assert session.user_id == user_id
    assert session.device_label == "Windows Browser"
    assert session.is_revoked is False
    db.add.assert_called_once()

    # Revoke session
    db.get.return_value = session
    await GovernanceService.revoke_session(db=db, user_id=user_id, session_id=session.id)
    assert session.is_revoked is True


# ---------------------------------------------------------------------------
# 8. API Route Endpoint Verification
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def override_auth(mock_owner):
    app.dependency_overrides[require_active_user] = lambda: mock_owner
    yield
    app.dependency_overrides.pop(require_active_user, None)


@pytest.mark.asyncio
async def test_api_permissions_catalog():
    """Verify GET /api/v1/permissions/catalog endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/v1/permissions/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["permissions"]) >= 20


@pytest.mark.asyncio
async def test_api_workspace_security_policy():
    """Verify GET and PUT /api/v1/workspace-security endpoints."""
    ws_id = uuid.uuid4()
    policy = WorkspaceSecurityPolicy(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        allow_public_share_links=True,
        max_share_link_days=30,
        restrict_external_sharing=False,
        restrict_report_downloads=False,
        restrict_dataset_exports=False,
        max_session_hours=24,
        allowed_invitation_domains=["corp.com"],
        custom_roles_enabled=True,
        audit_retention_days=90,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    with patch("app.services.workspace_service.WorkspaceService.get_workspace") as mock_ws_chk, \
         patch.object(GovernanceService, "get_or_create_policy", return_value=policy), \
         patch.object(GovernanceService, "update_security_policy", return_value=policy):

        mock_ws_chk.return_value = (Workspace(id=ws_id, name="Test WS"), "owner")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. GET policy
            get_resp = await client.get(f"/api/v1/workspace-security?workspace_id={ws_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["data"]["allow_public_share_links"] is True

            # 2. PUT policy
            put_resp = await client.put(
                f"/api/v1/workspace-security?workspace_id={ws_id}",
                json={"allow_public_share_links": False, "restrict_dataset_exports": True},
            )
            assert put_resp.status_code == 200
            assert put_resp.json()["success"] is True
