import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  AutoDashboardService,
  AutoDashboardRequest,
  AutoDashboardStatusResponse,
  AutoDashboardPreviewResponse,
} from '../services/autoDashboardService';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: vi.fn(async (url: string, options?: any) => {
    // 1. Start generation
    if (url.includes('/dashboards/auto-generate') && options?.method === 'POST' && !url.includes('/save') && !url.includes('/cancel')) {
      const body = JSON.parse(options.body);
      return {
        generation_id: 'gen-uuid-1234',
        status: 'running',
        stage: 'reading_structure',
        progress_pct: 15,
        message: 'Reading dataset structure...',
        dataset_id: body.dataset_id,
        dataset_name: 'Test Sales Dataset',
        preview_ready: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    // 2. Status
    if (url.includes('/dashboards/auto-generate/gen-uuid-1234') && !url.includes('/preview') && !url.includes('/save') && !url.includes('/cancel')) {
      return {
        generation_id: 'gen-uuid-1234',
        status: 'completed',
        stage: 'completed',
        progress_pct: 100,
        message: 'Dashboard ready!',
        dataset_id: 'ds-sales-1',
        dataset_name: 'Test Sales Dataset',
        preview_ready: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    // 3. Preview
    if (url.includes('/dashboards/auto-generate/gen-uuid-1234/preview')) {
      return {
        generation_id: 'gen-uuid-1234',
        dataset_id: 'ds-sales-1',
        dataset_name: 'Test Sales Dataset',
        dataset_version_id: 'ver-1',
        title: 'Sales & Revenue Performance',
        description: 'Verified DuckDB executive dashboard',
        business_domain: 'sales',
        theme: 'ocean',
        kpis: [
          {
            id: 'kpi-1',
            title: 'Total Revenue',
            metric_column: 'amount',
            aggregation: 'sum',
            formatted_value: '$1.25M',
            numeric_value: 1250000.0,
            grid_x: 0,
            grid_y: 0,
            grid_w: 3,
            grid_h: 3,
            display_settings: {},
          },
        ],
        charts: [
          {
            id: 'chart-1',
            widget_type: 'line',
            title: 'Monthly Revenue Trend',
            grid_x: 0,
            grid_y: 3,
            grid_w: 7,
            grid_h: 6,
            query_config: { time_column: 'order_date', metric_column: 'amount' },
            display_settings: {},
            calculated_data: { labels: ['2025-01', '2025-02'], values: [500000, 750000] },
          },
        ],
        filters: [
          {
            id: 'filt-1',
            name: 'Date Range',
            column_name: 'order_date',
            filter_type: 'date_range',
            default_operator: 'between',
            config: {},
          },
        ],
        insights: [
          {
            id: 'ins-1',
            title: 'Leading Segment: Electronics',
            observation: 'Electronics contributes 45% of total sales.',
            evidence: 'Calculated via DuckDB aggregation on category.',
            category: 'distribution',
          },
        ],
        total_widgets: 3,
        created_at: new Date().toISOString(),
      };
    }

    // 4. Save
    if (url.includes('/dashboards/auto-generate/gen-uuid-1234/save') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'saved-dash-999',
        workspace_id: 'ws-123',
        title: body.title || 'Saved Dashboard',
        description: body.description,
        visibility: 'workspace',
        is_archived: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        widgets: [],
        filters: [],
      };
    }

    // 5. Cancel
    if (url.includes('/dashboards/auto-generate/gen-uuid-1234/cancel') && options?.method === 'POST') {
      return { cancelled: true };
    }

    return {};
  }),
}));

describe('AutoDashboardService (AI Auto Dashboard Generator)', () => {
  const wsId = 'ws-test-123';
  const dsId = 'ds-sales-1';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('triggers AI dashboard auto-generation session', async () => {
    const req: AutoDashboardRequest = {
      dataset_id: dsId,
      business_domain: 'sales',
      user_objective: 'Understand top products and revenue trajectory',
      visual_style: 'ocean',
    };

    const statusRes: AutoDashboardStatusResponse = await AutoDashboardService.startGeneration(wsId, req);

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboards/auto-generate'),
      expect.objectContaining({ method: 'POST', workspaceId: wsId })
    );
    expect(statusRes.generation_id).toBe('gen-uuid-1234');
    expect(statusRes.status).toBe('running');
  });

  it('polls generation status', async () => {
    const statusRes: AutoDashboardStatusResponse = await AutoDashboardService.getStatus(wsId, 'gen-uuid-1234');

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboards/auto-generate/gen-uuid-1234'),
      expect.objectContaining({ workspaceId: wsId })
    );
    expect(statusRes.preview_ready).toBe(true);
    expect(statusRes.progress_pct).toBe(100);
  });

  it('retrieves verified preview with real DuckDB calculated metrics', async () => {
    const preview: AutoDashboardPreviewResponse = await AutoDashboardService.getPreview(wsId, 'gen-uuid-1234');

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboards/auto-generate/gen-uuid-1234/preview'),
      expect.objectContaining({ workspaceId: wsId })
    );
    expect(preview.title).toBe('Sales & Revenue Performance');
    expect(preview.kpis.length).toBe(1);
    expect(preview.kpis[0].formatted_value).toBe('$1.25M');
    expect(preview.charts[0].calculated_data.values).toEqual([500000, 750000]);
    expect(preview.insights[0].title).toContain('Leading Segment');
  });

  it('persists generated dashboard into standard DataLens dashboard storage', async () => {
    const saved = await AutoDashboardService.saveDashboard(wsId, 'gen-uuid-1234', {
      title: 'Executive Sales Dashboard',
      theme: 'ocean',
    });

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboards/auto-generate/gen-uuid-1234/save'),
      expect.objectContaining({ method: 'POST', workspaceId: wsId })
    );
    expect(saved.id).toBe('saved-dash-999');
    expect(saved.title).toBe('Executive Sales Dashboard');
  });

  it('cancels active generation session', async () => {
    const cancelRes = await AutoDashboardService.cancelGeneration(wsId, 'gen-uuid-1234');

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboards/auto-generate/gen-uuid-1234/cancel'),
      expect.objectContaining({ method: 'POST', workspaceId: wsId })
    );
    expect(cancelRes.cancelled).toBe(true);
  });
});

