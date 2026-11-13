# DataLens — Prompt Evaluation Engine

## 1. Evaluation Methodology

DataLens implements a multi-metric evaluation engine that evaluates prompt outputs across two categories:
1. **Deterministic Evaluations**: Computed algorithmically with exact verification against rules or reference outputs.
2. **Model-Assisted Evaluations**: Judged heuristically or via an evaluation LLM, clearly labeled as `AI-JUDGED` to avoid presenting subjective assessments as objective ground truth.

---

## 2. Deterministic Metrics

| Metric | Evaluation Method | Scoring Logic |
| :--- | :--- | :--- |
| `exact_match` | String comparison | Returns $1.0$ if normalized response equals expected output; $0.0$ otherwise. |
| `keyword_presence` | Token presence | Returns ratio $\frac{|K_{\text{found}}|}{|K_{\text{expected}}|}$, where $K$ is the set of required keywords. |
| `json_schema_valid` | JSON parser & key check | Returns $1.0$ if valid JSON dictionary with all required keys; $0.5$ if valid JSON with missing keys; $0.0$ if malformed. |
| `response_length` | Character count bounds | Returns $1.0$ if $\text{min\_chars} \le \text{len} \le \text{max\_chars}$; partial score if outside bounds. |

---

## 3. Model-Assisted Metrics

All model-assisted metrics are tagged with `evaluation_method="model_assisted"` and specify `evaluated_by_model`.

| Metric | Focus | Explanation Details |
| :--- | :--- | :--- |
| `relevance` | Query alignment | Evaluates whether the generated response directly addresses business context. |
| `instruction_following`| Constraint adherence | Evaluates compliance with negative constraints and formatting directives. |
| `factual_consistency` | Consistency | Evaluates internal consistency and absence of contradictory claims. |
| `completeness` | Depth of response | Evaluates coverage of required analytical dimensions. |
| `clarity` | Executive tone | Evaluates professional vocabulary, layout, and readability. |

---

## 4. Honest Analytics & Statistical Significance

In `PromptAnalyticsService`:
- If an experiment has fewer than 5 observations per version, the comparison report explicitly notes: *"Observation count is too small for statistical significance."*
- Winning versions are highlighted based on aggregated scores, success rate, and latency, without unsubstantiated claims of statistical superiority.

