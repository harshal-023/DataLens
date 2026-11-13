"""MySQL Connector for DataLens."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import pymysql
import pymysql.cursors

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectionAuthError,
    ConnectionTimeoutError,
    ConnectorError,
    QueryExecutionError,
    ResourceNotFoundError,
    SchemaDiscoveryError,
)


class MySQLConnector(BaseConnector):
    """Production MySQL connector supporting connection testing, discovery, preview, and streaming."""

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        super().__init__(connection_id, config, credentials)
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 3306))
        self.database = self.config.get("database", "")
        self.charset = self.config.get("charset", "utf8mb4")
        self.ssl_enabled = bool(self.config.get("ssl", False))
        self.user = self.credentials.get("username") or self.credentials.get("user", "root")
        self.password = self.credentials.get("password", "")

    def _get_connection(self) -> pymysql.Connection:
        ssl_arg = {"ssl": {}} if self.ssl_enabled else None
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database or None,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=15,
                read_timeout=60,
                write_timeout=60,
                ssl=ssl_arg.get("ssl") if ssl_arg else None,
            )
            return conn
        except pymysql.err.OperationalError as e:
            code = e.args[0] if len(e.args) > 0 else 0
            if code in (1045, 1044):  # Access denied
                raise ConnectionAuthError(f"MySQL authentication failed: {str(e)}") from e
            elif code in (2003, 2002, 2006, 2013):  # Can't connect to server / timeout
                raise ConnectionTimeoutError(f"MySQL connection timeout or unreachable: {str(e)}") from e
            raise ConnectorError(f"Failed to connect to MySQL: {str(e)}") from e
        except Exception as e:
            raise ConnectorError(f"MySQL error: {str(e)}") from e

    async def test_connection(self) -> dict[str, Any]:
        def _test():
            start = time.perf_counter()
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT VERSION() AS ver")
                    row = cursor.fetchone()
                    version = row["ver"] if row else "Unknown"
                latency = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "status": "success",
                    "latency_ms": latency,
                    "message": "Successfully connected to MySQL.",
                    "server_version": str(version),
                }
            finally:
                conn.close()

        return await asyncio.to_thread(_test)

    async def discover(self) -> dict[str, Any]:
        def _discover():
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # Discover databases if none specified or all available
                    cursor.execute("SHOW DATABASES;")
                    dbs = [r[list(r.keys())[0]] for r in cursor.fetchall()]
                    ignore_dbs = {"information_schema", "mysql", "performance_schema", "sys"}
                    valid_dbs = [d for d in dbs if d not in ignore_dbs]

                    active_db = self.database if self.database and self.database in valid_dbs else (valid_dbs[0] if valid_dbs else "")

                    tables_by_db: dict[str, list[dict[str, str]]] = {}
                    if active_db:
                        cursor.execute(
                            """
                            SELECT TABLE_NAME, TABLE_TYPE 
                            FROM information_schema.TABLES 
                            WHERE TABLE_SCHEMA = %s
                            ORDER BY TABLE_NAME;
                            """,
                            (active_db,),
                        )
                        rows = cursor.fetchall()
                        tables_by_db[active_db] = [
                            {
                                "name": r["TABLE_NAME"],
                                "type": "VIEW" if "VIEW" in r["TABLE_TYPE"] else "TABLE",
                            }
                            for r in rows
                        ]

                    return {
                        "database": active_db,
                        "available_databases": valid_dbs,
                        "schemas": tables_by_db,
                        "total_tables": sum(len(v) for v in tables_by_db.values()),
                    }
            finally:
                conn.close()

        try:
            return await asyncio.to_thread(_discover)
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise SchemaDiscoveryError(f"Failed to discover MySQL tables: {str(e)}") from e

    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        db_name = self.database
        table_name = resource_path
        if "." in resource_path:
            db_name, table_name = resource_path.split(".", 1)

        def _get_schema():
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            COLUMN_NAME,
                            DATA_TYPE,
                            IS_NULLABLE,
                            COLUMN_KEY,
                            COLUMN_DEFAULT
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION;
                        """,
                        (db_name, table_name),
                    )
                    rows = cursor.fetchall()
                    if not rows:
                        raise ResourceNotFoundError(f"MySQL table '{db_name}.{table_name}' not found.")

                    result = []
                    for r in rows:
                        result.append({
                            "name": r["COLUMN_NAME"],
                            "type": r["DATA_TYPE"].upper(),
                            "nullable": r["IS_NULLABLE"] == "YES",
                            "is_primary_key": r["COLUMN_KEY"] == "PRI",
                            "default": r["COLUMN_DEFAULT"],
                        })
                    return result
            finally:
                conn.close()

        try:
            return await asyncio.to_thread(_get_schema)
        except ResourceNotFoundError:
            raise
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise SchemaDiscoveryError(f"Failed to inspect MySQL schema for '{resource_path}': {str(e)}") from e

    async def preview(self, resource_path: str, limit: int = 100) -> dict[str, Any]:
        db_name = self.database
        table_name = resource_path
        if "." in resource_path:
            db_name, table_name = resource_path.split(".", 1)

        schema = await self.get_schema(resource_path)

        def _preview():
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    safe_db = db_name.replace("`", "``")
                    safe_table = table_name.replace("`", "``")
                    query = f"SELECT * FROM `{safe_db}`.`{safe_table}` LIMIT %s"
                    cursor.execute(query, (int(limit),))
                    rows = cursor.fetchall()
                    # Sanitize dates / dec / bytes
                    clean_rows = []
                    for r in rows:
                        d = dict(r)
                        for k, v in d.items():
                            if hasattr(v, "isoformat"):
                                d[k] = v.isoformat()
                            elif isinstance(v, (bytes, bytearray)):
                                d[k] = v.hex()
                            elif hasattr(v, "__float__"):
                                d[k] = float(v)
                        clean_rows.append(d)
                    return {
                        "resource": resource_path,
                        "columns": schema,
                        "rows": clean_rows,
                        "total_rows": len(clean_rows),
                    }
            finally:
                conn.close()

        try:
            return await asyncio.to_thread(_preview)
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise QueryExecutionError(f"Failed to preview MySQL table '{resource_path}': {str(e)}") from e

    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        db_name = self.database
        table_name = resource_path
        if "." in resource_path:
            db_name, table_name = resource_path.split(".", 1)

        safe_db = db_name.replace("`", "``")
        safe_table = table_name.replace("`", "``")

        where_clause = ""
        params: list[Any] = []
        if watermark_col:
            safe_wm = watermark_col.replace("`", "``")
            if watermark_val is not None:
                where_clause = f"WHERE `{safe_wm}` > %s"
                params.append(watermark_val)
            order_clause = f"ORDER BY `{safe_wm}` ASC"
        else:
            order_clause = ""

        query = f"SELECT * FROM `{safe_db}`.`{safe_table}` {where_clause} {order_clause}".strip()

        # Stream using SSDictCursor (server-side unbuffered cursor)
        conn = await asyncio.to_thread(self._get_connection)
        try:
            cursor = pymysql.cursors.SSDictCursor(conn)
            await asyncio.to_thread(cursor.execute, query, tuple(params) if params else None)

            while True:
                rows = await asyncio.to_thread(cursor.fetchmany, chunk_size)
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
                        elif hasattr(v, "__float__"):
                            d[k] = float(v)
                    batch.append(d)
                yield batch
        finally:
            cursor.close()
            conn.close()
