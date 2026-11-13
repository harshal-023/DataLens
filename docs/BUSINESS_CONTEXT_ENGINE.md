# Business Context Engine

## 1. Overview
The [`BusinessContextEngine`](file:///d:/PE%20CP/backend/app/services/intelligence/business_context_service.py) classifies uploaded datasets into business domains, infers core analytical purposes, identifies key business entities, and suggests domain-specific KPIs.

---

## 2. Business Domains Supported

1. **`SALES`**: Retail, wholesale, e-commerce, transaction logs (Signals: `revenue`, `order`, `sales`, `price`, `discount`, `quantity`, `customer`, `product`).
2. **`FINANCE`**: Financial ledgers, P&L statements, balance sheets (Signals: `expense`, `profit`, `margin`, `tax`, `budget`, `ledger`, `asset`, `liability`, `cogs`).
3. **`MARKETING`**: Campaigns, digital advertising, lead generation (Signals: `campaign`, `impressions`, `clicks`, `ctr`, `conversion`, `spend`, `leads`, `cpc`, `cpa`).
4. **`CUSTOMER_ANALYTICS`**: Retention, cohorts, customer satisfaction (Signals: `churn`, `retention`, `ltv`, `lifetime_value`, `nps`, `segment`, `satisfaction`).
5. **`OPERATIONS`**: Help desk, support ticketing, incident management (Signals: `incident`, `ticket`, `sla`, `resolution_time`, `uptime`, `downtime`, `throughput`).
6. **`INVENTORY`**: Warehousing, stock levels, supply chain (Signals: `stock`, `inventory`, `warehouse`, `reorder`, `quantity_on_hand`, `sku`, `supplier`).
7. **`HUMAN_RESOURCES`**: Employee rosters, payroll, headcount (Signals: `employee`, `salary`, `hire_date`, `attrition`, `department`, `headcount`).
8. **`LOGISTICS`**: Shipping, freight, dispatch (Signals: `shipment`, `delivery`, `carrier`, `freight`, `tracking`, `transit_time`).
9. **`GENERAL_BUSINESS`**: Default baseline when no specific domain keywords dominate.

---

## 3. Automated Context Generation

For each analyzed `DatasetVersion`, the engine constructs a structured business context:
- **`business_domain`**: The classified business domain.
- **`purpose`**: An executive summary describing what the records represent.
- **`important_entities`**: Key entities identified in the dataset (e.g. `Customer`, `Order`, `Product`, `Employee`).
- **`key_dimensions`**: Top categorical, temporal, and geographic dimensions for slicing and dicing.
- **`important_measures`**: Primary continuous numeric fields suitable for aggregation.
- **`suggested_kpis`**: Pre-configured formulas tailored to the domain (e.g. `Total Revenue`, `Total Orders`, `Average Order Value`).
- **`business_assumptions`**: Safe execution assumptions (e.g. currency standards, null handling).

---

## 4. User Modification & Confirmation
The business context is marked as `is_user_confirmed = False` initially. In the **Business Context** tab of the Dataset Intelligence Center, users can edit the domain or adjust the analytical purpose. Once saved, `is_user_confirmed` is set to `True`, preventing subsequent profiler runs from overriding the user's customized context.

