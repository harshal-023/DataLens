from app.db.session import get_db
from app.dependencies.auth import (
    get_current_user,
    get_current_workspace,
    require_active_user,
    require_workspace_role,
    verify_csrf,
)
from app.storage import StorageBackend, storage


def get_storage() -> StorageBackend:
    return storage


__all__ = [
    "StorageBackend",
    "get_current_user",
    "get_current_workspace",
    "get_db",
    "get_storage",
    "require_active_user",
    "require_workspace_role",
    "storage",
    "verify_csrf",
]
