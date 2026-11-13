import { describe, it, expect } from 'vitest';
import { TransformationStep, TransformationOpType } from '../services/transformationService';

describe('Data Transformation & Preparation Engine', () => {
  it('extracts referenced columns from a formula expression', () => {
    const extractColumns = (expr: string): string[] => {
      const matches = expr.matchAll(/\[([^\]]+)\]/g);
      const cols = new Set<string>();
      for (const m of matches) {
        cols.add(m[1].trim());
      }
      return Array.from(cols).sort();
    };

    const expr = '[price] * [quantity] * (1 - [discount]) / [tax_rate] + [shipping]';
    const cols = extractColumns(expr);
    expect(cols).toEqual(['discount', 'price', 'quantity', 'shipping', 'tax_rate']);
  });

  it('validates join key requirements', () => {
    const validateJoinKeys = (keys: Array<{ left: string; right: string }>) => {
      if (!keys || keys.length === 0) return { valid: false, error: 'At least one key pair required' };
      for (const k of keys) {
        if (!k.left?.trim() || !k.right?.trim()) {
          return { valid: false, error: 'Left and right columns must be specified' };
        }
      }
      return { valid: true };
    };

    expect(validateJoinKeys([])).toEqual({ valid: false, error: 'At least one key pair required' });
    expect(validateJoinKeys([{ left: 'user_id', right: '' }])).toEqual({
      valid: false,
      error: 'Left and right columns must be specified',
    });
    expect(validateJoinKeys([{ left: 'user_id', right: 'id' }])).toEqual({ valid: true });
  });

  it('correctly resolves column name conflicts between joined datasets', () => {
    const resolveConflictColumns = (
      leftCols: string[],
      rightCols: string[],
      suffixLeft = '_left',
      suffixRight = '_right'
    ) => {
      const common = new Set(leftCols.filter((c) => rightCols.includes(c)));
      const result: { left: string[]; right: string[] } = { left: [], right: [] };

      leftCols.forEach((c) => {
        result.left.push(common.has(c) ? `${c}${suffixLeft}` : c);
      });
      rightCols.forEach((c) => {
        result.right.push(common.has(c) ? `${c}${suffixRight}` : c);
      });
      return result;
    };

    const left = ['id', 'order_date', 'amount', 'created_at'];
    const right = ['id', 'customer_name', 'email', 'created_at'];

    const resolved = resolveConflictColumns(left, right);
    expect(resolved.left).toEqual(['id_left', 'order_date', 'amount', 'created_at_left']);
    expect(resolved.right).toEqual(['id_right', 'customer_name', 'email', 'created_at_right']);
  });

  it('reorders transformation steps sequentially without gaps', () => {
    const steps: Array<{ id: string; step_order: number; op: string }> = [
      { id: 's1', step_order: 0, op: 'clean_nulls' },
      { id: 's2', step_order: 1, op: 'join' },
      { id: 's3', step_order: 2, op: 'formula' },
    ];

    const moveStep = (
      items: typeof steps,
      id: string,
      direction: 'up' | 'down'
    ) => {
      const idx = items.findIndex((s) => s.id === id);
      if (idx === -1) return items;
      const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (targetIdx < 0 || targetIdx >= items.length) return items;

      const copy = [...items];
      const [moved] = copy.splice(idx, 1);
      copy.splice(targetIdx, 0, moved);
      return copy.map((s, i) => ({ ...s, step_order: i }));
    };

    // Move formula up to index 1
    const moved = moveStep(steps, 's3', 'up');
    expect(moved[0].id).toBe('s1');
    expect(moved[1].id).toBe('s3');
    expect(moved[1].step_order).toBe(1);
    expect(moved[2].id).toBe('s2');
    expect(moved[2].step_order).toBe(2);
  });

  it('generates appropriate null strategy descriptors', () => {
    const describeNullStrategy = (strategy: string, fillValue?: any) => {
      switch (strategy) {
        case 'drop':
          return 'Drop rows with NULLs';
        case 'fill_value':
          return `Fill NULLs with "${fillValue}"`;
        case 'fill_mean':
          return 'Fill NULLs with column average (mean)';
        case 'fill_median':
          return 'Fill NULLs with column median';
        case 'fill_mode':
          return 'Fill NULLs with most frequent value (mode)';
        default:
          return 'Unknown strategy';
      }
    };

    expect(describeNullStrategy('drop')).toBe('Drop rows with NULLs');
    expect(describeNullStrategy('fill_value', 0)).toBe('Fill NULLs with "0"');
    expect(describeNullStrategy('fill_mean')).toBe('Fill NULLs with column average (mean)');
    expect(describeNullStrategy('fill_median')).toBe('Fill NULLs with column median');
  });
});

