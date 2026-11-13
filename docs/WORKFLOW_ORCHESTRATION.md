# DataLens Phase 5D – Workflow Orchestration & DAG Engine

---

## 1. Overview

The Workflow Orchestration Engine allows users to chain complex, multi-step business intelligence pipelines as Directed Acyclic Graphs (DAGs):
$$\text{Source Refresh} \longrightarrow \text{Data Quality Gate} \longrightarrow \text{Transformation Pipeline} \longrightarrow \text{Materialized Version} \longrightarrow \text{Report Delivery}$$

---

## 2. Cycle Detection & Topological Sorting

Before any workflow is saved or activated, `WorkflowDAGService.validate_and_sort_steps` validates the graph:
1. **Self-Dependency Check:** No node may reference itself in `depends_on_step_ids`.
2. **Missing Reference Check:** Prerequisite step IDs must exist within the workflow.
3. **Kahn's Algorithm:**
   - Computes in-degree for each node.
   - Nodes with in-degree 0 are queued.
   - If the topological order count is less than the total node count, a circular dependency exists and activation is blocked with a detailed cycle diagnostic.

---

## 3. Configurable Failure Policies

| Failure Policy | Description |
|---|---|
| `STOP_IMMEDIATELY` | Aborts the entire workflow immediately when any step fails. Downstream steps are skipped. |
| `RETRY_FAILED_STEP` | Applies exponential backoff retries to the failed step before aborting downstream tasks. |
| `CONTINUE_INDEPENDENT_BRANCHES` | Continues executing independent steps whose prerequisites have succeeded. |
| `REQUIRE_MANUAL_INTERVENTION` | Pauses workflow execution and alerts administrators for manual resolution. |

---

## 4. Immutable Execution Lineage

- Every workflow run generates a `WorkflowExecution` parent and per-step `WorkflowStepExecution` records.
- Records input dataset versions and output dataset versions, ensuring auditability and reproducible retries.

