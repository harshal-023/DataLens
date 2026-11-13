# Phase 7C: AI Architecture & Intelligence Integration Report

## 1. Executive Summary

This report evaluates the **Unified AI Architecture** implemented across DataLens (Phases 3A, 6A, 6B, 6C, and 6D). The system integrates cloud AI (Google Gemini), local offline AI (Ollama), and a mathematical rule-based fallback into one hybrid routing engine.

### Core Architectural Principles Verified:
1. **Zero Raw Row Data Transmission**: Under default enterprise policy, raw cell data are never sent to cloud providers. Only sanitized schema column metadata, data types, and aggregated summaries are transmitted.
2. **Deterministic Calculations Only**: Neither Gemini nor Ollama performs numerical aggregation. All calculations are executed directly in DuckDB on Parquet files.
3. **No Arbitrary SQL / Code Execution**: AI models output structured analytical plans, never raw SQL or executable Python code. Plans are compiled via a strict, parameterized query generator.
4. **Resilient Offline Fallback**: In the absence of API keys or internet access, the deterministic provider produces verified heuristic plans and grounded narrative explanations.

---

## 2. Provider Abstraction & Hybrid Routing Engine

The `HybridAIRouter` (`backend/app/services/ai/hybrid_router.py`) directs analytical tasks across available providers based on routing mode, task complexity, and dataset sensitivity policies:

```
                                  ┌─────────────────────────────┐
                                  │     Analytical Question     │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │      Hybrid AI Router       │
                                  └──────────────┬──────────────┘
                                                 │
                  ┌──────────────────────────────┼──────────────────────────────┐
                  │                              │                              │
                  ▼                              ▼                              ▼
    ┌───────────────────────────┐  ┌───────────────────────────┐  ┌───────────────────────────┐
    │       Google Gemini       │  │       Local Ollama        │  │  Deterministic Fallback   │
    │  - Complex Reasoning      │  │  - Schema Explanation     │  │  - Zero External Dep      │
    │  - Executive Narratives   │  │  - Internal Queries       │  │  - Rule-Based Plans       │
    │  - Evaluator Judge        │  │  - Air-Gapped Privacy     │  │  - Grounded Templates     │
    └───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

### Routing Modes & Verification Status

| Routing Mode | Description | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| `HYBRID` (Default) | Routes business reasoning to Gemini; local queries to Ollama; falls back to deterministic on errors | Verified in `test_unified_ai.py::test_hybrid_router_task_routing` | **PASS** |
| `GEMINI_ONLY` | Forces all AI tasks through Google Gemini SDK | Verified in `test_gemini_integration.py` | **PASS** |
| `LOCAL_ONLY` | Strictly uses local Ollama daemon; blocks all cloud egress | Verified in `test_unified_ai.py::test_ollama_provider_mocked_generation` | **PASS** |
| `DETERMINISTIC_ONLY`| Pure offline rule-based heuristics; zero network calls | Verified in `test_unified_ai.py::test_deterministic_provider_plan_and_explanation` | **PASS** |

---

## 3. Data Privacy & Governance Controls

### 3.1 Sensitivity-Based Policy Enforcement
When a dataset's `sensitivity_tier` is marked `CONFIDENTIAL` or `RESTRICTED`:
- The router automatically overrides any `HYBRID` or `GEMINI_ONLY` configuration.
- Processing is forced to the local Ollama provider or deterministic fallback.
- Verified in `test_unified_ai.py::test_hybrid_router_privacy_enforcement_blocks_cloud` and `test_ai_security_audit.py::test_privacy_zero_raw_data_by_default`.

### 3.2 Cell Value & Secret Redaction
- Column profiling excludes `sample_values` from schema payloads when `AI_SEND_SAMPLE_VALUES=False`.
- Regex filters scan schemas and prompts for credentials, passwords, access keys, and API tokens before provider dispatch.

---

## 4. Natural Language Analytics & Safe Query Compilation

The Natural Language Analytics (NLA) pipeline converts business questions into verified calculations without hallucinations:

### 4.1 Step-by-Step Execution Lifecycle
1. **Ambiguity Resolution**: If a question lacks clear dimension or metric specifications, the planner requests clarification instead of guessing (`test_nl_analytics.py::test_planner_detects_ambiguity_and_asks_clarification`).
2. **Metric & Dimension Resolution**: Matches column synonyms against the semantic metric registry (e.g. *"sales"* $\to$ `revenue`, *"geo"* $\to$ `region`).
3. **Plan Validation**: `PlanValidator` verifies that all columns exist in the target dataset schema and ensures aggregations are type-compatible (e.g. prohibiting `SUM` on text columns).
4. **Safe Query Compilation**:
   - `SafeQueryCompiler` emits ANSI-compliant SQL targeting DuckDB.
   - Enforces `NULLIF(column, 0)` on denominators to prevent division-by-zero crashes.
   - Wraps column identifiers in double quotes to prevent SQL injection.
5. **Multi-Dataset JOIN Safety**:
   - Only joins with verified foreign key or discovered semantic relationships are allowed.
   - Compiled queries enforce explicit join predicates with safety row limits.

---

## 5. Autonomous AI Business Analyst

The Business Analyst engine (`backend/app/services/business_analyst/`) surfaces proactive insights across datasets:

1. **Trend Engine**: Analyzes period-over-period variance and compound growth trajectories.
2. **Anomaly Detection**: Combines parametric (Z-Score) and non-parametric (IQR, Isolation Forest) statistical models.
3. **Risk & Opportunity Engines**: Identifies customer concentration, margin compression, and high-growth opportunities.
4. **Variance Attribution**: Mathematical decomposition ensures that $\Delta \text{Total} = \Delta \text{Volume} + \Delta \text{Price} + \Delta \text{Mix}$ exactly, preventing fabricated variance explanations.
5. **Hallucination Guardrails**: Explanations cite only verified statistical outputs; statements asserting causality or fraud are explicitly barred by system instructions.

---

## 6. Live vs Mocked Testing Summary

| Test Category | Target Component | Mocked Suite | Live Execution | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **Gemini Integration** | Official `google-genai` SDK, availability, plan generation | 16 tests in `test_gemini_integration.py` | Verified fallback on offline/unreachable network | **PASS** |
| **Ollama Local AI** | HTTP REST client on `localhost:11434` | 3 tests in `test_unified_ai.py` | Verified health probe & offline error handling | **PASS** |
| **Deterministic Fallback** | Heuristic planner & grounded narrative | 6 tests across `test_ai_analytics.py` & `test_unified_ai.py` | 100% offline rule-based execution verified | **PASS** |
| **Prompt Lab** | Prompt execution, variable interpolation, evaluator | 18 tests in `test_prompt_lab.py` | Simulation and model-assisted judging verified | **PASS** |

