import { apiClient } from './apiClient';

export interface InsightEvidence {
  id: string;
  evidence_type: string;
  metric_name: string;
  baseline_value?: string | null;
  observed_value: string;
  deviation_pct?: number | null;
  supporting_data?: Record<string, any> | null;
  calculation_formula?: string | null;
  verified: boolean;
  created_at: string;
}

export interface InsightComment {
  id: string;
  insight_id: string;
  user_id: string;
  author_name?: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface BusinessInsight {
  id: string;
  workspace_id: string;
  dataset_id: string;
  dataset_version_id: string;
  title: string;
  category: 'performance' | 'trend' | 'anomaly' | 'risk' | 'opportunity';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
  status: 'NEW' | 'REVIEWED' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED' | 'DISMISSED';
  summary: string;
  detailed_explanation: string;
  affected_metric: string;
  affected_dimension?: string | null;
  affected_segment?: string | null;
  score: number;
  priority_reason?: string | null;
  recommended_action?: string | null;
  suggested_investigation?: string | null;
  assigned_to_user_id?: string | null;
  acknowledged_at?: string | null;
  acknowledged_by_user_id?: string | null;
  resolved_at?: string | null;
  resolved_by_user_id?: string | null;
  ai_provider: string;
  fingerprint: string;
  created_at: string;
  updated_at: string;
  evidence_items: InsightEvidence[];
  comments: InsightComment[];
}

export interface ExecutiveOverview {
  workspace_id: string;
  dataset_id?: string | null;
  total_insights_count: number;
  critical_risks_count: number;
  high_opportunities_count: number;
  anomalies_count: number;
  top_movements: Array<{
    title: string;
    category: string;
    severity: string;
    metric: string;
    change?: string | null;
    summary: string;
  }>;
  critical_findings: BusinessInsight[];
  positive_opportunities: BusinessInsight[];
  recent_changes: Array<Record<string, any>>;
}

export interface InsightRunHistory {
  id: string;
  dataset_id: string;
  dataset_version_id: string;
  trigger_type: string;
  status: string;
  insights_generated_count: number;
  execution_duration_ms: number;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface InsightSchedule {
  id: string;
  workspace_id: string;
  dataset_id?: string | null;
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'on_refresh' | 'on_pipeline';
  cron_expression?: string | null;
  timezone: string;
  is_active: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
  config?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export const BusinessAnalystService = {
  async getOverview(workspaceId: string, datasetId?: string): Promise<ExecutiveOverview> {
    const url = `/api/v1/business-analyst/overview?workspace_id=${workspaceId}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<ExecutiveOverview>(url, { workspaceId });
  },

  async getInsights(
    workspaceId: string,
    params?: {
      dataset_id?: string;
      category?: string;
      severity?: string;
      status?: string;
      limit?: number;
    }
  ): Promise<BusinessInsight[]> {
    let url = `/api/v1/business-analyst/insights?workspace_id=${workspaceId}`;
    if (params?.dataset_id) url += `&dataset_id=${params.dataset_id}`;
    if (params?.category) url += `&category=${params.category}`;
    if (params?.severity) url += `&severity=${params.severity}`;
    if (params?.status) url += `&status=${params.status}`;
    if (params?.limit) url += `&limit=${params.limit}`;
    return apiClient<BusinessInsight[]>(url, { workspaceId });
  },

  async getInsight(insightId: string, workspaceId: string): Promise<BusinessInsight> {
    return apiClient<BusinessInsight>(
      `/api/v1/business-analyst/insights/${insightId}?workspace_id=${workspaceId}`,
      { workspaceId }
    );
  },

  async generateInsights(
    workspaceId: string,
    req: {
      dataset_id: string;
      version_id?: string;
      categories?: string[];
      min_severity?: string;
      ai_provider?: string;
    }
  ): Promise<{ status: string; run_id: string; insights_generated_count: number; execution_duration_ms: number }> {
    return apiClient<{
      status: string;
      run_id: string;
      insights_generated_count: number;
      execution_duration_ms: number;
    }>(`/api/v1/business-analyst/insights/generate?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async updateStatus(
    insightId: string,
    workspaceId: string,
    newStatus: string,
    notes?: string
  ): Promise<BusinessInsight> {
    return apiClient<BusinessInsight>(
      `/api/v1/business-analyst/insights/${insightId}/status?workspace_id=${workspaceId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus, notes }),
        workspaceId,
      }
    );
  },

  async assignInsight(
    insightId: string,
    workspaceId: string,
    assignedToUserId: string,
    note?: string
  ): Promise<BusinessInsight> {
    return apiClient<BusinessInsight>(
      `/api/v1/business-analyst/insights/${insightId}/assign?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({ assigned_to_user_id: assignedToUserId, note }),
        workspaceId,
      }
    );
  },

  async addComment(
    insightId: string,
    workspaceId: string,
    content: string
  ): Promise<InsightComment> {
    return apiClient<InsightComment>(
      `/api/v1/business-analyst/insights/${insightId}/comments?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({ content }),
        workspaceId,
      }
    );
  },

  async getTrends(workspaceId: string, datasetId?: string): Promise<BusinessInsight[]> {
    const url = `/api/v1/business-analyst/trends?workspace_id=${workspaceId}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<BusinessInsight[]>(url, { workspaceId });
  },

  async getAnomalies(workspaceId: string, datasetId?: string): Promise<BusinessInsight[]> {
    const url = `/api/v1/business-analyst/anomalies?workspace_id=${workspaceId}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<BusinessInsight[]>(url, { workspaceId });
  },

  async getRisks(workspaceId: string, datasetId?: string): Promise<BusinessInsight[]> {
    const url = `/api/v1/business-analyst/risks?workspace_id=${workspaceId}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<BusinessInsight[]>(url, { workspaceId });
  },

  async getOpportunities(workspaceId: string, datasetId?: string): Promise<BusinessInsight[]> {
    const url = `/api/v1/business-analyst/opportunities?workspace_id=${workspaceId}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<BusinessInsight[]>(url, { workspaceId });
  },

  async getRunHistory(workspaceId: string, datasetId?: string, limit = 20): Promise<InsightRunHistory[]> {
    const url = `/api/v1/business-analyst/history?workspace_id=${workspaceId}&limit=${limit}${
      datasetId ? `&dataset_id=${datasetId}` : ''
    }`;
    return apiClient<InsightRunHistory[]>(url, { workspaceId });
  },

  async getSchedules(workspaceId: string): Promise<InsightSchedule[]> {
    return apiClient<InsightSchedule[]>(
      `/api/v1/business-analyst/schedules?workspace_id=${workspaceId}`,
      { workspaceId }
    );
  },

  async createSchedule(
    workspaceId: string,
    req: {
      name: string;
      frequency: string;
      dataset_id?: string;
      cron_expression?: string;
      timezone?: string;
      config?: Record<string, any>;
    }
  ): Promise<InsightSchedule> {
    return apiClient<InsightSchedule>(
      `/api/v1/business-analyst/schedules?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify(req),
        workspaceId,
      }
    );
  },

  async updateSchedule(
    scheduleId: string,
    workspaceId: string,
    data: Partial<{
      name: string;
      frequency: 'daily' | 'weekly' | 'monthly' | 'on_refresh' | 'on_pipeline';
      cron_expression: string | null;
      timezone: string;
      is_active: boolean;
      dataset_id: string | null;
      config: Record<string, any> | null;
    }>
  ): Promise<InsightSchedule> {
    return apiClient<InsightSchedule>(
      `/api/v1/business-analyst/schedules/${scheduleId}?workspace_id=${workspaceId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
        workspaceId,
      }
    );
  },

  async toggleScheduleActive(
    scheduleId: string,
    workspaceId: string,
    isActive: boolean
  ): Promise<InsightSchedule> {
    return this.updateSchedule(scheduleId, workspaceId, { is_active: isActive });
  },

  async runScheduleNow(
    scheduleId: string,
    workspaceId: string
  ): Promise<{ success: boolean; run_id: string; insights_generated: number; status: string }> {
    return apiClient<{ success: boolean; run_id: string; insights_generated: number; status: string }>(
      `/api/v1/business-analyst/schedules/${scheduleId}/run?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        workspaceId,
      }
    );
  },

  async deleteSchedule(scheduleId: string, workspaceId: string): Promise<{ success: boolean }> {
    return apiClient<{ success: boolean }>(
      `/api/v1/business-analyst/schedules/${scheduleId}?workspace_id=${workspaceId}`,
      {
        method: 'DELETE',
        workspaceId,
      }
    );
  },
};
