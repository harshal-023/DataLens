"""MongoDB Connector for DataLens with BSON normalization and chunked streaming."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import pymongo
from bson import Decimal128, ObjectId

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectionAuthError,
    ConnectionTimeoutError,
    ConnectorError,
    QueryExecutionError,
    ResourceNotFoundError,
    SchemaDiscoveryError,
)


def normalize_bson(obj: Any) -> Any:
    """Recursively convert BSON-specific types into standard Python / JSON types."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal128):
        return float(obj.to_decimal())
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    if isinstance(obj, dict):
        return {k: normalize_bson(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_bson(item) for item in obj]
    return obj


class MongoDBConnector(BaseConnector):
    """Production MongoDB connector supporting connection testing, collection discovery, preview, and streaming."""

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        super().__init__(connection_id, config, credentials)
        self.uri = self.credentials.get("uri") or self.config.get("uri")
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 27017))
        self.database = self.config.get("database", "admin")
        self.user = self.credentials.get("username") or self.credentials.get("user")
        self.password = self.credentials.get("password")
        self.auth_source = self.config.get("auth_source", "admin")

    def _get_client(self) -> pymongo.MongoClient:
        try:
            if self.uri:
                client = pymongo.MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000,
                )
            else:
                client = pymongo.MongoClient(
                    host=self.host,
                    port=self.port,
                    username=self.user or None,
                    password=self.password or None,
                    authSource=self.auth_source if self.user else None,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000,
                )
            return client
        except pymongo.errors.ConfigurationError as e:
            raise ConnectionAuthError(f"MongoDB configuration/auth error: {str(e)}") from e
        except Exception as e:
            raise ConnectorError(f"Failed to initialize MongoDB client: {str(e)}") from e

    async def test_connection(self) -> dict[str, Any]:
        def _test():
            start = time.perf_counter()
            client = self._get_client()
            try:
                info = client.server_info()
                latency = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "status": "success",
                    "latency_ms": latency,
                    "message": "Successfully connected to MongoDB server.",
                    "server_version": info.get("version", "Unknown"),
                }
            except pymongo.errors.ServerSelectionTimeoutError as e:
                raise ConnectionTimeoutError(f"MongoDB connection timed out: {str(e)}") from e
            except pymongo.errors.OperationFailure as e:
                raise ConnectionAuthError(f"MongoDB auth failure: {str(e)}") from e
            finally:
                client.close()

        return await asyncio.to_thread(_test)

    async def discover(self) -> dict[str, Any]:
        def _discover():
            client = self._get_client()
            try:
                db_names = client.list_database_names()
                ignore_dbs = {"admin", "config", "local"}
                valid_dbs = [d for d in db_names if d not in ignore_dbs]

                active_db = self.database if self.database and self.database in db_names else (valid_dbs[0] if valid_dbs else self.database)

                collections_by_db: dict[str, list[dict[str, str]]] = {}
                if active_db:
                    cols = client[active_db].list_collection_names()
                    collections_by_db[active_db] = [{"name": c, "type": "COLLECTION"} for c in sorted(cols)]

                return {
                    "database": active_db,
                    "available_databases": valid_dbs,
                    "schemas": collections_by_db,
                    "total_tables": sum(len(v) for v in collections_by_db.values()),
                }
            finally:
                client.close()

        try:
            return await asyncio.to_thread(_discover)
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise SchemaDiscoveryError(f"Failed to discover MongoDB collections: {str(e)}") from e

    def _infer_type(self, val: Any) -> str:
        if isinstance(val, bool):
            return "BOOLEAN"
        elif isinstance(val, int):
            return "BIGINT"
        elif isinstance(val, float):
            return "DOUBLE"
        elif isinstance(val, (dict, list)):
            return "JSON"
        return "VARCHAR"

    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        preview_data = await self.preview(resource_path, limit=20)
        return preview_data.get("columns", [])

    async def preview(self, resource_path: str, limit: int = 100) -> dict[str, Any]:
        db_name = self.database
        coll_name = resource_path
        if "." in resource_path:
            db_name, coll_name = resource_path.split(".", 1)

        def _preview():
            client = self._get_client()
            try:
                db = client[db_name]
                if coll_name not in db.list_collection_names():
                    raise ResourceNotFoundError(f"Collection '{db_name}.{coll_name}' not found.")

                cursor = db[coll_name].find().limit(int(limit))
                raw_docs = [normalize_bson(doc) for doc in cursor]

                # Infer columns
                col_types: dict[str, str] = {}
                for doc in raw_docs:
                    for k, v in doc.items():
                        if k not in col_types or col_types[k] == "VARCHAR":
                            if v is not None:
                                col_types[k] = self._infer_type(v)

                columns = [
                    {
                        "name": col,
                        "type": col_types[col],
                        "nullable": True,
                        "is_primary_key": col == "_id",
                    }
                    for col in sorted(col_types.keys())
                ]

                return {
                    "resource": resource_path,
                    "columns": columns,
                    "rows": raw_docs,
                    "total_rows": len(raw_docs),
                }
            finally:
                client.close()

        try:
            return await asyncio.to_thread(_preview)
        except ResourceNotFoundError:
            raise
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise QueryExecutionError(f"Failed to preview MongoDB collection '{resource_path}': {str(e)}") from e

    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        db_name = self.database
        coll_name = resource_path
        if "." in resource_path:
            db_name, coll_name = resource_path.split(".", 1)

        client = await asyncio.to_thread(self._get_client)
        try:
            db = client[db_name]
            filter_query: dict[str, Any] = {}
            sort_field = None

            if watermark_col:
                sort_field = watermark_col
                if watermark_val is not None:
                    if watermark_col == "_id" and ObjectId.is_valid(str(watermark_val)):
                        filter_query["_id"] = {"$gt": ObjectId(str(watermark_val))}
                    else:
                        filter_query[watermark_col] = {"$gt": watermark_val}

            cursor = db[coll_name].find(filter_query)
            if sort_field:
                cursor = cursor.sort(sort_field, pymongo.ASCENDING)

            batch: list[dict[str, Any]] = []
            for doc in cursor:
                batch.append(normalize_bson(doc))
                if len(batch) >= chunk_size:
                    yield batch
                    batch = []

            if batch:
                yield batch
        finally:
            client.close()
