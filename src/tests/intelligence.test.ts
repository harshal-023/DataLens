import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IntelligenceService } from '../services/intelligenceService';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: vi.fn(async (url: string, options?: any) => {
    if (url.includes('/intelligence/profile') && options?.method === 'POST') {
      return {
        dataset_id: 'ds-123',
        version_id: 'ver-123',
        version_number: 'v1',
        profile: { quality_score: 98 },
        columns: [],
        relationships: [],
        metrics: [],
      };
    }
    if (url.includes('/intelligence')) {
      return {
        dataset_id: 'ds-123',
        version_id: 'ver-123',
        version_number: 'v1',
        profile: {
          id: 'prof-1',
          row_count: 500,
          column_count: 5,
          quality_score: 95,
          warnings: [],
        },
        columns: [
          {
            id: 'col-1',
            column_name: 'revenue',
            business_name: 'Sales Revenue',
            semantic_type: 'currency',
            logical_type: 'float',
            aggregation_method: 'SUM',
            mapping_status: 'USER_CONFIRMED',
            is_measure: true,
            is_dimension: false,
          },
        ],
        relationships: [
          {
            id: 'rel-1',
            source_column: 'customer_id',
            target_column: 'customer_id',
            relationship_type: 'MANY_TO_ONE',
            status: 'SUGGESTED',
            confidence_score: 0.95,
          },
        ],
        metrics: [],
      };
    }
    if (url.includes('/columns/semantics') && options?.method === 'PATCH') {
      const body = JSON.parse(options.body);
      return {
        id: 'col-1',
        column_name: 'cust_order_amt',
        business_name: body.business_name || 'Customer Order Amount',
        semantic_type: 'currency',
        aggregation_method: 'SUM',
        mapping_status: body.mapping_status || 'USER_CONFIRMED',
      };
    }
    if (url.includes('/metrics/validate') && options?.method === 'POST') {
      return {
        is_valid: true,
        referenced_columns: ['Revenue', 'Total_Orders'],
        errors: [],
        compiled_sql: 'Revenue / NULLIF(Total_Orders, 0)',
      };
    }
    if (url.includes('/relationships') && options?.method === 'PATCH') {
      return {
        id: 'rel-1',
        source_column: 'customer_id',
        target_column: 'customer_id',
        relationship_type: 'MANY_TO_ONE',
        status: 'CONFIRMED',
      };
    }
    if (url.includes('/metrics/calculate') && options?.method === 'POST') {
      return {
        metric_value: 37210.0,
        is_null: false,
        formula: 'SUM(revenue)',
        compiled_sql: 'SELECT (SUM(revenue)) FROM ...',
      };
    }
    return {};
  }),
}));

describe('IntelligenceService (Phase 6B)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches dataset intelligence bundle including profile, columns, and relationships', async () => {
    const result = await IntelligenceService.getIntelligenceBundle('ds-123', 'ver-123');
    expect(apiClient).toHaveBeenCalledWith('/api/v1/datasets/ds-123/intelligence?version_id=ver-123');
    expect(result.dataset_id).toBe('ds-123');
    expect(result.profile?.quality_score).toBe(95);
    expect(result.columns[0].business_name).toBe('Sales Revenue');
  });

  it('updates column semantic mapping and marks as confirmed', async () => {
    const result = await IntelligenceService.updateColumnSemantics(
      'ds-123',
      'cust_order_amt',
      { business_name: 'Customer Order Amount', mapping_status: 'USER_CONFIRMED' },
      'ver-123'
    );

    expect(apiClient).toHaveBeenCalledWith(
      '/api/v1/datasets/ds-123/columns/semantics/cust_order_amt?version_id=ver-123',
      expect.objectContaining({ method: 'PATCH' })
    );
    expect(result.business_name).toBe('Customer Order Amount');
    expect(result.mapping_status).toBe('USER_CONFIRMED');
  });

  it('validates business metric formula safely', async () => {
    const result = await IntelligenceService.validateFormula('Revenue / Total_Orders');
    expect(apiClient).toHaveBeenCalledWith(
      '/api/v1/metrics/validate',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.is_valid).toBe(true);
    expect(result.referenced_columns).toContain('Revenue');
    expect(result.compiled_sql).toContain('NULLIF(Total_Orders, 0)');
  });

  it('confirms discovered relationship between datasets', async () => {
    const result = await IntelligenceService.updateRelationship('ds-123', 'rel-1', 'CONFIRMED');
    expect(apiClient).toHaveBeenCalledWith(
      '/api/v1/datasets/ds-123/relationships/rel-1',
      expect.objectContaining({ method: 'PATCH' })
    );
    expect(result.status).toBe('CONFIRMED');
  });

  it('calculates preview metric value via DuckDB calculation engine', async () => {
    const result = await IntelligenceService.calculateMetric('ds-123', 'SUM(revenue)', 'SUM');
    expect(apiClient).toHaveBeenCalledWith(
      '/api/v1/metrics/calculate',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.metric_value).toBe(37210.0);
    expect(result.is_null).toBe(false);
  });
});
