# Autonomous Business Insight Engine

## Overview
The `BusinessInsightEngine` serves as the primary autonomous coordinator for Phase 6D. It periodically evaluates business datasets or executes on-demand to surface prioritized findings across five key categories:
1. **Performance**: Top-line KPI movements against historical benchmarks.
2. **Trends**: Period-over-period direction, sustained trajectory, and velocity changes.
3. **Anomalies**: Statistical outliers isolated via IQR, Z-Score, or Isolation Forests.
4. **Risks**: Customer concentration, negative profit margins, and rapid cost acceleration.
5. **Opportunities**: High-margin segment expansion, under-indexed accounts, and accelerated growth vectors.

## Scoring & Prioritization Matrix
Every insight generated is assigned a multi-factor priority score:
$$\text{Priority Score} = w_m \cdot S_{\text{magnitude}} + w_c \cdot S_{\text{confidence}} + w_u \cdot S_{\text{urgency}}$$

| Priority Level | Score Range | Default Action | SLA Notification |
|---|---|---|---|
| **CRITICAL** | 85 - 100 | Immediate executive review & investigation | Real-time workspace alert |
| **HIGH** | 70 - 84 | Operating review within current cycle | Weekly digest summary |
| **MEDIUM** | 50 - 69 | Metric owner notification | Dashboard notification badge |
| **LOW** | 30 - 49 | Logged for trend tracking | In-page table only |
| **INFORMATIONAL** | 0 - 29 | Background historical benchmark | Filtered by default |

## Deduplication & Idempotency Fingerprinting
To avoid alert fatigue and repeated duplicate notifications across recurring runs, each insight generates a deterministic SHA-256 fingerprint:
$$\text{Fingerprint} = \text{SHA256}(\text{DatasetVersionID} \,\|\, \text{Category} \,\|\, \text{Metric} \,\|\, \text{Segment} \,\|\, \text{FindingType})[:32]$$
If an active insight with the same fingerprint exists in `NEW`, `REVIEWED`, or `INVESTIGATING` status, the existing insight's timestamp and observed value are refreshed rather than creating duplicate rows.

