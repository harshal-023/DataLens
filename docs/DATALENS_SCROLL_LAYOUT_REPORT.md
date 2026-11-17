# DataLens – Independent Scrolling Architecture Report

**Document:** `DATALENS_SCROLL_LAYOUT_REPORT.md`  
**Components:** `src/components/layout/AppLayout.tsx`, `src/pages/dashboards/DashboardEditor.tsx`, `src/pages/ask/AskYourData.tsx`

---

## 1. Objective & Problem Statement

In standard web applications, a single outer browser scrollbar handles all vertical scrolling. When building complex Business Intelligence dashboards and conversational AI interfaces, this causes severe UX degradation:
- Scrolling down causes the top navigation bar, dashboard filters, and AI prompt input to scroll off-screen.
- Users lose access to critical context (e.g. active filters, widget selectors, prompt composers) and must constantly scroll back to the top.
- Dual outer and inner scrollbars create "scroll trapping" and jarring page jumps.

---

## 2. Independent Scrolling Solution Architecture

DataLens implements an **Independent Module Scrolling Architecture** using CSS Flexbox constraints and strict container clipping:

```
┌────────────────────────────────────────────────────────────────────────┐
│ AppLayout: 100vh, overflow-hidden                                      │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Fixed Top Navbar (w-full, h-16, shrink-0)                          │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌───────────────────────┬────────────────────────────────────────────┐ │
│ │ Global Left Sidebar   │ Main Content Container                     │ │
│ │ Fixed width:          │ (flex-1 min-h-0 overflow-hidden)           │ │
│ │ expanded: 280px       │ ┌────────────────────────────────────────┐ │ │
│ │ collapsed: 76px       │ │ Stationary Header & Filter Bar         │ │ │
│ │ Stationary / Pinned   │ ├───────────────────────┬────────────────┤ │ │
│ │                       │ │ Canvas Scroll Area    │ Stationary     │ │ │
│ │                       │ │ (overflow-y-auto      │ Docked Panel   │ │ │
│ │                       │ │  min-h-0 flex-1)      │ (w-[230px])    │ │ │
│ │                       │ │ [Row 1: KPI Cards]    │ [Add Widget]   │ │ │
│ │                       │ │ [Row 2: Charts]       │                │ │ │
│ └───────────────────────┴─┴───────────────────────┴────────────────┴─┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Details by Module

### A. Global Shell (`AppLayout.tsx`)
- Container sets `h-screen overflow-hidden flex flex-col`.
- Detects independent scroll routes (`/dashboards`, `/dashboard`, `/ask`).
- For these routes, main container applies `h-full flex flex-col min-h-0 overflow-hidden`.
- For standard administrative pages (Settings, Workspace Members), it falls back to standard `overflow-y-auto`.

### B. Analytics & Dashboards (`DashboardEditor.tsx`)
- **Stationary Elements**:
  - Section title.
  - Dashboard Header Card (Title, Dataset metadata, View/Edit pill, Share, Export, 3-dots).
  - Filter Bar (`DashboardFilterBar` with Date Range, Region, Product).
  - Active Cross-Filters banner.
  - Docked right "Add Widget" pastel panel.
- **Scrollable Canvas**:
  - The middle canvas grid has `flex-1 min-h-0 overflow-y-auto pr-2 pb-16`.
  - Only the KPI cards and chart widgets scroll. The user never loses access to the filter bar or Add Widget tiles.

### C. Ask AI Conversation (`AskYourData.tsx`)
- **Stationary Elements**:
  - Top header (Active dataset, Token latency, Clear chat, Export buttons).
  - Left conversation history sidebar (Panel 1).
  - Right dataset intelligence & suggested questions sidebar (Panel 3).
  - Docked question composer at the bottom with quick suggestions.
- **Scrollable Elements**:
  - Middle message history container (`flex-1 min-h-0 overflow-y-auto p-4 space-y-4`).
  - Chat history scrolls fluidly while the prompt composer remains anchored at the bottom, exactly like ChatGPT and Gemini mobile apps.

---

## 4. Verification

- Tested across desktop viewports (1920x1080, 1440x900, 1280x800).
- Verified zero body scrollbar appearance.
- Verified that keyboard navigation and mouse wheel interactions scroll internal canvas elements smoothly without outer window jumping.

