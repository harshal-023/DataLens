import io
from pathlib import Path

import openpyxl
import pytest

from app.core.exceptions import DataLensException
from app.services.dataset_processor import DatasetProcessor


def test_csv_processing_with_bom_and_currencies(tmp_path: Path):
    # CSV with UTF-8 BOM, currency symbols, duplicate headers, and multiline string
    csv_content = (
        "\ufeffProduct,Product,Revenue,Price,Active,Date\n"
        'Premium Pro,Pro Version,"$1,200.50",₹499.00,true,2025-01-15\n'
        'Basic Plan,Starter,"€450.00",₹199.00,false,2025-01-16\n'
        '"Enterprise\nSuite",Full,"$5,000.00",₹2499.00,true,2025-01-17\n'
    ).encode("utf-8")

    result = DatasetProcessor.process_csv(
        data=csv_content,
        storage_root=tmp_path,
        relative_processed_dir="processed/v1",
    )

    assert result.row_count == 3
    assert result.column_count == 6
    col_names = [c.name for c in result.columns]
    # Header sanitization and deduplication
    assert "Product" in col_names
    assert "Product_1" in col_names
    assert "Revenue" in col_names

    # Check Parquet parts created
    assert len(result.parquet_parts) >= 1
    manifest_file = tmp_path / result.manifest_key
    assert manifest_file.is_file()

    # Read back paginated rows
    read_back = DatasetProcessor.read_paginated_rows(
        storage_root=tmp_path,
        manifest_key=result.manifest_key,
        offset=0,
        limit=10,
    )
    assert read_back["total"] == 3
    assert len(read_back["rows"]) == 3
    # Check currency coercion to numeric
    assert read_back["rows"][0]["Revenue"] == 1200.50
    assert read_back["rows"][0]["Price"] == 499.00
    assert read_back["rows"][0]["Active"] is True


def test_csv_empty_file_rejection(tmp_path: Path):
    with pytest.raises(DataLensException) as exc:
        DatasetProcessor.process_csv(
            data=b"",
            storage_root=tmp_path,
            relative_processed_dir="processed/v1",
        )
    assert exc.value.code == "EMPTY_FILE"


def test_csv_pagination_and_sorting(tmp_path: Path):
    lines = ["id,val,category"]
    for i in range(15):
        lines.append(f"{i},{100 - i},cat_{i % 3}")
    csv_data = "\n".join(lines).encode("utf-8")

    result = DatasetProcessor.process_csv(
        data=csv_data,
        storage_root=tmp_path,
        relative_processed_dir="processed/paged",
    )
    assert result.row_count == 15

    # Page 1 (limit 5)
    p1 = DatasetProcessor.read_paginated_rows(
        storage_root=tmp_path,
        manifest_key=result.manifest_key,
        offset=0,
        limit=5,
    )
    assert len(p1["rows"]) == 5
    assert p1["rows"][0]["id"] == 0

    # Page 2 (offset 5, limit 5)
    p2 = DatasetProcessor.read_paginated_rows(
        storage_root=tmp_path,
        manifest_key=result.manifest_key,
        offset=5,
        limit=5,
    )
    assert len(p2["rows"]) == 5
    assert p2["rows"][0]["id"] == 5

    # Sorted by val ascending
    sorted_asc = DatasetProcessor.read_paginated_rows(
        storage_root=tmp_path,
        manifest_key=result.manifest_key,
        offset=0,
        limit=5,
        sort_by="val",
        sort_dir="asc",
    )
    assert sorted_asc["rows"][0]["val"] == 86  # 100 - 14 = 86


def test_excel_processing_multi_sheet(tmp_path: Path):
    # Create an in-memory workbook with 2 sheets
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Sales"
    ws1.append(["Region", "Amount", "Units"])
    ws1.append(["North", 15000, 150])
    ws1.append(["South", 22000, 210])

    ws2 = wb.create_sheet(title="Inventory")
    ws2.append(["Item", "Stock", "Warehouse"])
    ws2.append(["Widget A", 500, "WH-1"])

    buf = io.BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()

    # Process first sheet by default
    res1 = DatasetProcessor.process_excel(
        data=excel_bytes,
        storage_root=tmp_path,
        relative_processed_dir="processed/excel_s1",
    )
    assert res1.row_count == 2
    assert res1.available_worksheets == ["Sales", "Inventory"]
    assert res1.selected_worksheet == "Sales"

    # Process explicitly selected sheet
    res2 = DatasetProcessor.process_excel(
        data=excel_bytes,
        storage_root=tmp_path,
        relative_processed_dir="processed/excel_s2",
        selected_worksheet="Inventory",
    )
    assert res2.row_count == 1
    assert res2.selected_worksheet == "Inventory"
    col_names = [c.name for c in res2.columns]
    assert "Item" in col_names
    assert "Stock" in col_names


def test_excel_corrupted_file_handling(tmp_path: Path):
    corrupt_data = b"PK\x03\x04not-a-valid-zip-or-excel-file-content"
    with pytest.raises(DataLensException) as exc:
        DatasetProcessor.process_excel(
            data=corrupt_data,
            storage_root=tmp_path,
            relative_processed_dir="processed/corrupt",
        )
    assert exc.value.code == "EXCEL_PARSE_ERROR"
