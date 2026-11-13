import re
import uuid
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """
    Abstract interface for blob/file persistence.
    Designed for pluggable adapters: LocalStorageBackend, S3StorageBackend, etc.
    """

    @abstractmethod
    async def save_file(self, key: str, data: bytes) -> str:
        """Saves binary data under the given storage key and returns the key."""

    @abstractmethod
    async def read_file(self, key: str) -> bytes:
        """Reads binary data from storage by key. Raises StorageException if not found."""

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Deletes a file by key. Returns True if deleted, False if not present."""

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """Checks if a file exists under the given key."""

    def generate_storage_key(self, prefix: str = "", extension: str = "") -> str:
        """
        Generates a secure UUID-based storage key.
        Never trusts raw client-supplied filenames.
        """
        unique_id = uuid.uuid4().hex
        # Extract only the leading alphanumeric extension segment
        match = re.match(r"^\.?([a-zA-Z0-9]{1,10})", extension.strip())
        clean_ext = match.group(1).lower() if match else ""
        ext_suffix = f".{clean_ext}" if clean_ext else ""

        if prefix:
            clean_prefix = re.sub(r"[^a-zA-Z0-9_-]", "", prefix).strip("/")
            return f"{clean_prefix}/{unique_id}{ext_suffix}"
        return f"{unique_id}{ext_suffix}"
