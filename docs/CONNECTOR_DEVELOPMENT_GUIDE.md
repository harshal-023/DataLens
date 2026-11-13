# Connector Development Guide

## Overview

DataLens features an extensible, unified connector architecture that decouples external protocol drivers from the internal storage, transformation, and analytical query engines. Every connector inherits from `BaseConnector` (`backend/app/connectors/base.py`) and is registered in the central `ConnectorRegistry` (`backend/app/connectors/registry.py`).

---

## 1. Connector Interface (`BaseConnector`)

Every connector must implement five core abstract methods and one optional resource cleanup lifecycle hook:

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

class BaseConnector(ABC):
    def __init__(
        self,
        connection_id: str,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
    ) -> None:
        self.connection_id = connection_id
        self.config = config or {}
        self.credentials = credentials or {}

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Ping target and return latency_ms, status, message, and server_version."""
        pass

    @abstractmethod
    async def discover(self) -> Dict[str, Any]:
        """Inspect and return available databases, schemas, tables, collections, or sheets."""
        pass

    @abstractmethod
    async def get_schema(self, resource_path: str) -> List[Dict[str, Any]]:
        """Return standardized column metadata for target resource."""
        pass

    @abstractmethod
    async def preview(self, resource_path: str, limit: int = 100) -> Dict[str, Any]:
        """Fetch sample records without persisting to disk."""
        pass

    @abstractmethod
    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: Optional[str] = None,
        watermark_val: Optional[Any] = None,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """Asynchronously yield batches of normalized row dictionaries."""
        pass

    async def close(self) -> None:
        """Release underlying client sessions, connection pools, or sockets."""
        return None
```

---

## 2. Standardized Type Normalization

Remote data types must be mapped into DataLens analytical types:

| Remote Type Family | DataLens Inferred Type | DuckDB / Parquet Mapped Type |
| :--- | :--- | :--- |
| `INT`, `BIGINT`, `SERIAL` | `BIGINT` | `BIGINT` |
| `FLOAT`, `DOUBLE`, `DECIMAL`, `NUMERIC` | `DOUBLE` | `DOUBLE` |
| `VARCHAR`, `TEXT`, `CHAR`, `STRING` | `VARCHAR` | `VARCHAR` |
| `TIMESTAMP`, `DATETIME`, `DATE` | `TIMESTAMP` | `TIMESTAMP_TZ` |
| `BOOLEAN`, `BOOL`, `BIT` | `BOOLEAN` | `BOOLEAN` |
| `JSON`, `JSONB`, `BSON`, Nested Dicts | `JSON` | `VARCHAR` (JSON-encoded) |

---

## 3. Registering a New Connector

To add a new data provider:

1. Create package under `backend/app/connectors/<provider>/`
2. Implement your connector class inheriting from `BaseConnector`
3. Register the connector in `ConnectorRegistry`:

```python
from app.connectors.registry import ConnectorRegistry
from app.connectors.snowflake.connector import SnowflakeConnector

ConnectorRegistry.register(
    source_type="snowflake",
    connector_cls=SnowflakeConnector,
    metadata={
        "type": "snowflake",
        "name": "Snowflake",
        "category": "Cloud Data Warehouse",
        "icon": "snowflake",
        "description": "Connect to Snowflake virtual warehouses with OAuth/keypair authentication.",
        "supports_watermark": True,
        "supports_ssl": True,
    }
)
```

---

## 4. Error Handling Hierarchy

All driver-specific exceptions must be caught and re-raised using the DataLens connector exception hierarchy from `app.connectors.exceptions`:

```
ConnectorError (Base)
├── ConnectionAuthError      # Bad credentials, token expired, invalid certificate
├── ConnectionTimeoutError   # Unreachable host, network timeout
├── ResourceNotFoundError    # Missing table, bucket, collection, sheet
├── QueryExecutionError      # Syntax error, permission denied on table
├── SSRFSecurityError        # Target resolved to loopback/private/link-local address
├── DataExtractionError      # Stream parsing or record deserialization failure
└── SchemaDiscoveryError     # Introspection failure
```

---

## 5. Streaming and Memory Safety Rules

1. **Unbuffered Streaming**: Never call `.fetchall()` on multi-million row datasets. Always use server-side cursors (`SSDictCursor` in MySQL, `conn.cursor()` inside a transaction in `asyncpg`, `.find()` cursor in PyMongo, or chunked ranges).
2. **Chunk Size**: Standard default chunk size is 5,000 to 10,000 records.
3. **Parquet Conversion**: The `ImportEngine` automatically consumes streaming batches and converts them into Snappy-compressed Parquet chunks on disk, preventing unbounded RAM consumption.

