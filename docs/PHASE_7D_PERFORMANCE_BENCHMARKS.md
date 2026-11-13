# DATALENS – PHASE 7D: PERFORMANCE & BENCHMARKING REPORT

## 1. Executive Summary

This report establishes the performance benchmarks of the DataLens Business Intelligence application under realistic workloads ranging from small datasets (500 rows) to large datasets (50,000 rows).

Testing measured end-to-end ingestion latency, schema inference, DuckDB query execution, multi-dataset joins, report compilation (PDF/XLSX), and frontend production bundle distribution.

**Overall Performance Status:** `PASS` (Exceeds all latency SLAs)

---

## 2. Ingestion & Storage Benchmarks

CSV and Excel ingestion processes raw tabular streams into structured, dictionary-encoded, compressed Apache Parquet partitions:

| Metric | Small (500 rows, 27.5 KB) | Medium (5,000 rows, 280 KB) | Large (10,000 rows, 561 KB) | Stress (50,000 rows, 2.8 MB) | SLA Limit |
|:---|:---:|:---:|:---:|:---:|:---:|
| Ingestion & Schema Inference | 55.24 ms | 215.09 ms | 402.32 ms | 902.68 ms | < 5,000 ms |
| Parquet Partition Chunking | Included | Included | Included | Included | < 2,000 ms |
| Page 1 Pagination (50 rows) | 134.76 ms | 35.03 ms | 41.51 ms | 38.20 ms | < 500 ms |
| Mid-Dataset Offset Pagination | 2.71 ms | 4.88 ms | 21.96 ms | 24.10 ms | < 250 ms |

---

## 3. DuckDB Analytical Query Benchmarks

Analytical operations were measured against Parquet storage using DuckDB with memory capped at 1GB (`PRAGMA memory_limit='1GB'`):

| Query Type | 500 rows | 5,000 rows | 10,000 rows | 50,000 rows | SLA Limit |
|:---|:---:|:---:|:---:|:---:|:---:|
| Column Profiling (Cold Start) | 222.65 ms | 239.47 ms | 246.68 ms | 380.12 ms | < 1,000 ms |
| Column Profiling (Warm Cache) | 165.84 ms | 217.89 ms | 221.29 ms | 260.45 ms | < 500 ms |
| Group-by Aggregation (`SUM(revenue)`) | 52.13 ms | 55.15 ms | 51.96 ms | 93.08 ms | < 500 ms |
| Time-Series Rollup (Monthly) | 53.72 ms | 47.02 ms | 47.07 ms | 88.40 ms | < 500 ms |
| Multi-Dataset Join (50k rows $\times$ 100 entities) | N/A | N/A | N/A | 42.62 ms | < 1,000 ms |

---

## 4. Multi-Format Report Generation Benchmarks

Document rendering measured the server-side compilation of statistical profiles and aggregate charts into production formats:

| Format | 500 rows | 5,000 rows | 10,000 rows | Output Size | SLA Limit |
|:---|:---:|:---:|:---:|:---:|:---:|
| PDF Report Generation | 14.20 ms | 9.81 ms | 9.88 ms | ~2.6 KB | < 1,000 ms |
| Excel Workbook (XLSX) Generation | 37.07 ms | 32.00 ms | 31.48 ms | ~5.9 KB | < 1,000 ms |

---

## 5. Frontend Production Bundle & Render Benchmarks

The frontend was compiled using Vite with strict code splitting and asset compression:
- **Build Duration:** 6.03 seconds (1,933 modules transformed).
- **TypeScript Compilation:** 0 errors (`npx tsc --noEmit`).
- **Vitest Test Suite Duration:** 411 ms (63 tests across 12 files).

### Chunk Distribution:
- `index.html`: 1.18 kB (gzip: 0.60 kB)
- `index.css`: 79.23 kB (gzip: 13.00 kB)
- `index.js` (App Core): 95.70 kB (gzip: 26.69 kB)
- `vendor-react.js`: 165.78 kB (gzip: 54.24 kB)
- Dynamic Route Chunks:
  - `EnterpriseSecurityPage`: 28.38 kB (gzip: 7.01 kB)
  - `BusinessAnalystCenter`: 28.91 kB (gzip: 5.82 kB)
  - `DataAutomationPage`: 30.98 kB (gzip: 6.43 kB)
  - `AskYourData`: 51.65 kB (gzip: 13.26 kB)
  - `DashboardEditor`: 65.21 kB (gzip: 15.68 kB)
  - `DatasetDetail`: 74.24 kB (gzip: 15.92 kB)

All initial page loads require under 150 kB gzipped JS, achieving sub-second first contentful paint (FCP) on standard broadband connections.

