import { apiClient, API_BASE_URL, getAccessToken } from './apiClient';

export type AdvancedWidgetType =
  | 'kpi'
  | 'bar'
  | 'stacked_bar'
  | 'grouped_bar'
  | 'horizontal_bar'
  | 'percent_bar'
  | 'top_n'
  | 'line'
  | 'multi_line'
  | 'area'
  | 'stacked_area'
  | 'combo'
  | 'heatmap'
  | 'histogram'
  | 'box_plot'
  | 'correlation'
  | 'treemap'
  | 'waterfall'
  | 'funnel'
  | 'gauge'
  | 'pareto'
  | 'pie'
  | 'donut'
  | 'scatter'
  | 'table'
  | 'text';

export interface ChartAnnotation {
  id: string;
  type: 'line' | 'marker' | 'threshold';
  label: string;
  value?: number;
  date?: string;
  color?: string;
}

export interface DashboardWidget {
  id: string;
  dashboard_id: string;
  dataset_id: string | null;
  dataset_version_id: string | null;
  widget_type: AdvancedWidgetType;
  title: string;
  description?: string | null;
  grid_x: number;
  grid_y: number;
  grid_w: number;
  grid_h: number;
  query_config: {
    metric_column?: string;
    secondary_metric_column?: string;
    group_by_column?: string;
    sub_group_by_column?: string;
    hierarchy_levels?: string[];
    time_column?: string;
    series_column?: string;
    x_column?: string;
    y_column?: string;
    label_column?: string;
    columns?: string[];
    aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'distinct_count';
    granularity?: 'day' | 'week' | 'month' | 'quarter' | 'year';
    sort_column?: string;
    sort_direction?: 'asc' | 'desc';
    limit?: number;
    bins?: number;
    target_value?: number;
    min_value?: number;
    max_value?: number;
    compare_to?: 'prior_period' | 'yoy' | 'target';
    filters?: Array<{
      column: string;
      operator: string;
      value: any;
      second_value?: any;
    }>;
    text_content?: string;
    [key: string]: any;
  };
  display_settings: {
    theme?: string;
    color?: string;
    colors?: string[];
    color_palette?: string;
    unit?: string;
    number_format?: 'currency' | 'percent' | 'number' | 'compact';
    show_legend?: boolean;
    legend_position?: 'top' | 'bottom' | 'left' | 'right' | 'none';
    show_labels?: boolean;
    chart_style?: string;
    annotations?: ChartAnnotation[];
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

export interface DashboardFilter {
  id: string;
  dashboard_id: string;
  name: string;
  column_name: string;
  filter_type: 'date_range' | 'dropdown' | 'multi_select' | 'numeric_range' | 'text';
  default_operator: string;
  default_value: any;
  config: {
    options?: Array<{ label: string; value: any }>;
    min?: number;
    max?: number;
    placeholder?: string;
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

export interface Dashboard {
  id: string;
  workspace_id: string;
  created_by?: string | null;
  title: string;
  description?: string | null;
  visibility: string;
  is_archived: boolean;
  layout_config: {
    columns?: number;
    gap?: number;
    theme?: string;
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
  widget_count?: number;
  filter_count?: number;
  widgets?: DashboardWidget[];
  filters?: DashboardFilter[];
}

export interface DashboardListResponse {
  items: Dashboard[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface WidgetQueryResponse {
  widget_id: string;
  widget_type: string;
  data: any;
  row_count: number;
  execution_time_ms: number;
  dataset_version_id?: string | null;
  dataset_id?: string | null;
  metadata?: Record<string, any>;
}

export const dashboardService = {
  async listDashboards(
    workspaceId: string,
    search?: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<DashboardListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search) params.append('search', search);

    return apiClient<DashboardListResponse>(`/api/v1/dashboards?${params.toString()}`, {
      workspaceId,
    });
  },

  async getDashboard(workspaceId: string, dashboardId: string): Promise<Dashboard> {
    return apiClient<Dashboard>(`/api/v1/dashboards/${dashboardId}`, {
      workspaceId,
    });
  },

  async createDashboard(
    workspaceId: string,
    data: {
      title: string;
      description?: string;
      visibility?: string;
      layout_config?: Record<string, any>;
    }
  ): Promise<Dashboard> {
    return apiClient<Dashboard>('/api/v1/dashboards', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async updateDashboard(
    workspaceId: string,
    dashboardId: string,
    data: Partial<Dashboard>
  ): Promise<Dashboard> {
    return apiClient<Dashboard>(`/api/v1/dashboards/${dashboardId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async duplicateDashboard(workspaceId: string, dashboardId: string): Promise<Dashboard> {
    return apiClient<Dashboard>(`/api/v1/dashboards/${dashboardId}/duplicate`, {
      method: 'POST',
      workspaceId,
    });
  },

  async deleteDashboard(
    workspaceId: string,
    dashboardId: string,
    hardDelete: boolean = false
  ): Promise<void> {
    return apiClient<void>(
      `/api/v1/dashboards/${dashboardId}${hardDelete ? '?hard_delete=true' : ''}`,
      {
        method: 'DELETE',
        workspaceId,
      }
    );
  },

  async addWidget(
    workspaceId: string,
    dashboardId: string,
    widget: Partial<DashboardWidget>
  ): Promise<DashboardWidget> {
    return apiClient<DashboardWidget>(`/api/v1/dashboards/${dashboardId}/widgets`, {
      method: 'POST',
      body: JSON.stringify(widget),
      workspaceId,
    });
  },

  async updateWidget(
    workspaceId: string,
    dashboardId: string,
    widgetId: string,
    widget: Partial<DashboardWidget>
  ): Promise<DashboardWidget> {
    return apiClient<DashboardWidget>(
      `/api/v1/dashboards/${dashboardId}/widgets/${widgetId}`,
      {
        method: 'PUT',
        body: JSON.stringify(widget),
        workspaceId,
      }
    );
  },

  async deleteWidget(
    workspaceId: string,
    dashboardId: string,
    widgetId: string
  ): Promise<void> {
    return apiClient<void>(`/api/v1/dashboards/${dashboardId}/widgets/${widgetId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async updateLayout(
    workspaceId: string,
    dashboardId: string,
    widgets: Array<{ id: string; grid_x: number; grid_y: number; grid_w: number; grid_h: number }>
  ): Promise<DashboardWidget[]> {
    return apiClient<DashboardWidget[]>(`/api/v1/dashboards/${dashboardId}/layout`, {
      method: 'POST',
      body: JSON.stringify({ widgets }),
      workspaceId,
    });
  },

  async addFilter(
    workspaceId: string,
    dashboardId: string,
    filter: Partial<DashboardFilter>
  ): Promise<DashboardFilter> {
    return apiClient<DashboardFilter>(`/api/v1/dashboards/${dashboardId}/filters`, {
      method: 'POST',
      body: JSON.stringify(filter),
      workspaceId,
    });
  },

  async updateFilter(
    workspaceId: string,
    dashboardId: string,
    filterId: string,
    filter: Partial<DashboardFilter>
  ): Promise<DashboardFilter> {
    return apiClient<DashboardFilter>(
      `/api/v1/dashboards/${dashboardId}/filters/${filterId}`,
      {
        method: 'PUT',
        body: JSON.stringify(filter),
        workspaceId,
      }
    );
  },

  async deleteFilter(
    workspaceId: string,
    dashboardId: string,
    filterId: string
  ): Promise<void> {
    return apiClient<void>(`/api/v1/dashboards/${dashboardId}/filters/${filterId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async queryWidget(
    workspaceId: string,
    dashboardId: string,
    widgetId: string,
    filters?: Array<{ column: string; operator: string; value: any; second_value?: any }>,
    options?: {
      drillLevel?: number;
      drillFilters?: any[];
      compareTo?: string;
      targetValue?: number;
    }
  ): Promise<WidgetQueryResponse> {
    return apiClient<WidgetQueryResponse>(
      `/api/v1/dashboards/${dashboardId}/widgets/${widgetId}/query`,
      {
        method: 'POST',
        body: JSON.stringify({
          filters: filters || [],
          drill_level: options?.drillLevel,
          drill_filters: options?.drillFilters,
          compare_to: options?.compareTo,
          target_value: options?.targetValue,
        }),
        workspaceId,
      }
    );
  },

  async exportDashboard(
    workspaceId: string,
    dashboardId: string,
    format: 'pdf' | 'csv' | 'xlsx',
    filters?: any[]
  ): Promise<Blob> {
    const token = getAccessToken();
    const url = `${API_BASE_URL}/api/v1/dashboards/${dashboardId}/export`;

    const res = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Workspace-ID': workspaceId,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ format, filters: filters || [] }),
    });

    if (!res.ok) {
      throw new Error(`Failed to export dashboard as ${format.toUpperCase()}`);
    }

    return await res.blob();
  },
};

