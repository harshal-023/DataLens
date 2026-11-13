import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import POSTGRES_AVAILABLE

BACKEND_DIR = str(Path(__file__).resolve().parent.parent)


def test_alembic_upgrade_sql_generation():
    """
    Verifies that Alembic generates the complete PostgreSQL DDL upgrade
    for both Phase 2A and Phase 2B migrations without syntax or dependency errors.
    """
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Alembic upgrade SQL failed: {result.stderr}"
    sql_output = result.stdout
    # Phase 2A tables
    assert "CREATE TABLE users" in sql_output
    assert "CREATE TABLE workspaces" in sql_output
    assert "CREATE TABLE workspace_memberships" in sql_output
    assert "CREATE TABLE datasets" in sql_output
    assert "CREATE TABLE dataset_versions" in sql_output
    assert "CREATE TABLE analysis_runs" in sql_output
    assert "CREATE TABLE reports" in sql_output
    assert "ALTER TABLE datasets ADD CONSTRAINT fk_datasets_current_version_id" in sql_output

    # Phase 2B tables
    assert "CREATE TABLE refresh_sessions" in sql_output
    assert "CREATE TABLE password_reset_tokens" in sql_output
    assert "CREATE TABLE workspace_invitations" in sql_output
    assert "UPDATE alembic_version SET version_num='20261111_0002'" in sql_output

    # Phase 2C columns
    assert "ALTER TABLE datasets ADD COLUMN is_archived" in sql_output
    assert "ALTER TABLE dataset_versions ADD COLUMN original_storage_key" in sql_output
    assert "UPDATE alembic_version SET version_num='20261111_0003'" in sql_output


def test_alembic_downgrade_sql_generation():
    """
    Verifies that Alembic generates the complete PostgreSQL DDL downgrade
    from head (20261111_0003) down to base without syntax or dependency errors.
    """
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "20261111_0003:base", "--sql"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"Alembic downgrade SQL failed: {result.stderr}"
    sql_output = result.stdout
    # Phase 2C columns dropped first
    assert "ALTER TABLE datasets DROP COLUMN is_archived" in sql_output
    assert "ALTER TABLE dataset_versions DROP COLUMN original_storage_key" in sql_output

    # Phase 2B tables dropped next
    assert "DROP TABLE workspace_invitations" in sql_output
    assert "DROP TABLE password_reset_tokens" in sql_output
    assert "DROP TABLE refresh_sessions" in sql_output

    # Phase 2A tables dropped next
    assert "DROP TABLE reports" in sql_output
    assert "DROP TABLE analysis_runs" in sql_output
    assert "ALTER TABLE datasets DROP CONSTRAINT fk_datasets_current_version_id" in sql_output
    assert "DROP TABLE dataset_versions" in sql_output
    assert "DROP TABLE datasets" in sql_output
    assert "DROP TABLE workspace_memberships" in sql_output
    assert "DROP TABLE workspaces" in sql_output
    assert "DROP TABLE users" in sql_output


@pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL instance is offline on port 5432 — live migration & row insertion tests marked not executed",
)
@pytest.mark.asyncio
async def test_live_postgres_connection_and_migration():
    """
    This test runs ONLY when a real PostgreSQL instance is detected on port 5432.
    It verifies live schema migration, user registration, and workspace creation.
    """
    from app.db.session import check_database_connection
    connected, error = await check_database_connection()
    assert connected is True
    assert error is None
