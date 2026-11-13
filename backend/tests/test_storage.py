import shutil

import pytest

from app.core.exceptions import StorageException
from app.storage.local import LocalStorageBackend


@pytest.fixture
def temp_storage(tmp_path):
    storage_dir = tmp_path / "test_storage"
    backend = LocalStorageBackend(str(storage_dir))
    yield backend
    shutil.rmtree(storage_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_storage_crud_lifecycle(temp_storage):
    key = temp_storage.generate_storage_key(prefix="datasets", extension="csv")
    assert key.startswith("datasets/")
    assert key.endswith(".csv")

    data = b"id,name,value\n1,Alpha,100\n2,Beta,200\n"

    # Save
    saved_key = await temp_storage.save_file(key, data)
    assert saved_key == key

    # Exists
    assert await temp_storage.file_exists(key) is True

    # Read
    read_data = await temp_storage.read_file(key)
    assert read_data == data

    # Delete
    deleted = await temp_storage.delete_file(key)
    assert deleted is True
    assert await temp_storage.file_exists(key) is False


@pytest.mark.asyncio
async def test_path_traversal_prevention(temp_storage):
    # Attempt directory traversal attacks
    traversal_keys = [
        "../../etc/passwd",
        "../outside.txt",
        "..\\..\\windows\\system32\\cmd.exe",
        "datasets/../../../secret.env",
    ]

    for malicious_key in traversal_keys:
        with pytest.raises(StorageException) as exc_info:
            await temp_storage.save_file(malicious_key, b"malicious content")
        assert exc_info.value.code == "PATH_TRAVERSAL"

        with pytest.raises(StorageException) as exc_info:
            await temp_storage.read_file(malicious_key)
        assert exc_info.value.code == "PATH_TRAVERSAL"


@pytest.mark.asyncio
async def test_storage_key_generation_sanitization(temp_storage):
    # Extension with dots, spaces, or invalid chars
    key = temp_storage.generate_storage_key(prefix="reports/financial", extension=".XLSX;drop table")
    assert "xlsx" in key
    assert ";" not in key
    assert "drop" not in key
    assert " " not in key


@pytest.mark.asyncio
async def test_read_nonexistent_file(temp_storage):
    with pytest.raises(StorageException) as exc_info:
        await temp_storage.read_file("nonexistent_key.csv")
    assert exc_info.value.code == "STORAGE_NOT_FOUND"
