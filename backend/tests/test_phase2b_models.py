from sqlalchemy.dialects.postgresql import UUID

import app.models  # noqa: F401
from app.db.base import Base


def test_phase2b_models_metadata_registered():
    tables = Base.metadata.tables.keys()
    assert "refresh_sessions" in tables
    assert "password_reset_tokens" in tables
    assert "workspace_invitations" in tables


def test_refresh_session_model_attributes():
    rs_table = Base.metadata.tables["refresh_sessions"]
    assert isinstance(rs_table.c.id.type, UUID)
    assert isinstance(rs_table.c.user_id.type, UUID)
    assert isinstance(rs_table.c.family_id.type, UUID)
    assert rs_table.c.token_hash.nullable is False
    assert rs_table.c.is_revoked.nullable is False

    # Check foreign key to users.id with CASCADE
    fks = list(rs_table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "users"
    assert fks[0].ondelete == "CASCADE"


def test_password_reset_token_model_attributes():
    prt_table = Base.metadata.tables["password_reset_tokens"]
    assert isinstance(prt_table.c.id.type, UUID)
    assert isinstance(prt_table.c.user_id.type, UUID)
    assert prt_table.c.token_hash.nullable is False
    assert prt_table.c.is_used.nullable is False

    fks = list(prt_table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "users"
    assert fks[0].ondelete == "CASCADE"


def test_workspace_invitation_model_attributes():
    wi_table = Base.metadata.tables["workspace_invitations"]
    assert isinstance(wi_table.c.id.type, UUID)
    assert isinstance(wi_table.c.workspace_id.type, UUID)
    assert wi_table.c.email.nullable is False
    assert wi_table.c.role.nullable is False
    assert wi_table.c.token_hash.nullable is False
    assert wi_table.c.is_accepted.nullable is False

    fks = {fk.column.table.name: fk for fk in wi_table.foreign_keys}
    assert "workspaces" in fks
    assert fks["workspaces"].ondelete == "CASCADE"
    assert "users" in fks
    assert fks["users"].ondelete == "SET NULL"
