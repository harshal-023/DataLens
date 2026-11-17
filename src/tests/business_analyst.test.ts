import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  BusinessAnalystService,
  BusinessInsight,
  ExecutiveOverview,
  InsightSchedule,
} from '../services/businessAnalystService';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: vi.fn(async (url: string, options?: any) => {
    // 1. Overview
    if (url.includes('/business-analyst/overview')) {
      return {
        workspace_id: 'ws-123',
        total_insights_count: 12,
        critical_risks_count: 2,
        high_opportunities_count: 3,
        anomalies_count: 1,
        top_movements: [
          {
            title: 'Q1 Revenue Expansion',
            category: 'trend',
            severity: 'HIGH',
            metric: 'Revenue',
            change: '+24.5%',
            summary: 'Revenue expanded by 24.5% in the latest quarter.',
          },
        ],
        critical_findings: [],
        positive_opportunities: [],
        recent_changes: [],
      };
    }

    // 2. Filtered Category Endpoints
    if (url.includes('/business-analyst/trends')) {
      return [
        {
          id: 'ins-trend-1',
          workspace_id: 'ws-123',
          title: 'Sustained Revenue Growth',
          category: 'trend',
          severity: 'HIGH',
          status: 'NEW',
          summary: 'Revenue experienced 3 consecutive periods of expansion.',
          affected_metric: 'Revenue',
          score: 0.85,
        },
      ];
    }

    if (url.includes('/business-analyst/risks')) {
      return [
        {
          id: 'ins-risk-1',
          workspace_id: 'ws-123',
          title: 'High Customer Concentration',
          category: 'risk',
          severity: 'CRITICAL',
          status: 'NEW',
          summary: 'Top customer accounts for 35% of total sales.',
          affected_metric: 'Revenue',
          affected_segment: 'MegaCorp',
          score: 0.9,
        },
      ];
    }

    if (url.includes('/business-analyst/opportunities')) {
      return [
        {
          id: 'ins-opp-1',
          workspace_id: 'ws-123',
          title: 'High Margin Expansion in Cloud',
          category: 'opportunity',
          severity: 'HIGH',
          status: 'NEW',
          summary: 'Cloud products offer 55% margin with growing order volume.',
          affected_metric: 'Profit Margin',
          affected_segment: 'Cloud',
          score: 0.88,
        },
      ];
    }

    if (url.includes('/business-analyst/anomalies')) {
      return [
        {
          id: 'ins-anom-1',
          workspace_id: 'ws-123',
          title: 'Order Volume Spike',
          category: 'anomaly',
          severity: 'HIGH',
          status: 'NEW',
          summary: 'Statistical anomaly of 4.2 Z-score detected on Day-15.',
          affected_metric: 'Order Volume',
          score: 0.82,
        },
      ];
    }

    // 3. Generate Insights Sweep
    if (url.includes('/business-analyst/insights/generate') && options?.method === 'POST') {
      return {
        status: 'success',
        run_id: 'run-999',
        insights_generated_count: 6,
        execution_duration_ms: 125,
      };
    }

    // 4. Update Status
    if (url.includes('/status') && options?.method === 'PATCH') {
      const body = JSON.parse(options.body);
      return {
        id: 'ins-risk-1',
        title: 'High Customer Concentration',
        category: 'risk',
        severity: 'CRITICAL',
        status: body.status,
      };
    }

    // 5. Assign Insight
    if (url.includes('/assign') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'ins-risk-1',
        title: 'High Customer Concentration',
        assigned_to_user_id: body.assigned_to_user_id,
      };
    }

    // 6. Comments
    if (url.includes('/comments') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'comm-1',
        insight_id: 'ins-risk-1',
        user_id: 'u-1',
        content: body.content,
        created_at: new Date().toISOString(),
      };
    }

    // 7. Schedules CRUD
    if (url.includes('/run') && options?.method === 'POST') {
      return {
        success: true,
        run_id: 'run-manual-1',
        insights_generated: 4,
        status: 'completed',
      };
    }

    if (url.includes('/business-analyst/schedules') && options?.method === 'PATCH') {
      const body = JSON.parse(options.body);
      return {
        id: 'sched-1',
        workspace_id: 'ws-123',
        name: body.name || 'Daily Morning Sweep',
        frequency: body.frequency || 'daily',
        is_active: body.is_active !== undefined ? body.is_active : true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    if (url.includes('/business-analyst/schedules') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'sched-1',
        workspace_id: 'ws-123',
        name: body.name,
        frequency: body.frequency,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    if (url.includes('/business-analyst/schedules') && options?.method === 'DELETE') {
      return { success: true };
    }

    if (url.includes('/business-analyst/schedules')) {
      return [
        {
          id: 'sched-1',
          workspace_id: 'ws-123',
          name: 'Daily Morning Sweep',
          frequency: 'daily',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ];
    }

    return {};
  }),
}));

describe('BusinessAnalystService (AI Business Analyst & Autonomous Insights)', () => {
  const wsId = 'ws-test-123';
  const dsId = 'ds-sales-456';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('retrieves the executive business overview', async () => {
    const overview: ExecutiveOverview = await BusinessAnalystService.getOverview(wsId, dsId);

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/business-analyst/overview'),
      expect.objectContaining({ workspaceId: wsId })
    );
    expect(overview.total_insights_count).toBe(12);
    expect(overview.critical_risks_count).toBe(2);
    expect(overview.top_movements[0].metric).toBe('Revenue');
  });

  it('queries category-filtered insights for trends, anomalies, risks and opportunities', async () => {
    const [trends, anomalies, risks, opps] = await Promise.all([
      BusinessAnalystService.getTrends(wsId),
      BusinessAnalystService.getAnomalies(wsId),
      BusinessAnalystService.getRisks(wsId),
      BusinessAnalystService.getOpportunities(wsId),
    ]);

    expect(trends.length).toBe(1);
    expect(trends[0].category).toBe('trend');
    expect(anomalies[0].category).toBe('anomaly');
    expect(risks[0].category).toBe('risk');
    expect(opps[0].category).toBe('opportunity');
  });

  it('triggers autonomous analytical insight generation', async () => {
    const res = await BusinessAnalystService.generateInsights(wsId, {
      dataset_id: dsId,
    });

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/business-analyst/insights/generate'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.status).toBe('success');
    expect(res.insights_generated_count).toBe(6);
  });

  it('manages insight lifecycle status updates and assignment', async () => {
    // 1. Status update
    const updated = await BusinessAnalystService.updateStatus(
      'ins-risk-1',
      wsId,
      'ACKNOWLEDGED',
      'Reviewed by CFO.'
    );
    expect(updated.status).toBe('ACKNOWLEDGED');

    // 2. Assignment
    const assigned = await BusinessAnalystService.assignInsight(
      'ins-risk-1',
      wsId,
      'user-analyst-99',
      'Please investigate contract retention.'
    );
    expect(assigned.assigned_to_user_id).toBe('user-analyst-99');

    // 3. Comment
    const comment = await BusinessAnalystService.addComment(
      'ins-risk-1',
      wsId,
      'Audit scheduled for Thursday.'
    );
    expect(comment.content).toBe('Audit scheduled for Thursday.');
  });

  it('manages scheduled background insight sweeps', async () => {
    const created: InsightSchedule = await BusinessAnalystService.createSchedule(wsId, {
      name: 'Weekly Executive Scan',
      frequency: 'weekly',
      dataset_id: dsId,
    });

    expect(created.name).toBe('Weekly Executive Scan');
    expect(created.frequency).toBe('weekly');

    const schedules = await BusinessAnalystService.getSchedules(wsId);
    expect(schedules.length).toBe(1);

    // Toggle active
    const paused = await BusinessAnalystService.toggleScheduleActive('sched-1', wsId, false);
    expect(paused.is_active).toBe(false);

    // Run now
    const runResult = await BusinessAnalystService.runScheduleNow('sched-1', wsId);
    expect(runResult.success).toBe(true);
    expect(runResult.insights_generated).toBe(4);

    const del = await BusinessAnalystService.deleteSchedule('sched-1', wsId);
    expect(del.success).toBe(true);
  });
});

