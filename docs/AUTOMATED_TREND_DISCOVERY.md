# Automated Trend Discovery

## Overview
The `TrendEngine` systematically analyzes approved metrics across temporal dimensions (daily, weekly, monthly, quarterly) without requiring user prompts.

## Core Capabilities
1. **Period-over-Period Delta Calculation**:
   - Month-over-Month (MoM):
     $$\Delta_{\text{MoM}} = \frac{V_t - V_{t-1}}{V_{t-1}} \times 100$$
   - Quarter-over-Quarter (QoQ): Compares current quarter against the immediate prior quarter.
   - Year-over-Year (YoY): Compares current period against the identical seasonal period in the prior year.

2. **Zero Baseline & Infinite Growth Handling**:
   - When the baseline $V_{t-1} = 0$:
     - If $V_t > 0$: Returns `delta_pct = None` with formatted label `"New metric baseline established ($V_t)"` rather than producing division-by-zero errors or false $+\infty\%$.
     - If $V_t = 0$: Returns `delta_pct = 0.0%`.

3. **Sustained Trajectory Detection**:
   - Flags metrics showing 3 or more consecutive periods of mono-directional growth or decline.
   - Assigns sustained compound velocity flags (`SUSTAINED_EXPANSION` or `SUSTAINED_CONTRACTION`).
   - Surfaces statistical slope and $R^2$ fit confidence alongside the primary delta.

