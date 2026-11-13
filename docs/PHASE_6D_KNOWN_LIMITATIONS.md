# Phase 6D Known Limitations & Architectural Scope Boundaries

## 1. Scope Boundary Enforcement
In strict compliance with development instructions, Phase 6D focuses exclusively on the autonomous AI Business Analyst, trend discovery, anomaly intelligence, risk/opportunity detection, variance decomposition, grounding guardrails, insight lifecycle, and scheduled background sweeps.

**Phase 6E (Predictive Forecasting, Scenario Simulation & Prescriptive What-If Modeling) has NOT been started.**

## 2. Technical Limitations & Future Considerations
1. **Univariate Time-Series Focus**:
   - The current `TrendEngine` primarily evaluates single-metric trajectories over uniform temporal buckets. Irregularly spaced event series or high-frequency streaming events are aggregated to hourly/daily intervals prior to evaluation.
2. **Cardinality Thresholds on Decompositions**:
   - `DriverEngine` decomposes variance across dimensions with up to 100 distinct categories. For dimensions with $>100$ distinct values (e.g., individual customer IDs), the engine groups the top 20 by absolute delta and aggregates remaining members into an `"Other / Long-Tail"` segment to preserve executive readability and prevent combinatorial explosion.
3. **Local AI Model Hardware Requirements**:
   - When workspace privacy policy enforces `local_only_enforced = True`, Ollama must be operational on the host machine. If Ollama is offline or unconfigured, the system automatically falls back to `DeterministicAIProvider` to guarantee uninterrupted operational insight delivery without transmitting data to cloud LLMs.
4. **Historical Lookback Window**:
   - Default trend sweeps inspect the most recent 12 completed periods (e.g., 12 months or 12 quarters). Datasets with fewer than 3 historical periods will omit sustained multi-period trajectory classifications.

