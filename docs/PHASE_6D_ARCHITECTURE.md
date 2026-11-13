# Phase 6D: AI Business Analyst Architecture

## Executive Overview
Phase 6D transforms DataLens from an ad-hoc conversational query tool into an autonomous AI Business Analyst. The system proactively scans datasets, identifies meaningful trends, isolates statistical anomalies, highlights operational and financial risks, surfaces revenue and margin opportunities, computes deterministic driver decompositions, and delivers grounded, evidence-backed narratives.

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                      AI Business Analyst Center                        │
│             Executive Overview | Trends | Anomalies | Risks            │
│            Opportunities | Detail Drawer | Lifecycle Controls          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ REST APIs (/api/v1/business-analyst)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        BusinessInsightEngine                           │
│  - Multi-category scan (Performance, Trends, Anomalies, Risks, Opps)   │
│  - Deduplication fingerprinting (SHA-256)                              │
│  - Composite prioritization & confidence scoring                       │
│  - Lifecycle management & assessment audit trail                       │
└──────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────┘
       │             │             │             │             │
       ▼             ▼             ▼             ▼             ▼
┌────────────┐┌────────────┐┌────────────┐┌────────────┐┌────────────┐
│TrendEngine ││Anomaly     ││ RiskEngine ││Opportunity ││DriverEngine│
│- MoM, QoQ  ││Engine      ││- Concentr. ││Engine      ││- Variance  │
│- YoY       ││- Z-score   ││- Margins   ││- High-Grwth││  decomp.   │
│- Sustained ││- IQR       ││- Cost infl.││- Expansion ││- Neutral   │
│  growth    ││- IsoForest ││            ││  signals   ││  language  │
└──────┬─────┘└──────┬─────┘└──────┬─────┘└──────┬─────┘└──────┬─────┘
       │             │             │             │             │
       └─────────────┴─────────────┼─────────────┴─────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │       ExplanationEngine       │
                   │ - AIProviderFactory routing   │
                   │ - Fact/inference separation   │
                   │ - Zero raw row transmission   │
                   │ - Hallucination citation guard│
                   └───────────────────────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │    PostgreSQL & DuckDB        │
                   │ - 7 Schema tables & indexes   │
                   │ - Parquet columnar execution  │
                   └───────────────────────────────┘
```

## Key Architectural Principles
1. **Zero Hallucination Verification**: All findings are computed by deterministic engines over DuckDB columnar storage. The AI explanation layer is restricted to interpreting validated evidence. All cited numbers must match calculated metrics.
2. **Data Privacy Guard**: Raw dataset records are never transmitted to cloud LLMs. Restricted or Confidential datasets strictly enforce local-only execution (Ollama or deterministic fallback).
3. **Traceability & Neutral Language**: Segment driver decompositions reconcile mathematically to 100% of the variance. Narratives maintain rigorous neutrality ("concentrated in", "correlated with"), forbidding unfounded causal claims ("caused by").

