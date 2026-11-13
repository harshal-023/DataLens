# DataLens — Comparative Analytics & Benchmark Engine

This document outlines the comparative analytics architecture, benchmark modes, and numerical calculations implemented in Phase 4C.

---

## 1. Supported Comparison Modes

1. **Target vs Actual (`target`)**:
   - Compares measured metric against an explicit business quota or threshold.
   - Used heavily in KPI cards, Gauge meters, and Bar charts.
2. **Period-over-Period / Month-over-Month (`prior_period`)**:
   - Evaluates current performance relative to the preceding analytical window.
3. **Year-over-Year (`yoy`)**:
   - Calculates annual growth comparing equivalent historical timeframes.

---

## 2. Mathematical Rigor & Division-by-Zero Handling

Calculations strictly follow deterministic formulas executed via DuckDB / backend services:

### Absolute Difference ($\Delta$)
$$\Delta = \text{Actual} - \text{Benchmark}$$

### Percentage Change ($\% \Delta$)
$$\% \Delta = \begin{cases} 
\dfrac{\Delta}{|\text{Benchmark}|} \times 100\%, & \text{if } \text{Benchmark} \ne 0 \\[8pt]
+100\%, & \text{if } \text{Benchmark} = 0 \text{ and } \Delta > 0 \\[8pt]
-100\%, & \text{if } \text{Benchmark} = 0 \text{ and } \Delta < 0 \\[8pt]
0\%, & \text{if } \text{Benchmark} = 0 \text{ and } \Delta = 0 
\end{cases}$$

### Directional Status
- `direction = "up"` if $\Delta > 0$
- `direction = "down"` if $\Delta < 0$
- `direction = "flat"` if $\Delta = 0$

---

## 3. Visual Representation

- **Pill Badges**: Displayed beside KPI headline values with $\uparrow$ or $\downarrow$ icons.
- **Color Coding**:
  - Growth / Target Exceeded: Vibrant Peacock Teal (`#009F98`)
  - Drop / Deficit: Coral Red (`#A63838`)
  - Neutral / On Par: Slate Muted (`#52616C`)

