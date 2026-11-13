# Business Risk Detection

## Overview
The `RiskEngine` scans dataset segments to uncover enterprise vulnerabilities before they become critical financial or operational incidents.

## Key Risk Detection Vectors

### 1. Revenue & Customer Concentration Risk
- **Rule**: If a single customer, account, or regional segment accounts for $> 25\%$ of total organization revenue, a `HIGH` priority risk is registered.
- **Critical Threshold**: If a single customer accounts for $> 50\%$ of total revenue, a `CRITICAL` priority risk is emitted with immediate executive attention warnings.
- **Herfindahl-Hirschman Index (HHI)**: Computes market concentration across customer accounts:
  $$\text{HHI} = \sum_{i=1}^N s_i^2$$
  where $s_i$ is the percentage revenue share of entity $i$.

### 2. Negative Gross & Operating Margins
- **Rule**: Isolates any SKU, product line, customer contract, or regional operating unit where:
  $$\text{Margin \%} = \frac{\text{Revenue} - \text{Cost}}{\text{Revenue}} \times 100 < 0$$
- Emits root-cause breakdown identifying whether negative margins stem from excessive discounting or inflated supplier costs.

### 3. Accelerated Cost Inflation
- **Rule**: Flags any cost line item expanding at $> 1.5\times$ the rate of associated revenue growth across the same temporal window:
  $$\Delta_{\text{Cost \%}} > 1.5 \times \Delta_{\text{Revenue \%}} \quad (\text{with } \Delta_{\text{Cost \%}} > 10\%)$$

