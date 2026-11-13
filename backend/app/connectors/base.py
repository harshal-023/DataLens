"""Abstract Base Class for DataLens External Data Source Connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class BaseConnector(ABC):
    """
    Abstract interface for all DataLens data source connectors.
    Provides standardized methods for testing, discovery, preview,
    and chunked streaming ingestion.
    """

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        self.connection_id = connection_id
        self.config = config or {}
        self.credentials = credentials or {}

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """
        Verify connectivity and credentials against the external source.
        Returns a dict containing:
          - status: "success" | "failed"
          - latency_ms: float
          - message: str
          - server_version: Optional[str]
        Raises ConnectorError on failure.
        """
        pass

    @abstractmethod
    async def discover(self) -> dict[str, Any]:
        """
        Discover available resources in the source:
        - Relational: databases, schemas, tables, views
        - MongoDB: databases, collections
        - Google Sheets: spreadsheets, sheets/tabs
        - S3: buckets, object keys/prefixes
        - REST API: endpoints/resources configured
        """
        pass

    @abstractmethod
    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        """
        Retrieve schema for a specific table, collection, sheet, or object.
        Returns list of column dicts:
          - name: str
          - type: str (normalized string, e.g. "VARCHAR", "INT", "FLOAT", "TIMESTAMP", "BOOLEAN", "JSON")
          - nullable: bool
          - is_primary_key: bool
        """
        pass

    @abstractmethod
    async def preview(
        self,
        resource_path: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Fetch sample rows/documents without writing to disk.
        Returns:
          - columns: List[Dict[str, Any]]
          - rows: List[Dict[str, Any]]
          - total_rows: int
        """
        pass

    @abstractmethod
    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Asynchronously stream data in chunks from the target resource.
        Supports optional watermark column and value for incremental extraction.
        Yields lists of row dictionaries.
        """
        pass

    async def close(self) -> None:
        """Release any open connection pools, sessions, or sockets."""
        return None
