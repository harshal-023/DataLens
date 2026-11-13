# Conversational Analytics & Session Memory

## Conversational Context Management
DataLens maintains multi-turn conversational context, allowing users to drill down, filter, pivot, and follow up naturally across an analysis thread.

## Follow-Up Query Resolution
When a user asks:
- *"What is revenue by region?"* -> System computes regional revenue breakdown.
- *"Now only for Maharashtra"* -> System recognizes the intent is a filter refinement, retains the regional group-by and revenue metric, and appends the categorical filter `region = 'Maharashtra'`.
- *"Break it down by product category"* -> System preserves the filtered state and swaps or appends `product_category` as the active dimension.

## Data Persistence Models
Conversational state is stored across PostgreSQL tables:
- `nla_sessions`: Stores `workspace_id`, `primary_dataset_id`, `title`, timestamps.
- `nla_messages`: Stores `role`, `content`, `direct_answer`, `metric_cards`, `chart_config`, `evidence_data`, `query_plan`, `raw_sql`, `execution_time_ms`, `row_count`.
- `saved_analyses`: Stores analyst bookmarks for quick recall and dashboard/report inclusion.

## API Endpoints
- `POST /api/v1/analytics/query`: Initial question submission.
- `POST /api/v1/analytics/clarify`: Disambiguation resolution.
- `POST /api/v1/analytics/follow-up`: Multi-turn conversational drill-downs.
- `GET /api/v1/analytics/sessions`: Retrieves thread list for the sidebar.
- `GET /api/v1/analytics/sessions/{session_id}`: Retrieves full message history.
- `DELETE /api/v1/analytics/sessions/{session_id}`: Deletes conversation thread.

