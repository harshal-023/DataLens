from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


# Role priority ranking for hierarchy comparisons
ROLE_HIERARCHY: dict[str, int] = {
    WorkspaceRole.OWNER.value: 40,
    WorkspaceRole.ADMIN.value: 30,
    WorkspaceRole.EDITOR.value: 20,
    WorkspaceRole.VIEWER.value: 10,
}


def normalize_role(role: str) -> str:
    """Normalizes role strings to lowercase standard values."""
    cleaned = role.strip().lower()
    if cleaned in ("owner", "admin", "editor", "viewer"):
        return cleaned
    raise ValueError(f"Invalid workspace role: '{role}'. Must be owner, admin, editor, or viewer.")


def is_role_at_least(user_role: str, minimum_required_role: str) -> bool:
    """Checks if user's role has at least the privilege level of minimum_required_role."""
    user_level = ROLE_HIERARCHY.get(normalize_role(user_role), 0)
    required_level = ROLE_HIERARCHY.get(normalize_role(minimum_required_role), 0)
    return user_level >= required_level


def can_manage_member(actor_role: str, target_role: str) -> bool:
    """
    Determines if actor can update or remove a member with target_role.
    - Owner can manage anyone (except removing the sole Owner).
    - Admin can manage Editor and Viewer, but cannot manage Owner or other Admins.
    - Editor and Viewer cannot manage members.
    """
    actor_norm = normalize_role(actor_role)
    target_norm = normalize_role(target_role)

    if actor_norm == WorkspaceRole.OWNER.value:
        return True
    if actor_norm == WorkspaceRole.ADMIN.value:
        return target_norm in (WorkspaceRole.EDITOR.value, WorkspaceRole.VIEWER.value)
    return False


def can_invite_role(actor_role: str, target_role_to_assign: str) -> bool:
    """
    Checks if actor can issue an invitation for the given target role.
    No one can directly invite as Owner (ownership must be transferred).
    Admin can invite Editor or Viewer.
    Owner can invite Admin, Editor, or Viewer.
    """
    actor_norm = normalize_role(actor_role)
    target_norm = normalize_role(target_role_to_assign)

    if target_norm == WorkspaceRole.OWNER.value:
        return False  # Owner role cannot be granted via invitation

    if actor_norm == WorkspaceRole.OWNER.value:
        return target_norm in (WorkspaceRole.ADMIN.value, WorkspaceRole.EDITOR.value, WorkspaceRole.VIEWER.value)
    if actor_norm == WorkspaceRole.ADMIN.value:
        return target_norm in (WorkspaceRole.EDITOR.value, WorkspaceRole.VIEWER.value)
    return False
