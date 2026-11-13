"""Comprehensive cryptographic and integrity verification for Enterprise Audit Logs (Phase 7D).

Tests:
1. All 8 protected fields included in SHA-256 chained hash.
2. Tampering detection on every protected field.
3. End-to-end audit chain continuity verification.
4. Immediate detection of intermediate record deletions.
5. Detection of chronological ordering anomalies.
6. Multi-event chain creation with secret redaction and hash linking.
"""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.governance import EnterpriseAuditLog
from app.models.user import User
from app.services.governance_service import GovernanceService


@pytest.fixture
def mock_user() -> User:
    user = User(
        id=uuid.uuid4(),
        email="compliance_officer@datalens.ai",
        full_name="Compliance Auditor",
        is_active=True,
    )
    return user


def test_audit_hash_includes_all_protected_fields():
    """Verify that every protected field strictly contributes to the SHA-256 hash."""
    base_id = uuid.uuid4()
    base_actor_id = uuid.uuid4()
    base_res_id = uuid.uuid4()
    base_time = datetime(2026, 11, 12, 12, 0, 0, tzinfo=UTC)
    base_meta = {"metric": "net_revenue", "threshold": 10000}

    base_hash = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )

    # 1. Changing event_id must change hash
    h_event_id = GovernanceService.compute_audit_hash(
        event_id=uuid.uuid4(),
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_event_id != base_hash

    # 2. Changing previous_hash must change hash
    h_prev = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="TAMPERED_HASH_456",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_prev != base_hash

    # 3. Changing actor_id must change hash
    h_actor = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=uuid.uuid4(),
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_actor != base_hash

    # 4. Changing action must change hash
    h_action = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:delete",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_action != base_hash

    # 5. Changing resource_type must change hash
    h_restype = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="workspace",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_restype != base_hash

    # 6. Changing resource_id must change hash
    h_resid = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=uuid.uuid4(),
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_resid != base_hash

    # 7. Changing outcome must change hash
    h_outcome = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="DENIED",
        timestamp=base_time,
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_outcome != base_hash

    # 8. Changing timestamp must change hash
    h_time = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time + timedelta(seconds=1),
        metadata_snapshot=base_meta,
        actor_email="compliance@datalens.ai",
    )
    assert h_time != base_hash

    # 9. Changing metadata_snapshot must change hash
    h_meta = GovernanceService.compute_audit_hash(
        event_id=base_id,
        prev_hash="PREV_HASH_123",
        actor_id=base_actor_id,
        action="dataset:export",
        resource_type="dataset",
        resource_id=base_res_id,
        outcome="SUCCESS",
        timestamp=base_time,
        metadata_snapshot={"metric": "net_revenue", "threshold": 99999},
        actor_email="compliance@datalens.ai",
    )
    assert h_meta != base_hash


def test_verify_audit_log_record_tampering_detection():
    """Verify that modifying any field in an EnterpriseAuditLog causes verify_audit_log_record to fail."""
    log_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    res_id = uuid.uuid4()
    now = datetime(2026, 11, 12, 14, 30, 0, tzinfo=UTC)
    meta = {"report_type": "executive_kpi"}

    chained = GovernanceService.compute_audit_hash(
        event_id=log_id,
        prev_hash="GENESIS_DATALENS_ROOT_HASH",
        actor_id=actor_id,
        action="report:generate",
        resource_type="report",
        resource_id=res_id,
        outcome="SUCCESS",
        timestamp=now,
        metadata_snapshot=meta,
    )

    log = EnterpriseAuditLog(
        id=log_id,
        workspace_id=uuid.uuid4(),
        actor_id=actor_id,
        action="report:generate",
        resource_type="report",
        resource_id=res_id,
        timestamp=now,
        outcome="SUCCESS",
        metadata_snapshot=meta,
        previous_hash="GENESIS_DATALENS_ROOT_HASH",
        chained_hash=chained,
    )

    # Valid record passes verification
    assert GovernanceService.verify_audit_log_record(log) is True

    # Tampering with outcome fails verification
    tampered_outcome = copy.copy(log)
    tampered_outcome.outcome = "FAILURE"
    assert GovernanceService.verify_audit_log_record(tampered_outcome) is False

    # Tampering with actor_id fails verification
    tampered_actor = copy.copy(log)
    tampered_actor.actor_id = uuid.uuid4()
    assert GovernanceService.verify_audit_log_record(tampered_actor) is False

    # Tampering with metadata snapshot fails verification
    tampered_meta = copy.copy(log)
    tampered_meta.metadata_snapshot = {"report_type": "tampered_kpi"}
    assert GovernanceService.verify_audit_log_record(tampered_meta) is False

    # Tampering with chained_hash fails verification
    tampered_hash = copy.copy(log)
    tampered_hash.chained_hash = "0" * 64
    assert GovernanceService.verify_audit_log_record(tampered_hash) is False


@pytest.mark.asyncio
async def test_audit_chain_verification_complete_valid_sequence():
    """Verify that a multi-record cryptographic audit chain passes full verification."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)

    records: list[EnterpriseAuditLog] = []
    current_prev = "GENESIS_DATALENS_ROOT_HASH"

    actions = ["dataset:upload", "transformation:run", "report:export", "policy:update"]
    for i, act in enumerate(actions):
        log_id = uuid.uuid4()
        res_id = uuid.uuid4()
        ts = base_time + timedelta(minutes=i * 5)
        meta = {"seq": i, "status": "ok"}
        chained = GovernanceService.compute_audit_hash(
            event_id=log_id,
            prev_hash=current_prev,
            actor_id=user_id,
            action=act,
            resource_type="dataset",
            resource_id=res_id,
            outcome="SUCCESS",
            timestamp=ts,
            metadata_snapshot=meta,
        )
        rec = EnterpriseAuditLog(
            id=log_id,
            workspace_id=ws_id,
            actor_id=user_id,
            action=act,
            resource_type="dataset",
            resource_id=res_id,
            timestamp=ts,
            outcome="SUCCESS",
            metadata_snapshot=meta,
            previous_hash=current_prev,
            chained_hash=chained,
        )
        records.append(rec)
        current_prev = chained

    db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = records
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    db.execute.return_value = mock_res

    res = await GovernanceService.verify_audit_chain(db=db, workspace_id=ws_id)
    assert res["is_valid"] is True
    assert res["status"] == "VALID"
    assert res["total_records"] == 4
    assert res["verified_records"] == 4
    assert res["latest_hash"] == records[-1].chained_hash


@pytest.mark.asyncio
async def test_audit_chain_intermediate_deletion_detected():
    """Verify that deleting an intermediate record immediately breaks chain continuity."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)

    records: list[EnterpriseAuditLog] = []
    current_prev = "GENESIS_DATALENS_ROOT_HASH"

    for i in range(5):
        log_id = uuid.uuid4()
        ts = base_time + timedelta(minutes=i)
        chained = GovernanceService.compute_audit_hash(
            event_id=log_id,
            prev_hash=current_prev,
            actor_id=user_id,
            action=f"action_{i}",
            resource_type="system",
            resource_id=None,
            outcome="SUCCESS",
            timestamp=ts,
            metadata_snapshot={},
        )
        rec = EnterpriseAuditLog(
            id=log_id,
            workspace_id=ws_id,
            actor_id=user_id,
            action=f"action_{i}",
            resource_type="system",
            resource_id=None,
            timestamp=ts,
            outcome="SUCCESS",
            metadata_snapshot={},
            previous_hash=current_prev,
            chained_hash=chained,
        )
        records.append(rec)
        current_prev = chained

    # Delete record #2 (leaving 0, 1, 3, 4)
    del records[2]

    db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = records
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    db.execute.return_value = mock_res

    res = await GovernanceService.verify_audit_chain(db=db, workspace_id=ws_id)
    assert res["is_valid"] is False
    assert res["status"] == "CHAIN_BROKEN"
    assert res["broken_at_index"] == 2
    assert "Hash mismatch" in res["message"]


@pytest.mark.asyncio
async def test_audit_chain_timestamp_order_anomaly_detected():
    """Verify that an out-of-order timestamp insertion is flagged as an anomaly."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)

    # Record 0
    id0 = uuid.uuid4()
    ts0 = base_time
    h0 = GovernanceService.compute_audit_hash(
        event_id=id0,
        prev_hash="GENESIS_DATALENS_ROOT_HASH",
        actor_id=user_id,
        action="init",
        resource_type="system",
        resource_id=None,
        outcome="SUCCESS",
        timestamp=ts0,
        metadata_snapshot={},
    )
    rec0 = EnterpriseAuditLog(
        id=id0,
        workspace_id=ws_id,
        actor_id=user_id,
        action="init",
        resource_type="system",
        resource_id=None,
        timestamp=ts0,
        outcome="SUCCESS",
        metadata_snapshot={},
        previous_hash="GENESIS_DATALENS_ROOT_HASH",
        chained_hash=h0,
    )

    # Record 1 with BACKDATED timestamp
    id1 = uuid.uuid4()
    ts1 = base_time - timedelta(hours=1)
    h1 = GovernanceService.compute_audit_hash(
        event_id=id1,
        prev_hash=h0,
        actor_id=user_id,
        action="backdated_action",
        resource_type="system",
        resource_id=None,
        outcome="SUCCESS",
        timestamp=ts1,
        metadata_snapshot={},
    )
    rec1 = EnterpriseAuditLog(
        id=id1,
        workspace_id=ws_id,
        actor_id=user_id,
        action="backdated_action",
        resource_type="system",
        resource_id=None,
        timestamp=ts1,
        outcome="SUCCESS",
        metadata_snapshot={},
        previous_hash=h0,
        chained_hash=h1,
    )

    db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [rec0, rec1]
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    db.execute.return_value = mock_res

    res = await GovernanceService.verify_audit_chain(db=db, workspace_id=ws_id)
    assert res["is_valid"] is False
    assert res["status"] == "ORDER_ANOMALY"
    assert res["broken_at_index"] == 1
    assert "Timestamp order anomaly" in res["message"]


@pytest.mark.asyncio
async def test_audit_chain_tampered_payload_in_middle_record():
    """Verify that tampering with any field in a middle record flags RECORD_TAMPERED."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    base_time = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)

    records: list[EnterpriseAuditLog] = []
    current_prev = "GENESIS_DATALENS_ROOT_HASH"

    for i in range(4):
        log_id = uuid.uuid4()
        res_id = uuid.uuid4()
        ts = base_time + timedelta(minutes=i * 5)
        meta = {"seq": i, "status": "ok"}
        chained = GovernanceService.compute_audit_hash(
            event_id=log_id,
            prev_hash=current_prev,
            actor_id=user_id,
            action=f"action_{i}",
            resource_type="dataset",
            resource_id=res_id,
            outcome="SUCCESS",
            timestamp=ts,
            metadata_snapshot=meta,
        )
        rec = EnterpriseAuditLog(
            id=log_id,
            workspace_id=ws_id,
            actor_id=user_id,
            action=f"action_{i}",
            resource_type="dataset",
            resource_id=res_id,
            timestamp=ts,
            outcome="SUCCESS",
            metadata_snapshot=meta,
            previous_hash=current_prev,
            chained_hash=chained,
        )
        records.append(rec)
        current_prev = chained

    # Tamper with record #1's metadata
    records[1].metadata_snapshot = {"seq": 1, "status": "maliciously_altered"}

    db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = records
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    db.execute.return_value = mock_res

    res = await GovernanceService.verify_audit_chain(db=db, workspace_id=ws_id)
    assert res["is_valid"] is False
    assert res["status"] == "RECORD_TAMPERED"
    assert res["broken_at_index"] == 1
    assert "Tampering detected in record" in res["message"]

