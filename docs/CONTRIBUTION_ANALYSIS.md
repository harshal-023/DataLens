# Deterministic Contribution & Driver Decomposition

## Overview
The `DriverEngine` decomposes macro metric shifts into underlying dimensional contributors, mathematically reconciling 100% of the variance.

## Mathematical Reconciliation
For any metric $M$ observed between period $t-1$ and $t$ with dimensional breakdown segments $s \in S$:
$$\Delta_{\text{total}} = M_t - M_{t-1}$$
$$\Delta_s = M_{t, s} - M_{t-1, s}$$
$$\sum_{s \in S} \Delta_s \equiv \Delta_{\text{total}}$$
$$\text{Reconciliation Variance} = \left| \Delta_{\text{total}} - \sum_{s \in S} \Delta_s \right| = 0.0$$

The engine guarantees exact zero-residual reconciliation. Individual segment contributions are ranked by absolute magnitude of delta.

## Neutral Language Governance
To prevent hallucinated causal claims and misleading executive assertions, the `DriverEngine` enforces strict linguistic guidelines:

- **Approved Phrases**:
  - *"The net change was concentrated in [Segment], which shifted by $\Delta$..."*
  - *"The variance correlated primarily with movement in [Segment]..."*
  - *"[Segment] contributed $\Delta$ of the overall $\Delta_{\text{total}}$ movement."*

- **Prohibited Causal Assertions**:
  - ❌ *"The decline was caused by [Segment]."*
  - ❌ *"[Segment] drove the downfall of quarterly profits."*
  - ❌ *"Due to mistakes in [Segment], overall targets failed."*

