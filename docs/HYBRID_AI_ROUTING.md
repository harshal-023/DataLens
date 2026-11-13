# Hybrid AI Provider Routing Engine

## 1. Overview
The DataLens `HybridAIRouter` provides intelligent, policy-driven orchestration between Google Gemini cloud models, local self-hosted Ollama instances, and an offline deterministic fallback engine.

```
                      +-----------------------------+
                      |       Incoming Task         |
                      | (Ask Data, Reports, ML, PL) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Data Sensitivity Check    |
                      |   (CONFIDENTIAL / RESTRICTED)|
                      +--------------+--------------+
                               /            \
                  Sensitive  /                \ Public / Internal
                           /                    \
                          v                      v
             +-------------------------+   +-------------------------+
             | Cloud Egress Blocked    |   | Workspace Policy Check  |
             | Route: Local Ollama     |   | (cloud_ai_permitted?)   |
             +------------+------------+   +------------+------------+
                          |                             |
                          | (Ollama Offline?)           | Yes
                          v                             v
             +-------------------------+   +-------------------------+
             | Cascade: Deterministic  |   | Task Complexity Matrix: |
             | Engine (Zero Egress)    |   | - Routine -> Ollama     |
             +-------------------------+   | - Complex -> Gemini     |
                                           +------------+------------+
                                                        |
                                           (Gemini Rate Limit / Offline)
                                                        |
                                                        v
                                           +-------------------------+
                                           | Fallback to Ollama      |
                                           +------------+------------+
                                                        |
                                           (Ollama Offline)
                                                        |
                                                        v
                                           +-------------------------+
                                           | Fallback to Determ.     |
                                           +-------------------------+
```

---

## 2. Operating Modes

1. **`HYBRID` (Default):**
   - Automatically routes tasks based on computational complexity, query intent, privacy policies, and provider health.
2. **`GEMINI_ONLY`:**
   - Exclusively routes requests to Google Gemini. If cloud egress is prohibited for a dataset, returns an explicit privacy policy violation.
3. **`LOCAL_ONLY`:**
   - Exclusively routes requests to the local Ollama instance, ensuring 100% data sovereignty.
4. **`DETERMINISTIC_ONLY`:**
   - Offline, heuristic-based mathematical execution without LLM calls. Useful for testing, offline demoing, and resource-constrained environments.

---

## 3. Task Classification & Routing Matrix in Hybrid Mode

| Task Type | Complexity | Privacy Consideration | Primary Provider | Fallback Provider | Fallback 2 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SCHEMA_EXPLANATION`** | Low | Low | Local Ollama | Fallback Deterministic | N/A |
| **`SQL_GENERATION`** | Medium-High | Schema only | Gemini | Local Ollama | Deterministic |
| **`RESULT_EXPLANATION`** | Medium | Aggregates only | Local Ollama | Gemini | Deterministic |
| **`REPORT_NARRATIVE`** | High | Aggregates only | Gemini | Local Ollama | Deterministic |
| **`ML_EXPLANATION`** | Medium | Metrics only | Local Ollama | Gemini | Deterministic |
| **`PROMPT_EVALUATION`** | High | Prompt text | Gemini | Local Ollama | Deterministic |
| **`SENSITIVE_DATA_QUERY`** | Any | **CONFIDENTIAL / RESTRICTED** | **Local Ollama (Strict)** | **Deterministic Only** | **Never Cloud** |

---

## 4. Privacy Invariant Guarantees
- Any query touching a dataset marked `CONFIDENTIAL` or `RESTRICTED` automatically strips Gemini from the candidate pool.
- Any workspace where `cloud_ai_permitted = False` enforces total cloud AI isolation.
- If Local Ollama is unreachable when cloud egress is barred, the router automatically fails over to `DeterministicAIProvider`, maintaining system availability without compromising confidentiality.

