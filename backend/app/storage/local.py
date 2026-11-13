import asyncio
import os
from pathlib import Path

from app.core.exceptions import StorageException
from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage adapter with robust path-traversal prevention.
    Stores files securely under a configured storage root directory.
    Uses asyncio.to_thread for non-blocking I/O with standard library.
    """

    def __init__(self, storage_root: str):
        self.storage_root_path = Path(storage_root).resolve()
        # Ensure root directory exists
        self.storage_root_path.mkdir(parents=True, exist_ok=True)
        self.storage_root_abs = str(self.storage_root_path)

    def _resolve_safe_path(self, key: str) -> Path:
        """
        Resolves the key against the root path and validates against path traversal.
        Raises StorageException(code='PATH_TRAVERSAL') if an escape is attempted.
        """
        if not key or not key.strip():
            raise StorageException(message="Storage key cannot be empty.", code="BAD_REQUEST")

        # Resolve candidate path
        candidate = (self.storage_root_path / key).resolve()
        candidate_str = str(candidate)

        # Check that candidate path is strictly within the storage root
        try:
            common = os.path.commonpath([self.storage_root_abs, candidate_str])
            if common != self.storage_root_abs:
                raise StorageException(
                    message="Security violation: Path traversal attempt detected.",
                    code="PATH_TRAVERSAL",
                    details={"attempted_key": key},
                )
        except ValueError:
            # Different drives on Windows will raise ValueError in commonpath
            raise StorageException(
                message="Security violation: Invalid storage drive location.",
                code="PATH_TRAVERSAL",
                details={"attempted_key": key},
            )

        return candidate

    async def save_file(self, key: str, data: bytes) -> str:
        safe_path = self._resolve_safe_path(key)
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        def _write():
            safe_path.write_bytes(data)

        try:
            await asyncio.to_thread(_write)
            return key
        except Exception as e:
            raise StorageException(
                message=f"Failed to write file to local storage: {e!s}",
                code="STORAGE_WRITE_ERROR",
                details={"key": key},
            )

    async def read_file(self, key: str) -> bytes:
        safe_path = self._resolve_safe_path(key)
        if not safe_path.is_file():
            raise StorageException(
                message=f"File not found for key: {key}",
                code="STORAGE_NOT_FOUND",
                details={"key": key},
            )

        try:
            return await asyncio.to_thread(safe_path.read_bytes)
        except Exception as e:
            raise StorageException(
                message=f"Failed to read file from local storage: {e!s}",
                code="STORAGE_READ_ERROR",
                details={"key": key},
            )

    async def delete_file(self, key: str) -> bool:
        safe_path = self._resolve_safe_path(key)
        if safe_path.is_file():
            try:
                await asyncio.to_thread(safe_path.unlink)
                return True
            except Exception as e:
                raise StorageException(
                    message=f"Failed to delete file from local storage: {e!s}",
                    code="STORAGE_DELETE_ERROR",
                    details={"key": key},
                )
        return False

    async def file_exists(self, key: str) -> bool:
        safe_path = self._resolve_safe_path(key)
        return safe_path.is_file()
