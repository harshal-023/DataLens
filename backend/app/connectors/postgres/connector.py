"""PostgreSQL Connector for DataLens."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import asyncpg

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectionAuthError,
    ConnectionTimeoutError,
    ConnectorError,
    QueryExecutionError,
    ResourceNotFoundError,
    SchemaDiscoveryError,
)


class PostgresConnector(BaseConnector):
    """Production PostgreSQL connector supporting pooling, discovery, preview, and streaming."""

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        super().__init__(connection_id, config, credentials)
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 5432))
        self.database = self.config.get("database", "postgres")
        self.ssl = self.config.get("ssl", False)
        self.user = self.credentials.get("username") or self.credentials.get("user", "postgres")
        self.password = self.credentials.get("password", "")
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            try:
                ssl_ctx = "require" if self.ssl is True else (self.ssl if isinstance(self.ssl, str) else None)
                self._pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    ssl=ssl_ctx,
                    min_size=1,
                    max_size=5,
                    command_timeout=60,
                    timeout=15,
                )
            except asyncpg.InvalidPasswordError as e:
                raise ConnectionAuthError(f"PostgreSQL authentication failed: {str(e)}") from e
            except (asyncpg.CannotConnectNowError, TimeoutError, OSError) as e:
                raise ConnectionTimeoutError(f"PostgreSQL connection timeout or unreachable: {str(e)}") from e
            except Exception as e:
                raise ConnectorError(f"Failed to connect to PostgreSQL: {str(e)}") from e
        return self._pool

    async def test_connection(self) -> dict[str, Any]:
        start = time.perf_counter()
        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                latency = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "status": "success",
                    "latency_ms": latency,
                    "message": "Successfully connected to PostgreSQL.",
                    "server_version": str(version),
                }
        except Exception as e:
            raise ConnectorError(f"PostgreSQL test query failed: {str(e)}") from e

    async def discover(self) -> dict[str, Any]:
        pool = await self._get_pool()
        query = """
            SELECT 
                table_schema,
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name;
        """
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(query)
                schemas: dict[str, list[dict[str, str]]] = {}
                for row in rows:
                    s = row["table_schema"]
                    t = row["table_name"]
                    kind = "VIEW" if "VIEW" in row["table_type"] else "TABLE"
                    if s not in schemas:
                        schemas[s] = []
                    schemas[s].append({"name": t, "type": kind})

                return {
                    "database": self.database,
                    "schemas": schemas,
                    "total_tables": sum(len(v) for v in schemas.values()),
                }
        except Exception as e:
            raise SchemaDiscoveryError(f"Failed to discover PostgreSQL tables: {str(e)}") from e

    def _parse_resource_path(self, resource_path: str) -> tuple[str, str]:
        parts = resource_path.split(".", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "public", parts[0]

    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        schema_name, table_name = self._parse_resource_path(resource_path)
        pool = await self._get_pool()
        cols_query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_pk
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.table_schema, kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.table_schema = pk.table_schema 
                AND c.table_name = pk.table_name 
                AND c.column_name = pk.column_name
            WHERE c.table_schema = $1 AND c.table_name = $2
            ORDER BY c.ordinal_position;
        """
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(cols_query, schema_name, table_name)
                if not rows:
                    raise ResourceNotFoundError(f"Table or view '{schema_name}.{table_name}' not found.")
                result = []
                for r in rows:
                    result.append({
                        "name": r["column_name"],
                        "type": r["data_type"].upper(),
                        "nullable": r["is_nullable"] == "YES",
                        "is_primary_key": r["is_pk"],
                        "default": r["column_default"],
                    })
                return result
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise SchemaDiscoveryError(f"Failed to inspect schema for '{resource_path}': {str(e)}") from e

    async def preview(self, resource_path: str, limit: int = 100) -> dict[str, Any]:
        schema_name, table_name = self._parse_resource_path(resource_path)
        schema = await self.get_schema(resource_path)
        safe_schema = schema_name.replace('"', '""')
        safe_table = table_name.replace('"', '""')
        query = f'SELECT * FROM "{safe_schema}"."{safe_table}" LIMIT {int(limit)}'

        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                records = await conn.fetch(query)
                rows = [dict(r) for r in records]
                # Serialize any non-standard values (e.g. UUID, datetime) to string/JSON-compatible format
                for row in rows:
                    for k, v in row.items():
                        if hasattr(v, "isoformat"):
                            row[k] = v.isoformat()
                        elif isinstance(v, (bytes, bytearray)):
                            row[k] = v.hex()

                return {
                    "resource": resource_path,
                    "columns": schema,
                    "rows": rows,
                    "total_rows": len(rows),
                }
        except Exception as e:
            raise QueryExecutionError(f"Failed to execute preview query on '{resource_path}': {str(e)}") from e

    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        schema_name, table_name = self._parse_resource_path(resource_path)
        safe_schema = schema_name.replace('"', '""')
        safe_table = table_name.replace('"', '""')

        where_clause = ""
        params: list[Any] = []
        if watermark_col:
            safe_wm = watermark_col.replace('"', '""')
            if watermark_val is not None:
                where_clause = f'WHERE "{safe_wm}" > $1'
                params.append(watermark_val)
            order_clause = f'ORDER BY "{safe_wm}" ASC'
        else:
            order_clause = ""

        query = f'SELECT * FROM "{safe_schema}"."{safe_table}" {where_clause} {order_clause}'.strip()

        pool = await self._get_pool()
        async with pool.acquire() as conn, conn.transaction():
            cur = await conn.cursor(query, *params)
            while True:
                rows = await cur.fetch(chunk_size)
                if not rows:
                    break
                batch = []
                for r in rows:
                    d = dict(r)
                    for k, v in d.items():
                        if hasattr(v, "isoformat"):
                            d[k] = v.isoformat()
                        elif isinstance(v, (bytes, bytearray)):
                            d[k] = v.hex()
                    batch.append(d)
                yield batch

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
