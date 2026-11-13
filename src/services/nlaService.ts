import { apiClient } from './apiClient';

export interface NLAMetricCard {
  title: string;
  value: string;
  numeric_value?: number | null;
  change?: string | null;
  trend?: 'up' | 'down' | 'neutral';
  formatted?: string | null;
}

export interface NLAEvidenceItem {
  id: string;
  metric_name: string;
  source_column: string;
  aggregation_type: string;
  formula?: string | null;
  computed_value: any;
  verified_by_engine: boolean;
  row_count_analyzed?: number | null;
  execution_time_ms?: number | null;
}

export interface NLAChartData {
  chart_type: 'line' | 'bar' | 'pie' | 'donut' | 'kpi' | 'table' | 'scatter';
  title: string;
  x_key: string;
  y_keys: string[];
  series: Record<string, any>[];
  recommended_by: string;
}

export interface NLATableData {
  columns: string[];
  rows: Record<string, any>[];
  total_rows: number;
}

export interface NLAClarificationOption {
  key: string;
  label: string;
  explanation: string;
  filter_value?: string;
  metric_name?: string;
}

export interface NLAMessageResponse {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  direct_answer?: string | null;
  intent?: string | null;
  metric_cards: NLAMetricCard[];
  chart?: NLAChartData | null;
  table?: NLATableData | null;
  evidence: NLAEvidenceItem[];
  detailed_narrative?: string | null;
  business_inferences: string[];
  recommendations: string[];
  suggested_follow_ups: string[];
  needs_clarification: boolean;
  clarification_prompt?: string | null;
  clarification_options: NLAClarificationOption[];
  raw_sql?: string | null;
  execution_time_ms?: number | null;
  row_count?: number | null;
  created_at: string;
}

export interface NLASessionResponse {
  id: string;
  workspace_id: string;
  title: string;
  primary_dataset_id: string;
  created_at: string;
  updated_at: string;
  messages: NLAMessageResponse[];
}

export interface SavedAnalysisResponse {
  id: string;
  workspace_id: string;
  title: string;
  notes?: string | null;
  dataset_id: string;
  session_id?: string | null;
  message_id?: string | null;
  query_plan?: Record<string, any> | null;
  raw_sql?: string | null;
  result_data?: Record<string, any> | null;
  chart_config?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export const NLAService = {
  async executeQuery(
    workspaceId: string,
    req: {
      question: string;
      dataset_id: string;
      session_id?: string;
    }
  ): Promise<NLAMessageResponse> {
    return apiClient<NLAMessageResponse>(`/api/v1/analytics/query?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async clarifyQuery(
    workspaceId: string,
    req: {
      session_id: string;
      clarification_choice: string;
      original_question?: string;
    }
  ): Promise<NLAMessageResponse> {
    return apiClient<NLAMessageResponse>(`/api/v1/analytics/clarify?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async followUpQuery(
    workspaceId: string,
    req: {
      session_id: string;
      follow_up_question: string;
    }
  ): Promise<NLAMessageResponse> {
    return apiClient<NLAMessageResponse>(`/api/v1/analytics/follow-up?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async getSessions(workspaceId: string, limit = 20): Promise<NLASessionResponse[]> {
    return apiClient<NLASessionResponse[]>(
      `/api/v1/analytics/sessions?workspace_id=${workspaceId}&limit=${limit}`
    );
  },

  async getSession(sessionId: string, workspaceId: string): Promise<NLASessionResponse> {
    return apiClient<NLASessionResponse>(
      `/api/v1/analytics/sessions/${sessionId}?workspace_id=${workspaceId}`
    );
  },

  async deleteSession(sessionId: string, workspaceId: string): Promise<{ success: boolean }> {
    return apiClient<{ success: boolean }>(
      `/api/v1/analytics/sessions/${sessionId}?workspace_id=${workspaceId}`,
      { method: 'DELETE' }
    );
  },

  async saveAnalysis(
    workspaceId: string,
    req: {
      title: string;
      notes?: string;
      dataset_id: string;
      session_id?: string;
      message_id?: string;
      query_plan?: Record<string, any>;
      raw_sql?: string;
      result_data?: Record<string, any>;
      chart_config?: Record<string, any>;
    }
  ): Promise<SavedAnalysisResponse> {
    return apiClient<SavedAnalysisResponse>(`/api/v1/analytics/saved?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async getSavedAnalyses(workspaceId: string, datasetId?: string): Promise<SavedAnalysisResponse[]> {
    const url = `/api/v1/analytics/saved?workspace_id=${workspaceId}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<SavedAnalysisResponse[]>(url);
  },

  async deleteSavedAnalysis(analysisId: string, workspaceId: string): Promise<{ success: boolean }> {
    return apiClient<{ success: boolean }>(
      `/api/v1/analytics/saved/${analysisId}?workspace_id=${workspaceId}`,
      { method: 'DELETE' }
    );
  },
};

