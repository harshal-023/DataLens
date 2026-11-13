# DataLens — Interactive Cross-Filtering Engine

This document describes the cross-filtering architecture and interactive mechanics implemented in DataLens Phase 4C.

---

## 1. Overview & User Experience

Cross-filtering allows any interactive chart or tabular widget to act as a dynamic filter for all other widgets on the dashboard.

When a user selects an element (e.g. clicking "Electronics" in a Category Bar Chart):
1. An active cross-filter is registered: `category = 'Electronics'`.
2. An **Active Cross-Filter Banner** appears immediately beneath the main filter bar.
3. Every sibling widget automatically re-executes its query incorporating the selected filter condition.
4. The clicked element remains highlighted, while clicking it again deselects and removes the filter.

---

## 2. Multi-Filter & Combination Semantics

- **Multi-Dimension Support**: Users can select across multiple dimensions simultaneously (e.g. `Region = West` from a bar chart AND `Priority = High` from a table).
- **Circular Dependency Prevention**:
  - The emitting widget does not recursively constrain itself into an empty state.
  - Cross-filters are stored in a dedicated keyed dictionary `crossFilterState: Record<string, { column, operator, value }>` which ensures at most one active value per dimension.
- **Toggle Deselection**: Clicking an already active element clears that dimension's constraint.
- **Global Reset**: A "Clear All Cross-Filters" action resets the interactive state across the entire dashboard in a single operation.

---

## 3. Integration with Dashboard Global Filters & Exports

In `DashboardEditor.tsx`:
```typescript
const combinedFilterList = useMemo(() => {
  const map = new Map<string, { column: string; operator: string; value: any }>();
  // 1. Dashboard persistent filters
  Object.values(filterState).forEach((f) => map.set(f.column, f));
  // 2. Runtime cross-filters override/extend
  Object.values(crossFilterState).forEach((f) => map.set(f.column, f));
  return Array.from(map.values());
}, [filterState, crossFilterState]);
```

When users export the dashboard to PDF, Excel (XLSX), or CSV, `combinedFilterList` is passed directly to the export service, ensuring exported reports accurately reflect what the user sees on their screen.

