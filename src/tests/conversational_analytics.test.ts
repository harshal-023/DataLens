import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NLAService, NLAMessageResponse, SavedAnalysisResponse } from '../services/nlaService';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: vi.fn(async (url: string, options?: any) => {
    // 1. Natural Language Query
    if (url.includes('/analytics/query') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      const isAmbiguous = body.question.toLowerCase().includes('best performance');
      return {
        id: 'msg-nla-001',
        session_id: body.session_id || 'sess-nla-999',
        role: 'assistant',
        content: isAmbiguous
          ? 'Your question is broad. Which metric would you like to evaluate?'
          : 'Total revenue reached $25,000 across 100 records.',
        direct_answer: isAmbiguous
          ? 'Please clarify your analytical goal:'
          : 'Total revenue reached $25,000 across 100 records.',
        metric_cards: isAmbiguous
          ? []
          : [{ title: 'Total Revenue', value: '$25,000', change: '+12%', trend: 'up' }],
        chart: isAmbiguous
          ? null
          : {
              chart_type: 'bar',
              title: 'Revenue by Region',
              x_key: 'region',
              y_keys: ['metric_value'],
              series: [{ region: 'North', metric_value: 15000 }, { region: 'South', metric_value: 10000 }],
              recommended_by: 'rule_heuristic',
            },
        table: isAmbiguous
          ? null
          : {
              columns: ['Region', 'Metric Value'],
              rows: [{ Region: 'North', 'Metric Value': 15000 }, { Region: 'South', 'Metric Value': 10000 }],
              total_rows: 2,
            },
        evidence: [
          {
            id: 'ev-1',
            metric_name: 'Total Revenue',
            source_column: 'revenue',
            aggregation_type: 'SUM',
            computed_value: 25000,
            verified_by_engine: true,
            execution_time_ms: 14,
          },
        ],
        business_inferences: ['North region drives 60% of total revenue.'],
        recommendations: ['Increase promotional spend in South region to close quota gap.'],
        suggested_follow_ups: ['Break it down by product category', 'Compare with last year'],
        needs_clarification: isAmbiguous,
        clarification_prompt: isAmbiguous ? 'Which metric do you want to explore?' : null,
        clarification_options: isAmbiguous
          ? [
              { key: 'rev', label: 'Total Revenue', explanation: 'Sum of monetary sales' },
              { key: 'vol', label: 'Order Volume', explanation: 'Count of completed orders' },
            ]
          : [],
        raw_sql: 'SELECT region, SUM(revenue) FROM read_parquet(...) GROUP BY 1',
        execution_time_ms: 14,
        row_count: 2,
        created_at: new Date().toISOString(),
      };
    }

    // 2. Clarification Submission
    if (url.includes('/analytics/clarify') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'msg-nla-002',
        session_id: body.session_id,
        role: 'assistant',
        content: `Analyzing ${body.clarification_choice}. Total Revenue is $25,000.`,
        direct_answer: `Total Revenue evaluated at $25,000 based on your selection.`,
        metric_cards: [{ title: 'Total Revenue', value: '$25,000', trend: 'up' }],
        evidence: [],
        business_inferences: [],
        recommendations: [],
        suggested_follow_ups: ['Show monthly trend'],
        needs_clarification: false,
        clarification_options: [],
        created_at: new Date().toISOString(),
      };
    }

    // 3. Follow-up query
    if (url.includes('/analytics/follow-up') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'msg-nla-003',
        session_id: body.session_id,
        role: 'assistant',
        content: `Filtered to ${body.follow_up_question}. Filtered revenue is $15,000.`,
        direct_answer: `North region revenue is $15,000.`,
        metric_cards: [{ title: 'North Revenue', value: '$15,000', trend: 'up' }],
        evidence: [],
        business_inferences: ['North continues to be the dominant contributor.'],
        recommendations: [],
        suggested_follow_ups: [],
        needs_clarification: false,
        clarification_options: [],
        created_at: new Date().toISOString(),
      };
    }

    // 4. Session listing & detail
    if (url.includes('/analytics/sessions/') && !options) {
      return {
        id: 'sess-nla-999',
        workspace_id: 'ws-1',
        title: 'Sales Performance Inquiry',
        primary_dataset_id: 'ds-123',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [],
      };
    }
    if (url.includes('/analytics/sessions') && options?.method === 'DELETE') {
      return { success: true };
    }
    if (url.includes('/analytics/sessions')) {
      return [
        {
          id: 'sess-nla-999',
          workspace_id: 'ws-1',
          title: 'Sales Performance Inquiry',
          primary_dataset_id: 'ds-123',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          messages: [],
        },
      ];
    }

    // 5. Saved analysis
    if (url.includes('/analytics/saved') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'saved-001',
        workspace_id: 'ws-1',
        title: body.title,
        notes: body.notes,
        dataset_id: body.dataset_id,
        session_id: body.session_id,
        raw_sql: body.raw_sql,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }
    if (url.includes('/analytics/saved') && options?.method === 'DELETE') {
      return { success: true };
    }
    if (url.includes('/analytics/saved')) {
      return [
        {
          id: 'saved-001',
          workspace_id: 'ws-1',
          title: 'Q1 Revenue Breakdown',
          dataset_id: 'ds-123',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ];
    }

    return {};
  }),
}));

describe('NLAService (Conversational Natural Language Analytics)', () => {
  const wsId = 'ws-test-123';
  const dsId = 'ds-sales-456';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits a natural-language query and parses structured analytical findings', async () => {
    const res: NLAMessageResponse = await NLAService.executeQuery(wsId, {
      dataset_id: dsId,
      question: 'What is our total revenue by region?',
    });

    expect(apiClient).toHaveBeenCalledWith(
      `/api/v1/analytics/query?workspace_id=${wsId}`,
      expect.objectContaining({ method: 'POST' })
    );

    expect(res.id).toBe('msg-nla-001');
    expect(res.needs_clarification).toBe(false);
    expect(res.metric_cards.length).toBeGreaterThan(0);
    expect(res.chart?.chart_type).toBe('bar');
    expect(res.evidence[0].verified_by_engine).toBe(true);
    expect(res.business_inferences).toContain('North region drives 60% of total revenue.');
  });

  it('detects ambiguous queries and surfaces targeted clarification options', async () => {
    const res: NLAMessageResponse = await NLAService.executeQuery(wsId, {
      dataset_id: dsId,
      question: 'Show me the best performance',
    });

    expect(res.needs_clarification).toBe(true);
    expect(res.clarification_options.length).toBe(2);
    expect(res.clarification_options[0].label).toBe('Total Revenue');
  });

  it('submits a clarification choice and returns disambiguated results', async () => {
    const res = await NLAService.clarifyQuery(wsId, {
      session_id: 'sess-nla-999',
      clarification_choice: 'Total Revenue',
    });

    expect(apiClient).toHaveBeenCalledWith(
      `/api/v1/analytics/clarify?workspace_id=${wsId}`,
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.needs_clarification).toBe(false);
    expect(res.direct_answer).toContain('Total Revenue');
  });

  it('handles conversational follow-up questions preserving session context', async () => {
    const res = await NLAService.followUpQuery(wsId, {
      session_id: 'sess-nla-999',
      follow_up_question: 'Now only for North',
    });

    expect(apiClient).toHaveBeenCalledWith(
      `/api/v1/analytics/follow-up?workspace_id=${wsId}`,
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.direct_answer).toContain('North region revenue');
  });

  it('manages sessions and loads analytical history', async () => {
    const sessions = await NLAService.getSessions(wsId);
    expect(sessions.length).toBe(1);
    expect(sessions[0].id).toBe('sess-nla-999');

    const detail = await NLAService.getSession('sess-nla-999', wsId);
    expect(detail.id).toBe('sess-nla-999');

    const del = await NLAService.deleteSession('sess-nla-999', wsId);
    expect(del.success).toBe(true);
  });

  it('persists and retrieves saved analytical findings', async () => {
    const created: SavedAnalysisResponse = await NLAService.saveAnalysis(wsId, {
      title: 'North Region Outlier Analysis',
      dataset_id: dsId,
      session_id: 'sess-nla-999',
      notes: 'Strategic finding for executive quarterly review.',
      raw_sql: 'SELECT * FROM sales WHERE region = ?',
    });

    expect(created.id).toBe('saved-001');
    expect(created.title).toBe('North Region Outlier Analysis');

    const savedList = await NLAService.getSavedAnalyses(wsId);
    expect(savedList.length).toBe(1);

    const del = await NLAService.deleteSavedAnalysis('saved-001', wsId);
    expect(del.success).toBe(true);
  });
});

