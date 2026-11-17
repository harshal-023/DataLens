# DataLens – Widget Color Customization Guide

**Document:** `WIDGET_COLOR_CUSTOMIZATION.md`  
**Components:** `src/components/dashboards/DashboardThemes.ts`, `src/components/dashboards/WidgetVisualizations.tsx`, `src/components/dashboards/DashboardWidgetCard.tsx`

---

## 1. Overview

DataLens widgets now feature deep color customization that empowers users to style individual charts and KPI cards to match executive slide decks, brand books, or personal preferences.

Customization is supported at two levels:
1. **7 Curated Color Palettes**: Harmonious gradient families optimized for visual readability and contrast.
2. **Custom Hex Accent Color**: Arbitrary hex color picker (`#RRGGBB`) with automatic complementary tone generation.

---

## 2. The 7 Curated Color Palettes

| Palette ID | Name | Theme Mood | Primary Color | Pastel Wash (KPI) | Swatch Colors |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ocean` | **Ocean (Default)** | DataLens Teal & Navy | `#009F98` | `#EDF8F7` (Mint) | `#009F98`, `#39C3B8`, `#102C46`, `#8BE5DE`, `#1D4664`, `#007D78` |
| `sunset` | **Sunset** | Warm Coral & Amber | `#F97316` | `#FEF7EC` (Peach) | `#F97316`, `#F59E0B`, `#F43F5E`, `#FDBA74`, `#FACC15`, `#EA580C` |
| `forest` | **Forest** | Emerald & Sage Greens | `#10B981` | `#ECFDF5` (Mint Green) | `#10B981`, `#34D399`, `#059669`, `#047857`, `#84CC16`, `#065F46` |
| `royal` | **Royal** | Purple, Violet & Lavender | `#8B5CF6` | `#F6F0FA` (Lavender) | `#8B5CF6`, `#6366F1`, `#A855F7`, `#C084FC`, `#4C1D95`, `#7C3AED` |
| `business` | **Business** | Corporate Blue & Navy | `#2563EB` | `#EDF5FB` (Sky Blue) | `#2563EB`, `#1E40AF`, `#3B82F6`, `#60A5FA`, `#1E293B`, `#475569` |
| `vibrant` | **Vibrant** | Multi-Color Dynamic Rainbow | `#009F98` | `#EDF8F7` (Mint) | `#009F98`, `#8B5CF6`, `#F59E0B`, `#EC4899`, `#10B981`, `#3B82F6` |
| `monochrome` | **Monochrome** | Minimalist Greys & Charcoal | `#334155` | `#F8FAFC` (Slate Tint) | `#0F172A`, `#334155`, `#475569`, `#64748B`, `#94A3B8`, `#CBD5E1` |

---

## 3. KPI Card Pastel Wash Architecture

As demonstrated in the primary reference image, KPI cards look significantly more professional with gentle pastel background washes rather than plain white rectangles:

- **Sales / Revenue / Profit:** Mint pastel wash (`#EDF8F7`) with teal circular icon badge.
- **Orders / Transactions:** Sky Blue pastel wash (`#EDF5FB`) with blue circular icon badge.
- **Customers / Users / Leads:** Peach pastel wash (`#FEF7EC`) with amber circular icon badge.
- **Averages / Rates / Percentages:** Lavender pastel wash (`#F6F0FA`) with violet circular icon badge.

Users can also override the wash color using the widget's appearance settings.

---

## 4. Quick Color Palette Switcher in Edit Mode

In Edit Mode, users do not need to re-open the entire wizard just to tweak widget colors:
1. Click the **3-dots menu** on any chart card.
2. Hover or click **"Color Theme"**.
3. A quick swatch popup reveals all 7 palette bubbles.
4. Clicking any swatch instantly recalculates chart colors and auto-saves the update.

---

## 5. Storage & Backward Compatibility

Palette settings are stored inside `widget.display_settings` as:
```json
{
  "unit": "₹",
  "color_palette": "sunset",
  "custom_color": "#F97316",
  "wash_color": "#FEF7EC",
  "show_legend": true,
  "show_labels": true
}
```
Existing widgets without a specified palette seamlessly fallback to the signature DataLens `ocean` palette with zero data migrations required.

