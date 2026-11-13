# DataLens — Prompt Experiments & Benchmarking

## 1. Experiment Lifecycle

A Prompt Experiment in DataLens evaluates two or more prompt versions against standardized test cases under controlled execution conditions.

```
┌─────────┐      ┌─────────┐      ┌───────────┐      ┌───────────┐
│ PENDING │ ───▶ │ RUNNING │ ───▶ │ COMPLETED │  OR  │  FAILED   │
└─────────┘      └─────────┘      └───────────┘      └───────────┘
                      │
                      ▼
                 ┌───────────┐
                 │ CANCELLED │
                 └───────────┘
```

1. **Pending**: Experiment created with target versions and test cases.
2. **Running**: Execution engine evaluates each permutation:
   $$\text{Total Runs} = |\text{Versions}| \times |\text{Test Cases}|$$
3. **Completed**: All runs executed and outputs recorded.
4. **Cancelled**: User manually stopped execution via `POST /api/v1/experiments/{id}/cancel`. All completed partial runs are preserved.
5. **Failed**: Unrecoverable network or configuration error. Completed runs remain intact for analysis.

---

## 2. Test Cases & Execution Tracking

Each `test_cases` record defines:
- `name`: Descriptive test case title.
- `variables`: Concrete dictionary of key-value inputs.
- `expected_output`: Ground truth reference string (for exact match evaluations).
- `expected_keywords`: Key terms that must appear in compliant outputs.

Each execution permutation is stored as an immutable `experiment_runs` record:
- `prompt_version_id`: Exact version tested.
- `test_case_id`: Exact test case tested.
- `rendered_system_prompt`: Final text sent as system instructions.
- `rendered_user_prompt`: Final text with variables rendered.
- `response_text`: Generated model output.
- `latency_ms`: Execution duration in milliseconds.
- `input_tokens` / `output_tokens`: Real or estimated token counts.
- `estimated_cost_usd`: Accurate cost calculation based on token counts.
- `status`: `completed`, `failed`, or `skipped`.
- `error_message`: Captured exception string if execution failed.

---

## 3. Duplicate Execution Safety

The experiment execution engine checks existing `(prompt_version_id, test_case_id)` pairs before scheduling calls, avoiding duplicate executions and unneeded provider costs.

