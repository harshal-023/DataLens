import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataLensException


@dataclass
class ColumnMeta:
    name: str
    inferred_type: str  # "integer" | "float" | "boolean" | "date" | "string"
    sample_values: list[Any] = field(default_factory=list)
    null_count: int = 0


@dataclass
class ProcessingResult:
    row_count: int
    column_count: int
    columns: list[ColumnMeta]
    schema_metadata: dict[str, Any]
    parquet_parts: list[str]
    manifest_key: str
    checksum: str
    warnings: list[str] = field(default_factory=list)
    invalid_row_count: int = 0
    available_worksheets: list[str] = field(default_factory=list)
    selected_worksheet: str | None = None


class DatasetProcessor:
    """
    Parses CSV and Excel data, writes normalized records into partitioned Parquet files,
    and produces metadata and schema summaries.
    """

    CHUNK_SIZE = 5000

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sanitize_column_name(name: str, index: int, seen: dict[str, int]) -> str:
        clean = (name or "").strip()
        if not clean:
            clean = f"column_{index + 1}"
        # Keep clean alphanumeric and underscores
        clean = re.sub(r"[^\w\s-]", "", clean).strip()
        clean = re.sub(r"[-\s]+", "_", clean)
        if not clean:
            clean = f"col_{index + 1}"

        lower_clean = clean.lower()
        if lower_clean in seen:
            seen[lower_clean] += 1
            clean = f"{clean}_{seen[lower_clean]}"
        else:
            seen[lower_clean] = 0
        return clean

    @classmethod
    def infer_and_coerce_value(cls, val: Any) -> tuple[Any, str]:
        if val is None:
            return None, "null"

        if isinstance(val, (datetime, date)):
            return val.isoformat(), "date"

        if isinstance(val, bool):
            return val, "boolean"

        if isinstance(val, (int, float)):
            if isinstance(val, float) and val.is_integer():
                return int(val), "integer"
            return float(val), "float"

        s = str(val).strip()
        if s == "" or s.lower() in ("null", "none", "nan", "n/a", "na"):
            return None, "null"

        # Check boolean
        if s.lower() in ("true", "false"):
            return s.lower() == "true", "boolean"

        # Check currency / stripped numeric (e.g. "$1,200.50", "€450", "₹1200")
        clean_numeric = re.sub(r"^[$\€\£\₹\¥\s]+|[,\s]+", "", s)
        if re.match(r"^-?\d+$", clean_numeric):
            try:
                return int(clean_numeric), "integer"
            except (ValueError, OverflowError):
                pass
        if re.match(r"^-?\d+\.\d+$", clean_numeric):
            try:
                return float(clean_numeric), "float"
            except ValueError:
                pass

        # Check ISO / common date formats
        if re.match(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2})?", s):
            return s, "date"

        return s, "string"

    @classmethod
    def process_csv(
        cls,
        data: bytes,
        storage_root: Path,
        relative_processed_dir: str,
    ) -> ProcessingResult:
        checksum = cls.compute_sha256(data)
        warnings: list[str] = []
        invalid_row_count = 0

        # Decode UTF-8 with BOM support
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
                warnings.append("File was decoded using latin-1 fallback instead of UTF-8.")
            except Exception as e:
                raise DataLensException(
                    f"Unable to decode CSV file: {e!s}",
                    code="DECODE_ERROR",
                )

        reader = csv.reader(io.StringIO(text))
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise DataLensException("CSV file is empty.", code="EMPTY_FILE")

        if not raw_headers:
            raise DataLensException("CSV file has no headers.", code="EMPTY_HEADERS")

        seen_headers: dict[str, int] = {}
        headers = [cls.sanitize_column_name(h, i, seen_headers) for i, h in enumerate(raw_headers)]
        num_cols = len(headers)

        rows_buffer: list[dict[str, Any]] = []
        col_type_votes: dict[str, dict[str, int]] = {h: {} for h in headers}
        col_null_counts: dict[str, int] = {h: 0 for h in headers}
        sample_values: dict[str, list[Any]] = {h: [] for h in headers}

        parts: list[str] = []
        part_idx = 1
        total_rows = 0

        processed_dir_path = storage_root / relative_processed_dir
        processed_dir_path.mkdir(parents=True, exist_ok=True)

        for _line_idx, raw_row in enumerate(reader, start=2):
            if not raw_row or all(cell.strip() == "" for cell in raw_row):
                continue  # skip completely empty rows

            if len(raw_row) != num_cols:
                invalid_row_count += 1
                if len(raw_row) < num_cols:
                    raw_row = raw_row + [""] * (num_cols - len(raw_row))
                else:
                    raw_row = raw_row[:num_cols]

            row_dict: dict[str, Any] = {}
            for col_idx, col_name in enumerate(headers):
                cell_val = raw_row[col_idx]
                coerced, detected_type = cls.infer_and_coerce_value(cell_val)
                row_dict[col_name] = coerced

                if coerced is None:
                    col_null_counts[col_name] += 1
                else:
                    col_type_votes[col_name][detected_type] = col_type_votes[col_name].get(detected_type, 0) + 1
                    if len(sample_values[col_name]) < 5:
                        sample_values[col_name].append(coerced)

            rows_buffer.append(row_dict)
            total_rows += 1

            if len(rows_buffer) >= cls.CHUNK_SIZE:
                part_filename = f"part-{part_idx:05d}.parquet"
                cls._write_parquet_part(rows_buffer, headers, processed_dir_path / part_filename)
                parts.append(f"{relative_processed_dir}/{part_filename}")
                part_idx += 1
                rows_buffer.clear()

        if rows_buffer or total_rows == 0:
            part_filename = f"part-{part_idx:05d}.parquet"
            cls._write_parquet_part(rows_buffer, headers, processed_dir_path / part_filename)
            parts.append(f"{relative_processed_dir}/{part_filename}")
            rows_buffer.clear()

        # Finalize column metadata
        columns: list[ColumnMeta] = []
        for h in headers:
            votes = col_type_votes[h]
            if not votes:
                final_type = "string"
            else:
                # Resolve dominant type (preference: float > integer > date > boolean > string)
                sorted_types = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)
                final_type = sorted_types[0][0]
                if final_type == "null":
                    final_type = "string"
            columns.append(
                ColumnMeta(
                    name=h,
                    inferred_type=final_type,
                    sample_values=sample_values[h],
                    null_count=col_null_counts[h],
                )
            )

        if invalid_row_count > 0:
            warnings.append(f"{invalid_row_count} rows had inconsistent column counts and were padded/truncated.")

        # Create manifest
        manifest_data = {
            "parts": parts,
            "row_count": total_rows,
            "column_count": num_cols,
            "columns": [
                {
                    "name": c.name,
                    "inferred_type": c.inferred_type,
                    "null_count": c.null_count,
                    "sample_values": [str(v) for v in c.sample_values],
                }
                for c in columns
            ],
            "checksum": checksum,
            "warnings": warnings,
            "created_at": datetime.now().isoformat(),
        }
        manifest_key = f"{relative_processed_dir}/manifest.json"
        manifest_path = storage_root / manifest_key
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        schema_metadata = {
            "columns": manifest_data["columns"],
            "row_count": total_rows,
            "column_count": num_cols,
            "manifest_key": manifest_key,
        }

        return ProcessingResult(
            row_count=total_rows,
            column_count=num_cols,
            columns=columns,
            schema_metadata=schema_metadata,
            parquet_parts=parts,
            manifest_key=manifest_key,
            checksum=checksum,
            warnings=warnings,
            invalid_row_count=invalid_row_count,
        )

    @classmethod
    def process_excel(
        cls,
        data: bytes,
        storage_root: Path,
        relative_processed_dir: str,
        selected_worksheet: str | None = None,
    ) -> ProcessingResult:
        checksum = cls.compute_sha256(data)
        warnings: list[str] = []
        invalid_row_count = 0

        # Load workbook in read_only and data_only mode
        try:
            wb = openpyxl.load_workbook(
                io.BytesIO(data),
                read_only=True,
                data_only=True,  # cached formula results
            )
        except Exception as e:
            raise DataLensException(
                f"Failed to parse Excel workbook: {e!s}. Ensure the file is not encrypted or password-protected.",
                code="EXCEL_PARSE_ERROR",
            )

        available_sheets = wb.sheetnames
        if not available_sheets:
            raise DataLensException("Excel workbook contains no sheets.", code="EMPTY_FILE")

        active_sheet_name = selected_worksheet if selected_worksheet in available_sheets else available_sheets[0]
        sheet = wb[active_sheet_name]

        rows_iter = sheet.iter_rows(values_only=True)
        raw_headers = None
        for r in rows_iter:
            if r and any(c is not None and str(c).strip() != "" for c in r):
                raw_headers = [str(c or "").strip() for c in r]
                break

        if not raw_headers:
            raise DataLensException(f"Worksheet '{active_sheet_name}' is empty.", code="EMPTY_SHEET")

        seen_headers: dict[str, int] = {}
        headers = [cls.sanitize_column_name(h, i, seen_headers) for i, h in enumerate(raw_headers)]
        num_cols = len(headers)

        rows_buffer: list[dict[str, Any]] = []
        col_type_votes: dict[str, dict[str, int]] = {h: {} for h in headers}
        col_null_counts: dict[str, int] = {h: 0 for h in headers}
        sample_values: dict[str, list[Any]] = {h: [] for h in headers}

        parts: list[str] = []
        part_idx = 1
        total_rows = 0

        processed_dir_path = storage_root / relative_processed_dir
        processed_dir_path.mkdir(parents=True, exist_ok=True)

        for raw_row in rows_iter:
            if not raw_row or all(c is None or str(c).strip() == "" for c in raw_row):
                continue

            row_list = list(raw_row)
            if len(row_list) != num_cols:
                invalid_row_count += 1
                if len(row_list) < num_cols:
                    row_list = row_list + [None] * (num_cols - len(row_list))
                else:
                    row_list = row_list[:num_cols]

            row_dict: dict[str, Any] = {}
            for col_idx, col_name in enumerate(headers):
                cell_val = row_list[col_idx]
                coerced, detected_type = cls.infer_and_coerce_value(cell_val)
                row_dict[col_name] = coerced

                if coerced is None:
                    col_null_counts[col_name] += 1
                else:
                    col_type_votes[col_name][detected_type] = col_type_votes[col_name].get(detected_type, 0) + 1
                    if len(sample_values[col_name]) < 5:
                        sample_values[col_name].append(coerced)

            rows_buffer.append(row_dict)
            total_rows += 1

            if len(rows_buffer) >= cls.CHUNK_SIZE:
                part_filename = f"part-{part_idx:05d}.parquet"
                cls._write_parquet_part(rows_buffer, headers, processed_dir_path / part_filename)
                parts.append(f"{relative_processed_dir}/{part_filename}")
                part_idx += 1
                rows_buffer.clear()

        wb.close()

        if rows_buffer or total_rows == 0:
            part_filename = f"part-{part_idx:05d}.parquet"
            cls._write_parquet_part(rows_buffer, headers, processed_dir_path / part_filename)
            parts.append(f"{relative_processed_dir}/{part_filename}")
            rows_buffer.clear()

        columns: list[ColumnMeta] = []
        for h in headers:
            votes = col_type_votes[h]
            final_type = "string" if not votes else sorted(votes.items(), key=lambda kv: kv[1], reverse=True)[0][0]
            if final_type == "null":
                final_type = "string"
            columns.append(
                ColumnMeta(
                    name=h,
                    inferred_type=final_type,
                    sample_values=sample_values[h],
                    null_count=col_null_counts[h],
                )
            )

        manifest_data = {
            "parts": parts,
            "row_count": total_rows,
            "column_count": num_cols,
            "columns": [
                {
                    "name": c.name,
                    "inferred_type": c.inferred_type,
                    "null_count": c.null_count,
                    "sample_values": [str(v) for v in c.sample_values],
                }
                for c in columns
            ],
            "checksum": checksum,
            "available_worksheets": available_sheets,
            "selected_worksheet": active_sheet_name,
            "warnings": warnings,
            "created_at": datetime.now().isoformat(),
        }
        manifest_key = f"{relative_processed_dir}/manifest.json"
        manifest_path = storage_root / manifest_key
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        schema_metadata = {
            "columns": manifest_data["columns"],
            "row_count": total_rows,
            "column_count": num_cols,
            "available_worksheets": available_sheets,
            "selected_worksheet": active_sheet_name,
            "manifest_key": manifest_key,
        }

        return ProcessingResult(
            row_count=total_rows,
            column_count=num_cols,
            columns=columns,
            schema_metadata=schema_metadata,
            parquet_parts=parts,
            manifest_key=manifest_key,
            checksum=checksum,
            warnings=warnings,
            invalid_row_count=invalid_row_count,
            available_worksheets=available_sheets,
            selected_worksheet=active_sheet_name,
        )

    @staticmethod
    def _write_parquet_part(rows: list[dict[str, Any]], headers: list[str], output_path: Path) -> None:
        if not rows:
            # Write empty table with string columns
            arrays = [pa.array([], type=pa.string()) for _ in headers]
            table = pa.Table.from_arrays(arrays, names=headers)
        else:
            # Build column-oriented arrays
            col_data: dict[str, list[Any]] = {h: [] for h in headers}
            for row in rows:
                for h in headers:
                    val = row.get(h)
                    col_data[h].append(val)

            arrays = []
            for h in headers:
                try:
                    arr = pa.array(col_data[h])
                except (pa.ArrowInvalid, pa.ArrowTypeError):
                    # Coerce heterogeneous elements to string on mismatch
                    arr = pa.array([str(v) if v is not None else None for v in col_data[h]], type=pa.string())
                arrays.append(arr)

            table = pa.Table.from_arrays(arrays, names=headers)

        pq.write_table(table, output_path, compression="SNAPPY")

    @classmethod
    def read_paginated_rows(
        cls,
        storage_root: Path,
        manifest_key: str,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        manifest_path = storage_root / manifest_key
        if not manifest_path.is_file():
            raise DataLensException("Dataset manifest not found.", code="NOT_FOUND")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        total_rows = manifest.get("row_count", 0)
        parts = manifest.get("parts", [])

        if offset >= total_rows or total_rows == 0:
            return {
                "rows": [],
                "total": total_rows,
                "offset": offset,
                "limit": limit,
            }

        # If sorting is requested across the entire dataset, we load tables from parts
        collected_rows: list[dict[str, Any]] = []
        current_skip = offset
        needed = limit

        for part_rel_path in parts:
            part_path = storage_root / part_rel_path
            if not part_path.is_file():
                continue

            table = pq.read_table(part_path, columns=columns)
            part_row_count = table.num_rows

            if sort_by and sort_by in table.column_names:
                # Accumulate for sort
                collected_rows.extend(table.to_pylist())
            else:
                if current_skip >= part_row_count:
                    current_skip -= part_row_count
                    continue

                # Slice table for this part
                slice_len = min(part_row_count - current_skip, needed)
                sliced_table = table.slice(offset=current_skip, length=slice_len)
                collected_rows.extend(sliced_table.to_pylist())
                needed -= slice_len
                current_skip = 0

                if needed <= 0:
                    break

        if sort_by and collected_rows:
            reverse = sort_dir.lower() == "desc"

            def sort_key(r: dict[str, Any]) -> Any:
                v = r.get(sort_by)
                if v is None:
                    return ""
                return v

            try:
                collected_rows.sort(key=sort_key, reverse=reverse)
            except TypeError:
                collected_rows.sort(key=lambda r: str(r.get(sort_by) or ""), reverse=reverse)
            collected_rows = collected_rows[offset : offset + limit]

        return {
            "rows": collected_rows,
            "total": total_rows,
            "offset": offset,
            "limit": limit,
        }
