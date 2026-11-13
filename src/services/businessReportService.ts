import { apiClient, getAccessToken, API_BASE_URL } from './apiClient';

export interface ReportTemplate {
  id: string;
  name: string;
  description: string | null;
  category: string;
  is_system: boolean;
  template_config: Record<string, any>;
  default_sections: Array<{
    id: string;
    title: string;
    section_type: string;
    description?: string;
    chart_type?: string;
    kpi_items?: any[];
  }>;
}

export interface ReportRun {
  id: string;
  report_id: string;
  workspace_id: string;
  triggered_by: string | null;
  trigger_type: 'manual' | 'scheduled' | 'api';
  execution_status: 'pending' | 'running' | 'completed' | 'failed';
  report_period: string | null;
  applied_filters: any[];
  source_provenance: any;
  generated_files: Record<string, { storage_key: string; file_size: number; filename: string; media_type: string }>;
  execution_duration_ms: number;
  error_details: string | null;
  ai_generated: boolean;
  created_at: string;
}

export interface ReportSchedule {
  id: string;
  report_id: string;
  workspace_id: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  day_of_week?: number | null;
  day_of_month?: number | null;
  hour: number;
  minute: number;
  timezone: string;
  next_execution_time: string | null;
  last_execution_time: string | null;
  last_execution_status: string | null;
  is_enabled: boolean;
  delivery_configuration: {
    email_recipients?: string[];
    attach_formats?: string[];
  };
  created_at: string;
  updated_at: string;
}

export interface BusinessReport {
  id: string;
  workspace_id: string;
  template_id: string | null;
  owner_id: string | null;
  title: string;
  description: string | null;
  report_type: string;
  status: string;
  configuration: {
    period?: string;
    sections?: any[];
    branding?: Record<string, any>;
  };
  source_dashboard_ids: string[];
  source_dataset_refs: Array<{ dataset_id: string; version_id?: string; name?: string }>;
  source_model_run_refs: Array<{ model_run_id: string; model_type?: string }>;
  created_at: string;
  updated_at: string;
  runs?: ReportRun[];
  schedules?: ReportSchedule[];
}

export interface BusinessReportListResponse {
  items: BusinessReport[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const businessReportService = {
  // Templates
  async listTemplates(workspaceId: string, category?: string): Promise<ReportTemplate[]> {
    const q = category ? `?category=${category}` : '';
    return apiClient<ReportTemplate[]>(`/api/v1/reports/templates${q}`, { workspaceId });
  },

  async getTemplate(workspaceId: string, templateId: string): Promise<ReportTemplate> {
    return apiClient<ReportTemplate>(`/api/v1/reports/templates/${templateId}`, { workspaceId });
  },

  // Business Reports CRUD
  async listReports(
    workspaceId: string,
    params: { page?: number; pageSize?: number; reportType?: string; search?: string } = {}
  ): Promise<BusinessReportListResponse> {
    const q = new URLSearchParams();
    if (params.page) q.set('page', String(params.page));
    if (params.pageSize) q.set('page_size', String(params.pageSize));
    if (params.reportType) q.set('report_type', params.reportType);
    if (params.search) q.set('search', params.search);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return apiClient<BusinessReportListResponse>(`/api/v1/reports/business${qs}`, { workspaceId });
  },

  async getReport(workspaceId: string, reportId: string): Promise<BusinessReport> {
    return apiClient<BusinessReport>(`/api/v1/reports/business/${reportId}`, { workspaceId });
  },

  async createReport(workspaceId: string, data: Partial<BusinessReport>): Promise<BusinessReport> {
    return apiClient<BusinessReport>('/api/v1/reports/business', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async updateReport(workspaceId: string, reportId: string, data: Partial<BusinessReport>): Promise<BusinessReport> {
    return apiClient<BusinessReport>(`/api/v1/reports/business/${reportId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async deleteReport(workspaceId: string, reportId: string): Promise<void> {
    await apiClient(`/api/v1/reports/business/${reportId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async duplicateReport(workspaceId: string, reportId: string): Promise<BusinessReport> {
    return apiClient<BusinessReport>(`/api/v1/reports/business/${reportId}/duplicate`, {
      method: 'POST',
      workspaceId,
    });
  },

  // Preview & Runs
  async previewReport(workspaceId: string, reportId: string, period?: string): Promise<any> {
    const q = period ? `?period=${encodeURIComponent(period)}` : '';
    return apiClient<any>(`/api/v1/reports/business/${reportId}/preview${q}`, {
      method: 'POST',
      workspaceId,
    });
  },

  async runReport(
    workspaceId: string,
    reportId: string,
    payload: { period?: string; formats?: string[]; applied_filters?: any[] } = {}
  ): Promise<ReportRun> {
    return apiClient<ReportRun>(`/api/v1/reports/business/${reportId}/run`, {
      method: 'POST',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  async listReportRuns(workspaceId: string, reportId: string): Promise<ReportRun[]> {
    return apiClient<ReportRun[]>(`/api/v1/reports/business/${reportId}/runs`, { workspaceId });
  },

  async downloadRunFile(workspaceId: string, runId: string, format: 'pdf' | 'docx' | 'xlsx' | 'csv' = 'pdf'): Promise<Blob> {
    const token = getAccessToken();
    const url = `${API_BASE_URL}/api/v1/reports/runs/${runId}/download?format=${format}`;
    const res = await fetch(url, {
      headers: {
        'X-Workspace-ID': workspaceId,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: 'include',
    });
    if (!res.ok) {
      throw new Error(`Failed to download report file (${res.status})`);
    }
    return res.blob();
  },

  // Schedules
  async createSchedule(workspaceId: string, reportId: string, data: any): Promise<ReportSchedule> {
    return apiClient<ReportSchedule>(`/api/v1/reports/business/${reportId}/schedules`, {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async updateSchedule(workspaceId: string, scheduleId: string, data: any): Promise<ReportSchedule> {
    return apiClient<ReportSchedule>(`/api/v1/reports/schedules/${scheduleId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async deleteSchedule(workspaceId: string, scheduleId: string): Promise<void> {
    await apiClient(`/api/v1/reports/schedules/${scheduleId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },
};
