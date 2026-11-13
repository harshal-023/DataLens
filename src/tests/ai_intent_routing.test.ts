import { describe, expect, it, vi, beforeEach } from 'vitest';
import { AskAnalyticsService } from '../services/askAnalyticsService';
import { StorageService } from '../services/storageService';
import { Dataset } from '../types';

describe('AI Data Analyst - Intent Routing & Conversational Intelligence', () => {
  const mockDataset = {
    id: 'ds-test-intent',
    name: 'Sales_Performance_2025',
    columns: [
      { id: 'c1', name: 'product', displayName: 'Product', type: 'string', missingCount: 0, uniqueCount: 3, sampleValues: ['Enterprise Suite'] },
      { id: 'c2', name: 'revenue', displayName: 'Revenue', type: 'number', missingCount: 0, uniqueCount: 3, sampleValues: ['50000'] },
      { id: 'c3', name: 'region', displayName: 'Region', type: 'string', missingCount: 0, uniqueCount: 3, sampleValues: ['North'] },
      { id: 'c4', name: 'order_date', displayName: 'Order Date', type: 'date', missingCount: 0, uniqueCount: 3, sampleValues: ['2025-01-15'] },
    ],
    columnCount: 4,
    rowCount: 500,
    previewRows: [
      { product: 'Enterprise Suite', revenue: 50000, region: 'North', order_date: '2025-01-15' },
      { product: 'Starter Plan', revenue: 15000, region: 'South', order_date: '2025-01-16' },
      { product: 'Pro Plan', revenue: 35000, region: 'East', order_date: '2025-01-17' },
    ],
  } as unknown as Dataset;

  beforeEach(() => {
    vi.spyOn(StorageService, 'getAllDatasetRowsAsync').mockResolvedValue(mockDataset.previewRows || []);
  });

  it('routes standalone greeting without calculating metrics or generating data artifacts', async () => {
    const res = await AskAnalyticsService.processQuestion('Hello', { dataset: mockDataset });

    expect(res.intent).toBe('GREETING');
    expect(res.directAnswer).toContain('Sales_Performance_2025');
    expect(res.metrics).toEqual([]);
    expect(res.evidence).toEqual([]);
    expect(res.chartData).toBeUndefined();
    expect(res.tableData).toBeUndefined();
    expect(res.suggestedFollowUps && res.suggestedFollowUps.length).toBeGreaterThan(0);
  });

  it('routes casual conversation politely without executing queries', async () => {
    const res = await AskAnalyticsService.processQuestion('Thank you very much!', { dataset: mockDataset });

    expect(res.intent).toBe('CASUAL_CONVERSATION');
    expect(res.directAnswer?.toLowerCase()).toContain('welcome');
    expect(res.metrics).toEqual([]);
    expect(res.evidence).toEqual([]);
    expect(res.chartData).toBeUndefined();
  });

  it('routes capability queries with structured explanation and sample prompts', async () => {
    const res = await AskAnalyticsService.processQuestion('What can you do?', { dataset: mockDataset });

    expect(res.intent).toBe('CAPABILITY_QUERY');
    expect(res.directAnswer).toContain('Metric Calculations');
    expect(res.directAnswer).toContain('Rankings & Comparisons');
    expect(res.directAnswer).toContain('Deterministic Verification');
    expect(res.metrics).toEqual([]);
    expect(res.evidence).toEqual([]);
    expect(res.suggestedFollowUps && res.suggestedFollowUps.length).toBeGreaterThan(0);
  });

  it('routes unsupported out-of-domain requests with polite scope boundaries', async () => {
    const res = await AskAnalyticsService.processQuestion('Write a poem about nature', { dataset: mockDataset });

    expect(res.intent).toBe('UNSUPPORTED_REQUEST');
    expect(res.directAnswer).toContain('DataLens');
    expect(res.directAnswer).toContain('cannot assist with external tasks');
    expect(res.metrics).toEqual([]);
    expect(res.evidence).toEqual([]);
    expect(res.chartData).toBeUndefined();
  });

  it('routes genuine business intelligence questions to the full analytical engine', async () => {
    const res = await AskAnalyticsService.processQuestion('Which product generated the highest revenue?', {
      dataset: mockDataset,
    });

    // Analytical query must compute real metrics and evidence
    expect(res.metrics && res.metrics.length).toBeGreaterThan(0);
    expect(res.evidence && res.evidence.length).toBeGreaterThan(0);
    expect(res.chartData).toBeDefined();
    expect(res.directAnswer).toContain('Enterprise Suite');
    expect(res.evidence![0].verifiedByEngine).toBe(true);
  });

  it('routes mixed greeting + analytical query to the analytical engine', async () => {
    const res = await AskAnalyticsService.processQuestion('Hello, which product generated the highest revenue?', {
      dataset: mockDataset,
    });

    // Must not be trapped in greeting mode
    expect(res.metrics && res.metrics.length).toBeGreaterThan(0);
    expect(res.directAnswer).toContain('Enterprise Suite');
  });
});
