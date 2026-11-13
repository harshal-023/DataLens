# Transformation Pipeline Execution & Materialization

## Execution Lifecycle

1. **Step Sequence Assembly**:
   - The user defines a pipeline containing an ordered list of steps ($0, 1, \dots, N-1$).
   - Base data is established using the primary source dataset.

2. **DuckDB In-Memory Execution**:
   - Source datasets are registered as views (`read_parquet([...])`).
   - Each step generates an intermediate table in DuckDB: `step_1`, `step_2`, $\dots$, `step_N`.
   - All transformations execute in-memory with zero temporary disk writes during preview.

3. **Materialization (Run Pipeline)**:
   - When the user triggers a full run:
     1. Creates a `TransformationRun` database record with status `running`.
     2. Snapshots exact versions of all source datasets into `source_dataset_versions`.
     3. Executes all steps against the complete dataset.
     4. Exports the final table directly to a compressed Parquet part file:
        `storage_data/datasets/{workspace_id}/{output_dataset_id}/{version_id}/processed/part_0.parquet`.
     5. Calculates SHA-256 checksum and infers column metadata (data type, null count, 3 sample values).
     6. Generates `manifest.json`.
     7. Creates `Dataset` and `DatasetVersion(version_number='v1')` in PostgreSQL.
     8. Updates `TransformationRun` status to `completed`, recording duration and row count.
     9. The new dataset is immediately accessible in Data Studio, Ask Your Data, Dashboards, and Reports.

## Immutability Guarantee

- Original source datasets and versions are **never modified or overwritten**.
- All transformations produce new, independent derived datasets.

