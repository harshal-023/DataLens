import { describe, it, expect } from 'vitest';

describe('Advanced Interactive Visualization Engine Tests', () => {
  describe('Comparative Analytics & Delta Calculations', () => {
    it('calculates absolute difference, percentage change, and trend direction accurately', () => {
      const computeComparison = (actual: number, base: number) => {
        const delta = actual - base;
        const pct = base !== 0 ? (delta / Math.abs(base)) * 100 : (delta > 0 ? 100 : delta < 0 ? -100 : 0);
        const direction = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
        return { delta, pct: Math.round(pct * 10) / 10, direction };
      };

      // Increase
      const res1 = computeComparison(1250, 1000);
      expect(res1.delta).toBe(250);
      expect(res1.pct).toBe(25.0);
      expect(res1.direction).toBe('up');

      // Decrease
      const res2 = computeComparison(800, 1000);
      expect(res2.delta).toBe(-200);
      expect(res2.pct).toBe(-20.0);
      expect(res2.direction).toBe('down');

      // Zero base value protection
      const res3 = computeComparison(150, 0);
      expect(res3.delta).toBe(150);
      expect(res3.pct).toBe(100);
      expect(res3.direction).toBe('up');

      // No change
      const res4 = computeComparison(500, 500);
      expect(res4.delta).toBe(0);
      expect(res4.pct).toBe(0);
      expect(res4.direction).toBe('flat');
    });
  });

  describe('100% Stacked Bar Normalization', () => {
    it('normalizes multi-series segment totals to exact 100% proportions', () => {
      const rawCategories = ['Q1', 'Q2'];
      const rawSeries = [
        { name: 'Hardware', values: [300, 600] },
        { name: 'Software', values: [100, 200] },
      ];

      // Compute normalized values
      const categoryTotals = rawCategories.map((_, catIdx) =>
        rawSeries.reduce((acc, s) => acc + (s.values[catIdx] || 0), 0)
      );

      expect(categoryTotals[0]).toBe(400);
      expect(categoryTotals[1]).toBe(800);

      const normalizedSeries = rawSeries.map((s) => ({
        name: s.name,
        percentages: s.values.map((v, catIdx) =>
          categoryTotals[catIdx] > 0
            ? Math.round((v / categoryTotals[catIdx]) * 1000) / 10
            : 0
        ),
      }));

      // Hardware: 300/400 = 75%, 600/800 = 75%
      expect(normalizedSeries[0].percentages).toEqual([75.0, 75.0]);
      // Software: 100/400 = 25%, 200/800 = 25%
      expect(normalizedSeries[1].percentages).toEqual([25.0, 25.0]);

      // Sum of percentages for each category equals 100%
      const q1Sum = normalizedSeries.reduce((acc, s) => acc + s.percentages[0], 0);
      const q2Sum = normalizedSeries.reduce((acc, s) => acc + s.percentages[1], 0);
      expect(q1Sum).toBe(100.0);
      expect(q2Sum).toBe(100.0);
    });
  });

  describe('Hierarchical Drill-Down State & Breadcrumbs', () => {
    it('manages hierarchical drill depth, drill filters, and breadcrumb trails', () => {
      const hierarchy = ['Region', 'Country', 'City'];
      let depth = 0;
      let drillFilters: Array<{ column: string; value: string }> = [];
      let history: string[] = [];

      const drillDown = (val: string) => {
        if (depth < hierarchy.length - 1) {
          const col = hierarchy[depth];
          drillFilters.push({ column: col, value: val });
          history.push(val);
          depth += 1;
        }
      };

      const drillUp = () => {
        if (depth > 0) {
          depth -= 1;
          drillFilters.pop();
          history.pop();
        }
      };

      // Initial state
      expect(depth).toBe(0);
      expect(hierarchy[depth]).toBe('Region');

      // Drill into "Europe"
      drillDown('Europe');
      expect(depth).toBe(1);
      expect(hierarchy[depth]).toBe('Country');
      expect(history).toEqual(['Europe']);
      expect(drillFilters).toEqual([{ column: 'Region', value: 'Europe' }]);

      // Drill into "Germany"
      drillDown('Germany');
      expect(depth).toBe(2);
      expect(hierarchy[depth]).toBe('City');
      expect(history).toEqual(['Europe', 'Germany']);

      // Attempt to drill beyond leaf level (should not increase depth)
      drillDown('Berlin');
      expect(depth).toBe(2);
      expect(history.length).toBe(2);

      // Drill back up to Country level
      drillUp();
      expect(depth).toBe(1);
      expect(hierarchy[depth]).toBe('Country');
      expect(history).toEqual(['Europe']);
    });
  });

  describe('Cross-Filtering Engine & Circular Avoidance', () => {
    it('toggles cross filters on click and merges with dashboard filters without circular loops', () => {
      let crossFilterState: Record<string, { column: string; operator: string; value: any }> = {};

      const handleCrossFilter = (column: string, value: any) => {
        if (crossFilterState[column] && crossFilterState[column].value === value) {
          // Toggle off
          delete crossFilterState[column];
        } else {
          crossFilterState[column] = { column, operator: 'equals', value };
        }
      };

      // Click on Region = "West"
      handleCrossFilter('region', 'West');
      expect(crossFilterState['region']).toEqual({ column: 'region', operator: 'equals', value: 'West' });

      // Click on Category = "Technology"
      handleCrossFilter('category', 'Technology');
      expect(Object.keys(crossFilterState).length).toBe(2);

      // Re-click on Category = "Technology" (toggles off)
      handleCrossFilter('category', 'Technology');
      expect(crossFilterState['category']).toBeUndefined();
      expect(Object.keys(crossFilterState).length).toBe(1);

      // Merge with dashboard global filters
      const globalFilters = [
        { column: 'year', operator: 'equals', value: '2026' },
      ];
      const mergedFilters = [
        ...globalFilters,
        ...Object.values(crossFilterState),
      ];

      expect(mergedFilters).toHaveLength(2);
      expect(mergedFilters.map((f) => f.column)).toEqual(['year', 'region']);
    });
  });

  describe('Pareto 80/20 Distribution Analysis', () => {
    it('computes cumulative share and identifies the 80% vital few threshold', () => {
      const items = [
        { name: 'Defect A', count: 50 },
        { name: 'Defect B', count: 30 },
        { name: 'Defect C', count: 12 },
        { name: 'Defect D', count: 5 },
        { name: 'Defect E', count: 3 },
      ];

      const total = items.reduce((sum, item) => sum + item.count, 0); // 100
      expect(total).toBe(100);

      let running = 0;
      const paretoData = items.map((item) => {
        running += item.count;
        const cumPct = (running / total) * 100;
        return {
          ...item,
          cumulativePct: cumPct,
          isVitalFew: cumPct <= 80 || (cumPct - (item.count / total) * 100 < 80),
        };
      });

      expect(paretoData[0].cumulativePct).toBe(50);
      expect(paretoData[1].cumulativePct).toBe(80);
      expect(paretoData[2].cumulativePct).toBe(92);

      // Top 2 items make up 80% of total defects
      const vitalFew = paretoData.filter((p) => p.isVitalFew);
      expect(vitalFew.map((v) => v.name)).toEqual(['Defect A', 'Defect B']);
    });
  });

  describe('Statistical Five-Number Summary (Box Plot)', () => {
    it('computes correct quartile boundaries and interquartile range', () => {
      const sortedValues = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
      const n = sortedValues.length;

      const q1 = sortedValues[Math.floor(n * 0.25)]; // 30
      const median = (sortedValues[Math.floor(n / 2) - 1] + sortedValues[Math.floor(n / 2)]) / 2; // 55
      const q3 = sortedValues[Math.floor(n * 0.75)]; // 80
      const iqr = q3 - q1; // 50

      expect(q1).toBe(30);
      expect(median).toBe(55);
      expect(q3).toBe(80);
      expect(iqr).toBe(50);

      const lowerWhisker = Math.max(sortedValues[0], q1 - 1.5 * iqr);
      const upperWhisker = Math.min(sortedValues[n - 1], q3 + 1.5 * iqr);

      expect(lowerWhisker).toBe(10);
      expect(upperWhisker).toBe(100);
    });
  });
});
