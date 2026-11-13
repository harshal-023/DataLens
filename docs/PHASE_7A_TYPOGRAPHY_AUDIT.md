# Phase 7A: Global Typography Audit & Hierarchy Standardization

## 1. Typography System Overview
The DataLens application adheres to a dual-font typographic hierarchy designed for enterprise business intelligence:
1. **Primary Sans-Serif (`Inter`, system-ui, -apple-system, Roboto, sans-serif)**:
   - Used for all operational UI, controls, tables, buttons, inputs, navigation, badges, tooltips, and body text.
   - High legibility at small sizes (11px to 14px) with robust tabular figure rendering.
2. **Executive Serif (`DM Serif Display`, Playfair Display, Georgia, serif)**:
   - Used exclusively for executive hero headers on key landing pages (`OverviewDashboard`, `AskYourData`, `DataStudio`, `ReportsLibrary`, `BusinessAnalystCenter`, `SettingsPage`, and Auth hero banners).
   - Conveys authoritative, publication-grade executive reporting.

---

## 2. Heading Hierarchy & Standardization

| Level | Font Family | Size / Leading | Weight | Color | Usage Context |
|---|---|---|---|---|---|
| **Executive Hero (H1)** | `font-serif` | `text-2xl sm:text-3xl` / `tracking-tight` | `font-normal` or `font-semibold` | `#102C46` | Primary landing page headers on executive dashboards. |
| **Operational Page Title (H1)** | `font-sans` | `text-2xl` / `tracking-tight` | `font-bold` | `#102C46` | Tool and configuration pages (`PromptLab`, `DataSources`, `Governance`, `Automation`). |
| **Section Header (H2)** | `font-sans` | `text-lg` or `text-xl` | `font-bold` | `#102C46` | Card headers, modal titles, drawer headers, tab panels. |
| **Subsection Header (H3)** | `font-sans` | `text-sm` or `text-base` | `font-semibold` | `#102C46` | Widget titles, form section labels, parameter groupings. |
| **Card / Widget Label** | `font-sans` | `text-xs` / `uppercase tracking-wider` | `font-bold` | `#52616C` | Micro-labels, KPI card metrics, status category tags. |

---

## 3. Secondary Text & Contrast Compliance
- **Body Text**: `text-sm text-[#102C46]` or `text-[#35434F]` on white surfaces. Contrast ratio $\ge 7.1:1$ (exceeds WCAG AAA requirement).
- **Secondary / Helper Text**: Standardized to `text-xs text-[#52616C]` (Warm Grey/Slate). Contrast ratio $\ge 4.6:1$ against `#FFFFFF` and `#F8FAFC` (exceeds WCAG AA requirement).
- **Muted Metadata / Timestamps**: `text-[11px] text-[#8A99A6]`.
- **Negative Finding Fixed**: Eliminated unreadable dark olive body text (`color: #252720`) in `src/index.css`, replacing it with crisp DataLens Deep Navy `#102C46`.

---

## 4. Component Typography Standard

### Buttons
- **Primary Button**: `text-xs font-semibold tracking-wide text-white bg-[#009F98] hover:bg-[#007D78]`.
- **Secondary Button**: `text-xs font-semibold text-[#102C46] bg-white border border-[#DCE5EB] hover:bg-[#F5F8FA]`.
- **Ghost / Link Button**: `text-xs font-medium text-[#009F98] hover:underline`.

### Tables
- **Header Row (`<th>`)**: `text-xs font-semibold text-[#52616C] uppercase tracking-wider bg-[#F5F8FA] px-4 py-3 border-b border-[#DCE5EB]`.
- **Data Cell (`<td>`)**: `text-xs text-[#102C46] px-4 py-3 border-b border-[#F1F5F9] font-normal`.
- **Numerical Values**: `font-mono` alignment for quantities, currencies, and percentages to ensure vertical column alignment.

### Badges & Status Chips
- `text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider`.
- Clear semantic foreground/background pairings (`bg-emerald-50 text-emerald-700`, `bg-amber-50 text-amber-700`, `bg-rose-50 text-rose-700`, `bg-[#009F98]/20 text-[#007D78]`).

