import { apiClient } from './apiClient';

export interface AutoDashboardRequest {
  dataset_id: string;
  dataset_version_id?: string;
  business_domain?: string;
  user_objective?: string;
  visual_style?: string;
}

export interface AutoDashboardStatusResponse {
  generation_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  stage: string;
  progress_pct: number;
  message: string;
  dataset_id: string;
  dataset_name: string;
  preview_ready: boolean;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedKPIItem {
  id: string;
  title: string;
  metric_column?: string | null;
  aggregation: string;
  formatted_value: string;
  numeric_value: number;
  change_pct?: number | null;
  change_direction?: string | null;
  target_value?: number | null;
  grid_x: number;
  grid_y: number;
  grid_w: number;
  grid_h: number;
  display_settings: Record<string, any>;
}

export interface GeneratedChartItem {
  id: string;
  widget_type: string;
  title: string;
  description?: string | null;
  grid_x: number;
  grid_y: number;
  grid_w: number;
  grid_h: number;
  query_config: Record<string, any>;
  display_settings: Record<string, any>;
  calculated_data?: any;
}

export interface GeneratedFilterItem {
  id: string;
  name: string;
  column_name: string;
  filter_type: string;
  default_operator: string;
  default_value?: any;
  config: Record<string, any>;
}

export interface GeneratedInsightItem {
  id: string;
  title: string;
  observation: string;
  evidence: string;
  category: string;
  recommendation?: string | null;
}

export interface AutoDashboardPreviewResponse {
  generation_id: string;
  dataset_id: string;
  dataset_name: string;
  dataset_version_id: string;
  title: string;
  description: string;
  business_domain: string;
  theme: string;
  kpis: GeneratedKPIItem[];
  charts: GeneratedChartItem[];
  filters: GeneratedFilterItem[];
  insights: GeneratedInsightItem[];
  total_widgets: number;
  created_at: string;
}

export interface AutoDashboardSaveRequest {
  title?: string;
  description?: string;
  theme?: string;
  kpis?: GeneratedKPIItem[];
  charts?: GeneratedChartItem[];
  filters?: GeneratedFilterItem[];
}

export const AutoDashboardService = {
  async startGeneration(
    workspaceId: string,
    req: AutoDashboardRequest
  ): Promise<AutoDashboardStatusResponse> {
    return apiClient<AutoDashboardStatusResponse>(
      `/api/v1/dashboards/auto-generate?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify(req),
        workspaceId,
      }
    );
  },

  async getStatus(
    workspaceId: string,
    generationId: string
  ): Promise<AutoDashboardStatusResponse> {
    return apiClient<AutoDashboardStatusResponse>(
      `/api/v1/dashboards/auto-generate/${generationId}?workspace_id=${workspaceId}`,
      {
        method: 'GET',
        workspaceId,
      }
    );
  },

  async getPreview(
    workspaceId: string,
    generationId: string
  ): Promise<AutoDashboardPreviewResponse> {
    return apiClient<AutoDashboardPreviewResponse>(
      `/api/v1/dashboards/auto-generate/${generationId}/preview?workspace_id=${workspaceId}`,
      {
        method: 'GET',
        workspaceId,
      }
    );
  },

  async saveDashboard(
    workspaceId: string,
    generationId: string,
    saveReq: AutoDashboardSaveRequest
  ): Promise<any> {
    return apiClient<any>(
      `/api/v1/dashboards/auto-generate/${generationId}/save?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify(saveReq),
        workspaceId,
      }
    );
  },

  async cancelGeneration(
    workspaceId: string,
    generationId: string
  ): Promise<{ cancelled: boolean }> {
    return apiClient<{ cancelled: boolean }>(
      `/api/v1/dashboards/auto-generate/${generationId}/cancel?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        workspaceId,
      }
    );
  },
};

