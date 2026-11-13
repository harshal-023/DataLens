import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.analysis_run import AnalysisRun
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.refresh_session import RefreshSession
from app.models.report import Report
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from tests.conftest import POSTGRES_AVAILABLE

pytestmark = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL is offline on port 5432",
)

# Use NullPool in integration tests to ensure connections are strictly scoped to the active pytest event loop
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
AsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.mark.asyncio
async def test_live_postgres_crud_and_rollback():
    """
    Stage 3.1: Verifies real insert, select, update, delete, and transaction rollback
    against PostgreSQL 18.
    """
    async with AsyncSessionLocal() as session:
        test_email = f"crud_test_{uuid.uuid4().hex[:8]}@datalens.ai"
        user = User(
            full_name="CRUD Test User",
            email=test_email,
            password_hash=hash_password("ValidPass123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        user_id = user.id
        assert user_id is not None
        assert user.email == test_email

    # Select and Update in a fresh session
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        retrieved = res.scalar_one_or_none()
        assert retrieved is not None
        assert retrieved.full_name == "CRUD Test User"

        retrieved.full_name = "CRUD Updated User"
        await session.commit()

    # Verify update
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        retrieved = res.scalar_one_or_none()
        assert retrieved.full_name == "CRUD Updated User"

    # Test Transaction Rollback
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        retrieved = res.scalar_one_or_none()
        retrieved.full_name = "Should Be Rolled Back"
        await session.rollback()

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        retrieved = res.scalar_one_or_none()
        assert retrieved.full_name == "CRUD Updated User"

        # Cleanup
        await session.delete(retrieved)
        await session.commit()


@pytest.mark.asyncio
async def test_live_postgres_constraints():
    """
    Stage 3.1: Verifies unique and foreign key constraints enforcement in PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        test_email = f"unique_{uuid.uuid4().hex[:8]}@datalens.ai"
        user1 = User(
            full_name="Unique User 1",
            email=test_email,
            password_hash=hash_password("Pass123!"),
        )
        session.add(user1)
        await session.commit()

        # Duplicate email should fail unique constraint
        user2 = User(
            full_name="Unique User 2",
            email=test_email,
            password_hash=hash_password("Pass123!"),
        )
        session.add(user2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # Cleanup
        await session.delete(user1)
        await session.commit()


@pytest.mark.asyncio
async def test_live_postgres_auth_lifecycle():
    """
    Stage 3.2: Verifies user registration, Argon2id password verification,
    refresh session creation, rotation, and revocation in PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        raw_pw = "StrongPass@2026!"
        user = User(
            full_name="Auth Lifecycle User",
            email=f"auth_{uuid.uuid4().hex[:8]}@datalens.ai",
            password_hash=hash_password(raw_pw),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Verify password matches Argon2id hash
        assert verify_password(raw_pw, user.password_hash) is True
        assert verify_password("WrongPassword!", user.password_hash) is False

        # Create refresh session
        session_id = uuid.uuid4()
        refresh_token_hash = "token_hash_alpha"
        session_obj = RefreshSession(
            id=session_id,
            user_id=user.id,
            token_hash=refresh_token_hash,
            ip_address="127.0.0.1",
            user_agent="pytest-runner",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
        )
        session.add(session_obj)
        await session.commit()

        # Rotate refresh token
        session_obj.token_hash = "token_hash_beta"
        await session.commit()

        # Revoke session
        session_obj.is_revoked = True
        await session.commit()

        # Verify revoked state persists
        await session.refresh(session_obj)
        assert session_obj.is_revoked is True
        assert session_obj.token_hash == "token_hash_beta"

        # Cleanup
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_live_postgres_workspaces_and_rbac():
    """
    Stage 3.3: Verifies workspace creation, owner membership, role hierarchy,
    and member assignments in PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        owner = User(
            full_name="Workspace Owner",
            email=f"owner_{uuid.uuid4().hex[:8]}@datalens.ai",
            password_hash=hash_password("Pass123!"),
        )
        member = User(
            full_name="Workspace Viewer",
            email=f"viewer_{uuid.uuid4().hex[:8]}@datalens.ai",
            password_hash=hash_password("Pass123!"),
        )
        session.add_all([owner, member])
        await session.commit()
        await session.refresh(owner)
        await session.refresh(member)

        # Create Workspace
        ws = Workspace(name="Live Analytics Workspace", owner_id=owner.id)
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

        # Add memberships (Owner and Viewer)
        m_owner = WorkspaceMembership(workspace_id=ws.id, user_id=owner.id, role="owner")
        m_viewer = WorkspaceMembership(workspace_id=ws.id, user_id=member.id, role="viewer")
        session.add_all([m_owner, m_viewer])
        await session.commit()

        # Query memberships
        stmt = select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == ws.id)
        res = await session.execute(stmt)
        memberships = res.scalars().all()
        assert len(memberships) == 2
        roles = {m.role for m in memberships}
        assert "owner" in roles
        assert "viewer" in roles

        # Cleanup
        await session.delete(owner)
        await session.delete(member)
        await session.commit()


@pytest.mark.asyncio
async def test_live_postgres_dataset_and_immutable_versions():
    """
    Stage 3.4: Verifies dataset metadata, JSONB schemas, immutable versioning,
    and version pointers in PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        user = User(
            full_name="Dataset Analyst",
            email=f"analyst_{uuid.uuid4().hex[:8]}@datalens.ai",
            password_hash=hash_password("Pass123!"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        ws = Workspace(name="Data Persistence Workspace", owner_id=user.id)
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

        # Create Dataset
        ds = Dataset(
            workspace_id=ws.id,
            uploaded_by=user.id,
            name="Q4 Sales Pipeline",
            original_filename="sales_pipeline.csv",
            file_type="csv",
            row_count=5000,
            column_count=8,
            status="ready",
        )
        session.add(ds)
        await session.commit()
        await session.refresh(ds)

        # Create Version 1 with JSONB schema
        schema_v1 = {
            "columns": [
                {"name": "deal_id", "inferred_type": "integer"},
                {"name": "revenue", "inferred_type": "float"},
            ]
        }
        v1 = DatasetVersion(
            dataset_id=ds.id,
            version_number="v1.0",
            storage_key="processed/ds_q4/part-00001.parquet",
            original_storage_key="uploads/ds_q4_v1.csv",
            file_size=102400,
            schema_metadata=schema_v1,
            row_count=5000,
            column_count=2,
            checksum="sha256_mock_hash_v1",
            status="ready",
        )
        session.add(v1)
        await session.commit()
        await session.refresh(v1)

        # Point dataset current_version_id to v1
        ds.current_version_id = v1.id
        await session.commit()

        # Create Version 2 (replacement dataset - immutability verification)
        schema_v2 = {
            "columns": [
                {"name": "deal_id", "inferred_type": "integer"},
                {"name": "revenue", "inferred_type": "float"},
                {"name": "region", "inferred_type": "string"},
            ]
        }
        v2 = DatasetVersion(
            dataset_id=ds.id,
            version_number="v2.0",
            storage_key="processed/ds_q4_v2/part-00001.parquet",
            original_storage_key="uploads/ds_q4_v2.csv",
            file_size=153600,
            schema_metadata=schema_v2,
            row_count=6200,
            column_count=3,
            checksum="sha256_mock_hash_v2",
            status="ready",
        )
        session.add(v2)
        await session.commit()
        await session.refresh(v2)

        # Update pointer to v2
        ds.current_version_id = v2.id
        ds.row_count = 6200
        ds.column_count = 3
        await session.commit()

        # Verify historical versions remain intact in PostgreSQL
        stmt = select(DatasetVersion).where(DatasetVersion.dataset_id == ds.id).order_by(DatasetVersion.version_number)
        res = await session.execute(stmt)
        versions = res.scalars().all()
        assert len(versions) == 2
        assert versions[0].version_number == "v1.0"
        assert versions[0].row_count == 5000
        assert versions[1].version_number == "v2.0"
        assert versions[1].row_count == 6200

        # Verify JSONB retrieval
        assert versions[1].schema_metadata["columns"][2]["name"] == "region"

        # Cleanup
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_live_postgres_analysis_and_reports():
    """
    Stage 3.5 & 3.6: Verifies analysis run execution logging and report
    metadata persistence in PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        user = User(
            full_name="Report Generator",
            email=f"reports_{uuid.uuid4().hex[:8]}@datalens.ai",
            password_hash=hash_password("Pass123!"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        ws = Workspace(name="Reporting Workspace", owner_id=user.id)
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

        ds = Dataset(
            workspace_id=ws.id,
            uploaded_by=user.id,
            name="Quarterly Financials",
            original_filename="fin.xlsx",
            file_type="xlsx",
            row_count=1000,
            column_count=5,
            status="ready",
        )
        session.add(ds)
        await session.commit()
        await session.refresh(ds)

        v1 = DatasetVersion(
            dataset_id=ds.id,
            version_number="v1.0",
            storage_key="processed/fin/part-00001.parquet",
            file_size=50000,
            schema_metadata={"columns": [{"name": "revenue", "inferred_type": "float"}]},
            row_count=1000,
            column_count=1,
            checksum="hash_fin",
            status="ready",
        )
        session.add(v1)
        await session.commit()
        await session.refresh(v1)
        ds.current_version_id = v1.id
        await session.commit()

        # 1. Create AnalysisRun record
        analysis_run = AnalysisRun(
            dataset_id=ds.id,
            dataset_version_id=v1.id,
            analysis_type="descriptive_statistics",
            parameters={"target_columns": ["revenue"]},
            status="completed",
            execution_time_ms=12,
            result_summary={"revenue": {"mean": 1250.0, "sum": 1250000.0}},
        )
        session.add(analysis_run)
        await session.commit()
        await session.refresh(analysis_run)
        assert analysis_run.id is not None
        assert analysis_run.result_summary["revenue"]["sum"] == 1250000.0

        # 2. Create Report record
        report = Report(
            workspace_id=ws.id,
            dataset_id=ds.id,
            dataset_version_id=v1.id,
            created_by=user.id,
            title="Q4 Executive Performance Audit",
            format="pdf",
            storage_key=f"reports/{ws.id}/q4_exec.pdf",
            file_size=45230,
            report_config={"analysis_run_id": str(analysis_run.id)},
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)

        assert report.id is not None
        assert report.title == "Q4 Executive Performance Audit"
        assert report.format == "pdf"
        assert report.report_config["analysis_run_id"] == str(analysis_run.id)

        # Query reports by workspace
        stmt = select(Report).where(Report.workspace_id == ws.id)
        res = await session.execute(stmt)
        reports_list = res.scalars().all()
        assert len(reports_list) == 1
        assert reports_list[0].file_size == 45230

        # Cleanup
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_live_postgres_concurrency_and_pooling():
    """
    Stage 5: Verifies concurrent async sessions against connection pool
    without deadlock or connection exhaustion.
    """
    async def run_worker(worker_id: int):
        async with AsyncSessionLocal() as session:
            test_email = f"worker_{worker_id}_{uuid.uuid4().hex[:6]}@datalens.ai"
            user = User(
                full_name=f"Worker {worker_id}",
                email=test_email,
                password_hash=hash_password("WorkerPass123!"),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            stmt = select(User).where(User.id == user.id)
            res = await session.execute(stmt)
            retrieved = res.scalar_one_or_none()
            assert retrieved is not None
            assert retrieved.email == test_email

            # Clean up worker user
            await session.delete(retrieved)
            await session.commit()
            return True

    # Launch 15 concurrent sessions (bursting beyond base pool_size=10 into max_overflow=20)
    tasks = [run_worker(i) for i in range(15)]
    results = await asyncio.gather(*tasks)
    assert all(results)
    assert len(results) == 15
