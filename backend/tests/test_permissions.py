import pytest

from app.core.permissions import (
    WorkspaceRole,
    can_invite_role,
    can_manage_member,
    is_role_at_least,
    normalize_role,
)


def test_role_normalization():
    assert normalize_role("OWNER") == "owner"
    assert normalize_role("Admin ") == "admin"
    assert normalize_role("editor") == "editor"
    assert normalize_role("Viewer") == "viewer"

    with pytest.raises(ValueError):
        normalize_role("SuperUser")


def test_role_hierarchy():
    # Owner >= all
    assert is_role_at_least(WorkspaceRole.OWNER, WorkspaceRole.ADMIN) is True
    assert is_role_at_least(WorkspaceRole.OWNER, WorkspaceRole.EDITOR) is True
    assert is_role_at_least(WorkspaceRole.OWNER, WorkspaceRole.VIEWER) is True

    # Admin >= Editor and Viewer, but < Owner
    assert is_role_at_least(WorkspaceRole.ADMIN, WorkspaceRole.OWNER) is False
    assert is_role_at_least(WorkspaceRole.ADMIN, WorkspaceRole.EDITOR) is True
    assert is_role_at_least(WorkspaceRole.ADMIN, WorkspaceRole.VIEWER) is True

    # Editor >= Viewer, but < Admin
    assert is_role_at_least(WorkspaceRole.EDITOR, WorkspaceRole.ADMIN) is False
    assert is_role_at_least(WorkspaceRole.EDITOR, WorkspaceRole.VIEWER) is True

    # Viewer < Editor
    assert is_role_at_least(WorkspaceRole.VIEWER, WorkspaceRole.EDITOR) is False


def test_member_management_permissions():
    # Owner can manage Admin, Editor, Viewer
    assert can_manage_member(WorkspaceRole.OWNER, WorkspaceRole.ADMIN) is True
    assert can_manage_member(WorkspaceRole.OWNER, WorkspaceRole.EDITOR) is True
    assert can_manage_member(WorkspaceRole.OWNER, WorkspaceRole.VIEWER) is True

    # Admin can manage Editor and Viewer only
    assert can_manage_member(WorkspaceRole.ADMIN, WorkspaceRole.OWNER) is False
    assert can_manage_member(WorkspaceRole.ADMIN, WorkspaceRole.ADMIN) is False
    assert can_manage_member(WorkspaceRole.ADMIN, WorkspaceRole.EDITOR) is True
    assert can_manage_member(WorkspaceRole.ADMIN, WorkspaceRole.VIEWER) is True

    # Editor and Viewer cannot manage members
    assert can_manage_member(WorkspaceRole.EDITOR, WorkspaceRole.VIEWER) is False
    assert can_manage_member(WorkspaceRole.VIEWER, WorkspaceRole.VIEWER) is False


def test_invitation_role_permissions():
    # Cannot invite directly as Owner
    assert can_invite_role(WorkspaceRole.OWNER, WorkspaceRole.OWNER) is False
    assert can_invite_role(WorkspaceRole.ADMIN, WorkspaceRole.OWNER) is False

    # Owner can invite Admin, Editor, Viewer
    assert can_invite_role(WorkspaceRole.OWNER, WorkspaceRole.ADMIN) is True
    assert can_invite_role(WorkspaceRole.OWNER, WorkspaceRole.EDITOR) is True
    assert can_invite_role(WorkspaceRole.OWNER, WorkspaceRole.VIEWER) is True

    # Admin can invite Editor and Viewer, but cannot invite Admin
    assert can_invite_role(WorkspaceRole.ADMIN, WorkspaceRole.ADMIN) is False
    assert can_invite_role(WorkspaceRole.ADMIN, WorkspaceRole.EDITOR) is True
    assert can_invite_role(WorkspaceRole.ADMIN, WorkspaceRole.VIEWER) is True

    # Editor and Viewer cannot invite anyone
    assert can_invite_role(WorkspaceRole.EDITOR, WorkspaceRole.VIEWER) is False
    assert can_invite_role(WorkspaceRole.VIEWER, WorkspaceRole.VIEWER) is False
