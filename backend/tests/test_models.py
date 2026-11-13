from sqlalchemy.dialects.postgresql import JSONB, UUID

import app.models  # noqa: F401
from app.db.base import Base


def test_models_metadata_registered():
    tables = Base.metadata.tables.keys()
    assert "users" in tables
    assert "workspaces" in tables
    assert "workspace_memberships" in tables
    assert "datasets" in tables
    assert "dataset_versions" in tables
    assert "analysis_runs" in tables
    assert "reports" in tables


def test_user_model_attributes():
    user_table = Base.metadata.tables["users"]
    assert isinstance(user_table.c.id.type, UUID)
    assert user_table.c.email.unique or any(
        ix.unique for ix in user_table.indexes if "email" in ix.columns
    )
    assert user_table.c.password_hash.nullable is False
    assert user_table.c.is_active.nullable is False


def test_workspace_membership_unique_constraint():
    wm_table = Base.metadata.tables["workspace_memberships"]
    unique_constraints = [
        c for c in wm_table.constraints if getattr(c, "columns", None) is not None
    ]
    has_workspace_user_unique = False
    for uc in unique_constraints:
        col_names = {c.name for c in uc.columns}
        if {"workspace_id", "user_id"}.issubset(col_names):
            has_workspace_user_unique = True
            break
    assert has_workspace_user_unique is True


def test_dataset_version_unique_constraint():
    dv_table = Base.metadata.tables["dataset_versions"]
    has_dataset_version_unique = False
    for c in dv_table.constraints:
        if getattr(c, "columns", None) is not None:
            col_names = {col.name for col in c.columns}
            if {"dataset_id", "version_number"}.issubset(col_names):
                has_dataset_version_unique = True
                break
    assert has_dataset_version_unique is True
    assert isinstance(dv_table.c.schema_metadata.type, JSONB)


def test_report_foreign_key_delete_policy():
    report_table = Base.metadata.tables["reports"]
    # Check that dataset_id and dataset_version_id FKs use SET NULL
    for fk in report_table.foreign_keys:
        if fk.parent.name in ("dataset_id", "dataset_version_id"):
            assert fk.ondelete == "SET NULL"


def test_circular_foreign_key_handling():
    dataset_table = Base.metadata.tables["datasets"]
    # current_version_id foreign key
    fks = [fk for fk in dataset_table.foreign_keys if fk.parent.name == "current_version_id"]
    assert len(fks) == 1
    assert fks[0].use_alter is True
    assert fks[0].ondelete == "SET NULL"


def test_analysis_run_jsonb_columns():
    ar_table = Base.metadata.tables["analysis_runs"]
    assert isinstance(ar_table.c.parameters.type, JSONB)
    assert isinstance(ar_table.c.result_summary.type, JSONB)
