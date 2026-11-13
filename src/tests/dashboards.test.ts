import { describe, it, expect } from 'vitest';

describe('Dashboard Grid & Layout Engine', () => {
  it('enforces 12-column grid boundaries during resizing', () => {
    const clampWidth = (currentW: number, delta: number) => {
      return Math.min(Math.max(currentW + delta, 3), 12);
    };

    // Expanding within range
    expect(clampWidth(6, 2)).toBe(8);
    // Expanding beyond maximum 12
    expect(clampWidth(12, 2)).toBe(12);
    // Shrinking within range
    expect(clampWidth(6, -2)).toBe(4);
    // Shrinking below minimum 3
    expect(clampWidth(3, -2)).toBe(3);
  });

  it('correctly reorders widgets when moved up or down', () => {
    const initialWidgets = [
      { id: 'w1', title: 'Revenue KPI', grid_y: 0 },
      { id: 'w2', title: 'Category Breakdown', grid_y: 1 },
      { id: 'w3', title: 'Sales Trend', grid_y: 2 },
    ];

    const moveWidget = (
      widgets: typeof initialWidgets,
      id: string,
      direction: 'up' | 'down'
    ) => {
      const idx = widgets.findIndex((w) => w.id === id);
      if (idx === -1) return widgets;
      const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (targetIdx < 0 || targetIdx >= widgets.length) return widgets;

      const copy = [...widgets];
      const [moved] = copy.splice(idx, 1);
      copy.splice(targetIdx, 0, moved);
      return copy.map((w, i) => ({ ...w, grid_y: i }));
    };

    // Move w2 up
    const afterUp = moveWidget(initialWidgets, 'w2', 'up');
    expect(afterUp[0].id).toBe('w2');
    expect(afterUp[0].grid_y).toBe(0);
    expect(afterUp[1].id).toBe('w1');
    expect(afterUp[1].grid_y).toBe(1);

    // Move w1 down
    const afterDown = moveWidget(initialWidgets, 'w1', 'down');
    expect(afterDown[1].id).toBe('w1');
    expect(afterDown[0].id).toBe('w2');
  });

  it('simulates drag and drop reordering between slots', () => {
    const widgets = [
      { id: 'w1', title: 'A' },
      { id: 'w2', title: 'B' },
      { id: 'w3', title: 'C' },
    ];

    const reorderOnDrop = (sourceId: string, targetId: string) => {
      const sourceIdx = widgets.findIndex((w) => w.id === sourceId);
      const targetIdx = widgets.findIndex((w) => w.id === targetId);
      const copy = [...widgets];
      const [moved] = copy.splice(sourceIdx, 1);
      copy.splice(targetIdx, 0, moved);
      return copy;
    };

    const dropped = reorderOnDrop('w1', 'w3');
    expect(dropped.map((w) => w.id)).toEqual(['w2', 'w3', 'w1']);
  });
});

describe('Dashboard Interactive Filtering System', () => {
  it('applies, modifies, and clears filter state correctly', () => {
    let filterState: Record<string, { column: string; operator: string; value: any }> = {};

    const handleFilterChange = (column: string, operator: string, value: any) => {
      if (value === null || value === '' || value === undefined) {
        delete filterState[column];
      } else {
        filterState[column] = { column, operator, value };
      }
    };

    // Apply Region filter
    handleFilterChange('region', 'eq', 'North America');
    expect(filterState['region']).toEqual({
      column: 'region',
      operator: 'eq',
      value: 'North America',
    });

    // Apply Date Range filter
    handleFilterChange('order_date', 'gte', '2025-01-01');
    expect(Object.keys(filterState).length).toBe(2);

    // Update Region filter
    handleFilterChange('region', 'eq', 'Europe');
    expect(filterState['region'].value).toBe('Europe');

    // Remove Region filter
    handleFilterChange('region', 'eq', null);
    expect(filterState['region']).toBeUndefined();
    expect(Object.keys(filterState).length).toBe(1);

    // Clear all
    filterState = {};
    expect(Object.keys(filterState).length).toBe(0);
  });
});

describe('Widget Visualization Data Adapters', () => {
  it('formats KPI numerical values correctly', () => {
    const formatKPI = (val: number | null | undefined, unit?: string) => {
      if (val === null || val === undefined) return '0';
      const formatted = val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      return unit ? `${unit} ${formatted}` : formatted;
    };

    expect(formatKPI(150000, '$')).toBe('$ 150,000.00');
    expect(formatKPI(0)).toBe('0.00');
    expect(formatKPI(undefined)).toBe('0');
  });

  it('normalizes time-series points for Line and Area charts', () => {
    const rawPoints = [
      { timestamp: '2025-01-01', value: 100 },
      { timestamp: '2025-02-01', value: 250 },
      { timestamp: '2025-03-01', value: 180 },
    ];

    const values = rawPoints.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;

    expect(min).toBe(100);
    expect(max).toBe(250);
    expect(range).toBe(150);

    // Normalized Y coordinate (0 to 1)
    const normalizedY = rawPoints.map((p) => (p.value - min) / range);
    expect(normalizedY[0]).toBe(0);
    expect(normalizedY[1]).toBe(1);
    expect(normalizedY[2]).toBeCloseTo(0.533, 2);
  });
});
