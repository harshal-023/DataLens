# DataLens – Global Collapsible Left Sidebar Report

**Document:** `DATALENS_GLOBAL_SIDEBAR_REPORT.md`  
**Components:** `src/components/layout/Sidebar.tsx`, `src/components/layout/AppLayout.tsx`

---

## 1. Overview & Requirements

The DataLens Global Left Sidebar is the primary navigation backbone of the application. To maximize canvas screen real estate for wide multi-column BI dashboards while maintaining instant access to core modules, the sidebar supports smooth collapsing and expanding with persistent user preferences.

---

## 2. Key Specifications & Metrics

| Attribute | Expanded State | Collapsed State |
| :--- | :--- | :--- |
| **Width** | `w-[280px]` | `w-[76px]` |
| **Transition Animation** | `transition-[width] duration-200 ease-in-out` | `transition-[width] duration-200 ease-in-out` |
| **Brand Display** | Full logo + "DATALENS BUSINESS INTELLIGENCE & REPORT GENERATOR" | Compact icon mark (`w-8 h-8 rounded-xl bg-gradient-to-br`) |
| **Navigation Links** | Icon + Full Text Label + Active Pill | Centered Icon + Dark Glass Hover Tooltip |
| **Workspace Pill** | Full "Pro Workspace" badge + progress bar ("12 / 50 Reports Used") | Mini crown icon badge with dark glass hover tooltip |
| **Toggle Trigger** | Dedicated chevron button with accessible tooltip (`aria-label`) | Dedicated chevron button with accessible tooltip (`aria-label`) |
| **Persistence** | `localStorage.getItem('datalens_sidebar_collapsed')` | `localStorage.setItem('datalens_sidebar_collapsed', 'true')` |

---

## 3. Dark Glass Hover Tooltip System

When the sidebar is collapsed to `76px`, navigation labels are visually hidden to preserve clean aesthetics. To ensure zero usability penalty, hovering over any navigation item renders a floating dark glass tooltip:

- **Styling:** `bg-[#102C46]/95 text-white text-xs font-semibold px-2.5 py-1.5 rounded-xl shadow-lg border border-white/10 backdrop-blur-md`
- **Positioning:** Floating to the right of the icon at `left-[76px]` with an animated fade-in.
- **Accessibility:** Includes `role="tooltip"` and corresponding `aria-label` attributes for screen readers.

---

## 4. Mobile Responsiveness

On mobile viewports (`< 768px`):
- The sidebar automatically converts into an overlay drawer.
- Sliding out over the content with a backdrop scrim (`bg-black/40 backdrop-blur-xs`).
- Selecting any navigation destination automatically dismisses the drawer to prevent screen obstruction.

---

## 5. Verification

- Tested toggling between 280px and 76px.
- Verified smooth 200ms easing without content flickering.
- Verified that refreshing the page retains the user's collapsed or expanded preference via `localStorage`.

