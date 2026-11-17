# DataLens – Dashboard Theme & Appearance Settings Guide

**Document:** `DASHBOARD_THEME_SETTINGS.md`  
**Components:** `src/components/dashboards/DashboardThemes.ts`, `src/components/dashboards/DashboardThemeModal.tsx`, `src/pages/dashboards/DashboardEditor.tsx`

---

## 1. Overview

DataLens dashboards support 5 full-canvas themes that style the dashboard background canvas, widget cards, headers, borders, and typography.

Themes allow teams to adapt dashboards for different viewing environments:
- Daytime conference room presentations (**Clean Light** / **Minimal White**).
- Prolonged analytical workstations (**Soft Grey**).
- Command center NOC screens and dark-mode displays (**Midnight**).
- Executive marketing and product reviews (**Ocean**).

---

## 2. The 5 Dashboard Theme Presets

### 1. Clean Light (Default)
- **Canvas Background:** `#F5F8FA` (Cool Soft White)
- **Card Background:** `#FFFFFF` (Pure White)
- **Border Color:** `#DCE5EB` (Crisp Light Slate)
- **Primary Text:** `#102C46` (Deep Navy)
- **Muted Text:** `#52616C` (Slate)
- **Accent:** `#009F98` (Peacock Teal)
- **Best For:** General business intelligence, executive reporting, and print exports.

### 2. Soft Grey
- **Canvas Background:** `#ECEFF2` (Neutral Slate Grey)
- **Card Background:** `#F8FAFC` (Off-white)
- **Border Color:** `#CBD5E1` (Muted Slate)
- **Primary Text:** `#0F172A` (Slate 900)
- **Muted Text:** `#475569` (Slate 600)
- **Accent:** `#0284C7` (Sky Blue)
- **Best For:** Reduced glare and eye fatigue during all-day monitoring.

### 3. Midnight (Dark Mode)
- **Canvas Background:** `#0B1926` (Deep Navy Black)
- **Card Background:** `#132537` (Dark Navy Blue)
- **Border Color:** `#1F3851` (Midnight Border)
- **Primary Text:** `#F1F5F9` (Crisp White)
- **Muted Text:** `#94A3B8` (Light Slate)
- **Accent:** `#38BDF8` (Luminous Sky Blue)
- **Best For:** Operations control rooms, high-contrast wall displays, and developer preference.

### 4. Ocean
- **Canvas Background:** `#EBF5F6` (Aquatic Light Wash)
- **Card Background:** `#FFFFFF` (White)
- **Border Color:** `#BBDCE8` (Soft Cyan Border)
- **Primary Text:** `#0E3B43` (Deep Teal Black)
- **Muted Text:** `#3C6D77` (Teal Slate)
- **Accent:** `#009F98` (Peacock Teal)
- **Best For:** Highlighting DataLens brand aesthetics with a fresh aquatic tone.

### 5. Minimal White
- **Canvas Background:** `#FFFFFF` (Flat White)
- **Card Background:** `#FFFFFF` (Pure White)
- **Border Color:** `#F1F5F9` (Hairline Border)
- **Primary Text:** `#111827` (Charcoal)
- **Muted Text:** `#6B7280` (Cool Grey)
- **Accent:** `#111827` (Monochrome Black)
- **Best For:** Clean paper-like aesthetic, minimalist embedding, and board reports.

---

## 3. How Users Change Dashboard Themes

1. In the Dashboard header, click the **3-dots options menu** (`...`).
2. Select **"Dashboard Theme & Style"** (accompanied by a palette icon).
3. The **Dashboard Theme Modal** opens, showing preview cards with color bubbles and theme descriptions.
4. Clicking any theme immediately applies the theme tokens to the canvas and widget cards.
5. The choice is saved immediately to `dashboard.layout_config.theme` without requiring manual page reload.

---

## 4. Theme Persistence & API Architecture

Theme settings are saved via the existing `PUT /api/v1/workspaces/{workspace_id}/dashboards/{dashboard_id}` endpoint:
```json
{
  "layout_config": {
    "theme": "clean_light",
    "columns": 12,
    "gap": 16
  }
}
```
No database migrations were required, ensuring 100% stability and zero regression risk across versions.

