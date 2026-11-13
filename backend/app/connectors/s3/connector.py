"""S3-Compatible Object Storage Connector for DataLens (AWS, MinIO, R2)."""

from __future__ import annotations

import asyncio
import io
import time
from collections.abc import AsyncIterator
from typing import Any

import boto3
import pyarrow.csv as pcsv
import pyarrow.parquet as pq
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectionAuthError,
    ConnectionTimeoutError,
    ConnectorError,
    QueryExecutionError,
    ResourceNotFoundError,
    SchemaDiscoveryError,
)


class S3Connector(BaseConnector):
    """Production S3 / S3-compatible connector supporting CSV and Parquet discovery, preview, and streaming."""

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        super().__init__(connection_id, config, credentials)
        self.bucket = self.config.get("bucket", "")
        self.region_name = self.config.get("region_name", "us-east-1")
        self.endpoint_url = self.config.get("endpoint_url")
        self.prefix = self.config.get("prefix", "")
        self.access_key = self.credentials.get("access_key_id") or self.credentials.get("aws_access_key_id")
        self.secret_key = self.credentials.get("secret_access_key") or self.credentials.get("aws_secret_access_key")
        self.session_token = self.credentials.get("session_token") or self.credentials.get("aws_session_token")

    def _get_client(self):
        try:
            botocore_cfg = Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=30,
            )
            return boto3.client(
                "s3",
                region_name=self.region_name,
                endpoint_url=self.endpoint_url or None,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                aws_session_token=self.session_token,
                config=botocore_cfg,
            )
        except Exception as e:
            raise ConnectorError(f"Failed to create S3 client: {str(e)}") from e

    async def test_connection(self) -> dict[str, Any]:
        def _test():
            start = time.perf_counter()
            client = self._get_client()
            try:
                if self.bucket:
                    client.head_bucket(Bucket=self.bucket)
                    msg = f"Successfully verified access to S3 bucket '{self.bucket}'."
                else:
                    client.list_buckets()
                    msg = "Successfully authenticated with S3 service."
                latency = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "status": "success",
                    "latency_ms": latency,
                    "message": msg,
                    "server_version": "S3-Compatible API",
                }
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("403", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
                    raise ConnectionAuthError(f"S3 authentication failed: {str(e)}") from e
                elif code in ("404", "NoSuchBucket"):
                    raise ResourceNotFoundError(f"S3 bucket '{self.bucket}' does not exist.") from e
                raise ConnectorError(f"S3 client error: {str(e)}") from e
            except EndpointConnectionError as e:
                raise ConnectionTimeoutError(f"Cannot reach S3 endpoint: {str(e)}") from e

        return await asyncio.to_thread(_test)

    async def discover(self) -> dict[str, Any]:
        def _discover():
            client = self._get_client()
            try:
                available_buckets = []
                try:
                    res = client.list_buckets()
                    available_buckets = [b["Name"] for b in res.get("Buckets", [])]
                except Exception:
                    pass

                target_bucket = self.bucket or (available_buckets[0] if available_buckets else "")
                if not target_bucket:
                    raise ResourceNotFoundError("No S3 bucket specified or accessible.")

                objects_by_type: dict[str, list[dict[str, Any]]] = {"files": []}
                paginator = client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=target_bucket, Prefix=self.prefix, MaxKeys=500):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        if key.endswith("/") or key.startswith("."):
                            continue
                        ext = key.split(".")[-1].lower() if "." in key else ""
                        if ext in ("csv", "tsv", "parquet", "json"):
                            objects_by_type["files"].append({
                                "name": key,
                                "size_bytes": obj["Size"],
                                "last_modified": obj["LastModified"].isoformat(),
                                "type": ext.upper(),
                            })

                return {
                    "bucket": target_bucket,
                    "available_buckets": available_buckets,
                    "schemas": objects_by_type,
                    "total_tables": len(objects_by_type["files"]),
                }
            except ClientError as e:
                raise SchemaDiscoveryError(f"Failed to list S3 objects: {str(e)}") from e

        return await asyncio.to_thread(_discover)

    def _infer_arrow_type(self, arrow_type) -> str:
        s = str(arrow_type).lower()
        if "int" in s:
            return "BIGINT"
        elif "float" in s or "double" in s or "decimal" in s:
            return "DOUBLE"
        elif "bool" in s:
            return "BOOLEAN"
        elif "timestamp" in s or "date" in s:
            return "TIMESTAMP"
        return "VARCHAR"

    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        preview_data = await self.preview(resource_path, limit=10)
        return preview_data.get("columns", [])

    async def preview(self, resource_path: str, limit: int = 100) -> dict[str, Any]:
        bucket = self.bucket
        key = resource_path
        if "/" in resource_path and not self.bucket:
            bucket, key = resource_path.split("/", 1)

        def _preview():
            client = self._get_client()
            try:
                ext = key.split(".")[-1].lower() if "." in key else "csv"
                if ext == "parquet":
                    # Read parquet header/bytes
                    resp = client.get_object(Bucket=bucket, Key=key)
                    body_bytes = resp["Body"].read()
                    pf = pq.ParquetFile(io.BytesIO(body_bytes))
                    arrow_schema = pf.schema_arrow
                    table = pf.read_row_group(0)
                    if table.num_rows > limit:
                        table = table.slice(0, limit)
                    pydict = table.to_pylist()
                    columns = [
                        {
                            "name": field.name,
                            "type": self._infer_arrow_type(field.type),
                            "nullable": field.nullable,
                            "is_primary_key": False,
                        }
                        for field in arrow_schema
                    ]
                    return {
                        "resource": key,
                        "columns": columns,
                        "rows": pydict,
                        "total_rows": len(pydict),
                    }
                else:
                    # CSV or delimited
                    resp = client.get_object(Bucket=bucket, Key=key, Range="bytes=0-1048576")  # first 1MB
                    body = resp["Body"].read()
                    table = pcsv.read_csv(io.BytesIO(body))
                    if table.num_rows > limit:
                        table = table.slice(0, limit)
                    pydict = table.to_pylist()
                    columns = [
                        {
                            "name": field.name,
                            "type": self._infer_arrow_type(field.type),
                            "nullable": field.nullable,
                            "is_primary_key": False,
                        }
                        for field in table.schema
                    ]
                    return {
                        "resource": key,
                        "columns": columns,
                        "rows": pydict,
                        "total_rows": len(pydict),
                    }
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("NoSuchKey", "404"):
                    raise ResourceNotFoundError(f"S3 key '{key}' not found in bucket '{bucket}'.")
                raise QueryExecutionError(f"S3 get_object failed: {str(e)}") from e

        return await asyncio.to_thread(_preview)

    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        bucket = self.bucket
        key = resource_path
        if "/" in resource_path and not self.bucket:
            bucket, key = resource_path.split("/", 1)

        def _get_stream():
            client = self._get_client()
            resp = client.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read()

        file_bytes = await asyncio.to_thread(_get_stream)
        ext = key.split(".")[-1].lower() if "." in key else "csv"

        if ext == "parquet":
            pf = pq.ParquetFile(io.BytesIO(file_bytes))
            for i in range(pf.num_row_groups):
                rg = pf.read_row_group(i)
                records = rg.to_pylist()
                # Yield in chunks
                for start_idx in range(0, len(records), chunk_size):
                    batch = records[start_idx : start_idx + chunk_size]
                    if watermark_col and watermark_val is not None:
                        batch = [r for r in batch if r.get(watermark_col) is not None and str(r.get(watermark_col)) > str(watermark_val)]
                    if batch:
                        yield batch
        else:
            table = pcsv.read_csv(io.BytesIO(file_bytes))
            records = table.to_pylist()
            for start_idx in range(0, len(records), chunk_size):
                batch = records[start_idx : start_idx + chunk_size]
                if watermark_col and watermark_val is not None:
                    batch = [r for r in batch if r.get(watermark_col) is not None and str(r.get(watermark_col)) > str(watermark_val)]
                if batch:
                    yield batch
