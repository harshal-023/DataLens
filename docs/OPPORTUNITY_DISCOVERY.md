# Opportunity Discovery

## Overview
The `OpportunityEngine` autonomously discovers expansion vectors, high-margin segments, and above-baseline performance signals across enterprise datasets.

## Opportunity Detection Strategies

### 1. High-Growth Product & Segment Discovery
- Evaluates individual dimension breakdown items (e.g., product lines, customer tiers, geographic regions) against organizational averages.
- Flags any segment growing at $> 2\times$ the overall category growth rate with at least 5% total share contribution:
  $$g_{\text{segment}} \ge 2 \times g_{\text{total}} \quad \text{and} \quad \text{Share}_{\text{segment}} \ge 5\%$$
- Highlights momentum catalysts for commercial investment.

### 2. High-Margin Expansion Vectors
- Identifies product lines, service categories, or regional channels demonstrating margins $\ge 15$ percentage points above the overall business baseline:
  $$\text{Margin}_{\text{segment}} \ge \text{Margin}_{\text{overall}} + 15\%$$
- Recommends capital reallocation or marketing investment to expand high-margin mix.

### 3. Untapped Customer Expansion
- Segments accounts with high transaction frequency but low basket value, suggesting upsell or bundling opportunities.

