from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend

# Global storage instance using configured root
storage: StorageBackend = LocalStorageBackend(storage_root=settings.STORAGE_ROOT)


def get_storage_backend() -> StorageBackend:
    return storage


__all__ = ["LocalStorageBackend", "StorageBackend", "get_storage_backend", "storage"]
