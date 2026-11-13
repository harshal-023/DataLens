# AI Insight Grounding & Verification Guardrails

## Overview
The `ExplanationEngine` bridges calculated mathematical facts and natural-language executive interpretations. It incorporates multiple protective mechanisms to eliminate AI hallucinations and protect confidential business data.

## Protective Architecture

```
┌────────────────────────────────────────────────────────┐
│           Deterministic Mathematical Evidence          │
│   (Metrics, Baselines, Deltas, Ranks, Decompositions)  │
└──────────────────────────┬─────────────────────────────┘
                           │ Zero Raw Rows Transmitted
                           ▼
┌────────────────────────────────────────────────────────┐
│           Workspace AI Privacy Policy Filter           │
│  - CONFIDENTIAL / RESTRICTED ➔ Local Only (Ollama)     │
│  - Allow Samples = False ➔ Zero individual records     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Structured Prompt Formulation            │
│   - Provides ONLY computed aggregate metrics & deltas  │
│   - Temperature <= 0.2                                 │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│         NLAEvidenceVerifier Hallucination Guard        │
│  - Extracts all numbers, percentages & currencies      │
│  - Compares citations against verified evidence cards  │
│  - If citation unverified ➔ REJECT & FALLBACK          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           Final Grounded Executive Narrative           │
│  [Observed Fact] + [Business Inference] + [Action]     │
└────────────────────────────────────────────────────────┘
```

## Grounding Rules
1. **Fact Separation**: Every insight narrative distinguishes between:
   - **Observed Fact**: Directly computed values (e.g., *"West region revenue declined from $40,000 to $25,000 (-37.5%)."*).
   - **Business Inference**: AI contextualization (e.g., *"This margin contraction reflects a pricing tier shift."*).
2. **Rejection Policy**: If an LLM response cites a numeric percentage or amount not present in the evidence cards, `ExplanationEngine` logs a warning and automatically falls back to deterministic rule-based phrasing.

