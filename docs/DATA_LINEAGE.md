# Data Lineage & Provenance Tracking

## Lineage Model

DataLens tracks end-to-end provenance for all transformed datasets via the `TransformationRun` model:

- `pipeline_id`: Foreign key to `transformation_pipelines.id`.
- `workspace_id`: Foreign key to `workspaces.id`.
- `triggered_by`: User ID who initiated the execution.
- `source_dataset_versions`: JSON snapshot recording exact dataset names, version IDs, version numbers, and row counts at the time of execution.
- `output_dataset_id`: Derived `Dataset.id`.
- `output_dataset_version_id`: Derived `DatasetVersion.id`.
- `execution_duration_ms`: Execution runtime in milliseconds.
- `row_count`: Final row count produced.
- `status`: Execution state (`pending`, `running`, `completed`, `failed`).
- `error_details`: Exception message and stack trace if execution failed.

## Manifest Provenance

The generated `manifest.json` embedded in the Parquet storage bundle includes lineage tags:
```json
{
  "parts": ["datasets/.../part_0.parquet"],
  "row_count": 1250,
  "column_count": 8,
  "columns": [...],
  "checksum": "...",
  "created_at": "2026-11-12T01:15:00.000000Z",
  "transformation_pipeline_id": "9350adf4-3e68-41d6-a8a1-8134f564715a",
  "transformation_run_id": "0df628ab-40a2-4a0b-967b-b5d12ef4b419"
}
```
This guarantees that derived datasets can always be audited back to the exact code, pipeline, and version of source inputs.

