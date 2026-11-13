// DataLens API Client with in-memory Bearer Token, CSRF, and Automatic Refresh

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

let inMemoryAccessToken: string | null = null;
let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

function onRefreshed(newToken: string | null) {
  refreshSubscribers.forEach((cb) => cb(newToken));
  refreshSubscribers = [];
}

export async function refreshAccessToken(): Promise<string | null> {
  const csrfToken = getCookie('datalens_csrf_token');
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
    });

    if (!res.ok) {
      setAccessToken(null);
      return null;
    }

    const data = await res.json();
    const token = data.access_token || null;
    setAccessToken(token);
    return token;
  } catch (e) {
    setAccessToken(null);
    return null;
  }
}

export interface ApiRequestOptions extends RequestInit {
  workspaceId?: string;
  skipAuth?: boolean;
}

export async function apiClient<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Inject in-memory access token
  if (!options.skipAuth && inMemoryAccessToken) {
    headers.set('Authorization', `Bearer ${inMemoryAccessToken}`);
  }

  // Inject Workspace ID header if provided
  if (options.workspaceId) {
    headers.set('X-Workspace-ID', options.workspaceId);
  }

  // Inject CSRF token for state-changing requests
  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCookie('datalens_csrf_token');
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include', // Always send HttpOnly cookies for refresh token handling
  };

  let response: Response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (networkError: any) {
    throw new Error(
      `Network connection error: Unable to reach DataLens backend API at ${API_BASE_URL}. Ensure the backend service is running.`
    );
  }

  // Handle 401 Unauthorized with Automatic Refresh
  if (response.status === 401 && !options.skipAuth && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true;
      const newToken = await refreshAccessToken();
      isRefreshing = false;
      onRefreshed(newToken);

      if (newToken) {
        // Retry original request with new token
        headers.set('Authorization', `Bearer ${newToken}`);
        const retryRes = await fetch(url, { ...fetchOptions, headers });
        if (!retryRes.ok) {
          const errData = await retryRes.json().catch(() => ({}));
          throw new Error(errData?.error?.message || errData?.detail || `HTTP error ${retryRes.status}`);
        }
        return (await retryRes.json()) as T;
      }
    } else {
      // Queue until refreshing finishes
      const retryToken = await new Promise<string | null>((resolve) => {
        refreshSubscribers.push(resolve);
      });

      if (retryToken) {
        headers.set('Authorization', `Bearer ${retryToken}`);
        const retryRes = await fetch(url, { ...fetchOptions, headers });
        if (!retryRes.ok) {
          const errData = await retryRes.json().catch(() => ({}));
          throw new Error(errData?.error?.message || errData?.detail || `HTTP error ${retryRes.status}`);
        }
        return (await retryRes.json()) as T;
      }
    }
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const message = errData?.error?.message || errData?.detail || `Request failed with status ${response.status}`;
    const code = errData?.error?.code || 'API_ERROR';
    const error: any = new Error(message);
    error.code = code;
    error.status = response.status;
    error.details = errData?.error?.details || {};
    throw error;
  }

  // If status is 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

// ==========================================
// DATASET API HELPERS
// ==========================================

export interface ApiDatasetListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  sortBy?: string;
  sortDir?: 'asc' | 'desc';
}

export interface ApiDatasetRowParams {
  versionId?: string;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortDir?: 'asc' | 'desc';
  columns?: string[];
}

export const DatasetApi = {
  async list(workspaceId: string, params: ApiDatasetListParams = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set('page', String(params.page));
    if (params.pageSize) q.set('page_size', String(params.pageSize));
    if (params.search) q.set('search', params.search);
    if (params.status) q.set('status', params.status);
    if (params.sortBy) q.set('sort_by', params.sortBy);
    if (params.sortDir) q.set('sort_dir', params.sortDir);

    const qs = q.toString() ? `?${q.toString()}` : '';
    return apiClient<any>(`/api/v1/datasets${qs}`, { workspaceId });
  },

  async get(workspaceId: string, datasetId: string) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}`, { workspaceId });
  },

  async getStatus(workspaceId: string, datasetId: string) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/status`, { workspaceId });
  },

  async getVersions(workspaceId: string, datasetId: string) {
    return apiClient<any[]>(`/api/v1/datasets/${datasetId}/versions`, { workspaceId });
  },

  async getRows(workspaceId: string, datasetId: string, params: ApiDatasetRowParams = {}) {
    const q = new URLSearchParams();
    if (params.versionId) q.set('version_id', params.versionId);
    if (params.page) q.set('page', String(params.page));
    if (params.pageSize) q.set('page_size', String(params.pageSize));
    if (params.sortBy) q.set('sort_by', params.sortBy);
    if (params.sortDir) q.set('sort_dir', params.sortDir);
    if (params.columns) params.columns.forEach((col) => q.append('columns', col));

    const qs = q.toString() ? `?${q.toString()}` : '';
    return apiClient<any>(`/api/v1/datasets/${datasetId}/rows${qs}`, { workspaceId });
  },

  async upload(workspaceId: string, formData: FormData) {
    return apiClient<any>('/api/v1/datasets', {
      method: 'POST',
      body: formData,
      workspaceId,
    });
  },

  async uploadReplacement(workspaceId: string, datasetId: string, formData: FormData) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/versions`, {
      method: 'POST',
      body: formData,
      workspaceId,
    });
  },

  async delete(workspaceId: string, datasetId: string, permanent: boolean = false) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}?permanent=${permanent}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async downloadOriginalFile(workspaceId: string, datasetId: string, versionId: string): Promise<Blob> {
    const token = getAccessToken();
    const url = `${API_BASE_URL}/api/v1/datasets/${datasetId}/versions/${versionId}/download`;
    const res = await fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'X-Workspace-ID': workspaceId,
      },
      credentials: 'include',
    });
    if (!res.ok) {
      throw new Error(`Failed to download original file: HTTP ${res.status}`);
    }
    return res.blob();
  },
};

// ==========================================
// ANALYTICS API HELPERS
// ==========================================

export const AnalyticsApi = {
  async getProfile(workspaceId: string, datasetId: string, versionId?: string) {
    const qs = versionId ? `?version_id=${versionId}` : '';
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analytics/profile${qs}`, {
      method: 'POST',
      workspaceId,
    });
  },

  async getDescriptiveStats(workspaceId: string, datasetId: string, req: any = {}) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analytics/summary`, {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async getAggregation(workspaceId: string, datasetId: string, req: any) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analytics/aggregate`, {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async getTimeSeries(workspaceId: string, datasetId: string, req: any) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analytics/time-series`, {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async getQuality(workspaceId: string, datasetId: string, versionId?: string) {
    const qs = versionId ? `?version_id=${versionId}` : '';
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analytics/quality${qs}`, {
      method: 'POST',
      workspaceId,
    });
  },

  async compareVersions(workspaceId: string, datasetId: string, req: any) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analytics/compare`, {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async createAnalysisRun(workspaceId: string, datasetId: string, req: any) {
    return apiClient<any>(`/api/v1/datasets/${datasetId}/analysis-runs`, {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async listAnalysisRuns(workspaceId: string, datasetId: string) {
    return apiClient<any[]>(`/api/v1/datasets/${datasetId}/analysis-runs`, { workspaceId });
  },
};

// ==========================================
// REPORTS API HELPERS
// ==========================================

export const ReportApi = {
  async create(workspaceId: string, req: any) {
    return apiClient<any>('/api/v1/reports', {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async list(workspaceId: string, params: { page?: number; pageSize?: number; datasetId?: string; format?: string } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set('page', String(params.page));
    if (params.pageSize) q.set('page_size', String(params.pageSize));
    if (params.datasetId) q.set('dataset_id', params.datasetId);
    if (params.format) q.set('format', params.format);

    const qs = q.toString() ? `?${q.toString()}` : '';
    return apiClient<any>(`/api/v1/reports${qs}`, { workspaceId });
  },

  async get(workspaceId: string, reportId: string) {
    return apiClient<any>(`/api/v1/reports/${reportId}`, { workspaceId });
  },

  async download(workspaceId: string, reportId: string): Promise<Blob> {
    const token = getAccessToken();
    const url = `${API_BASE_URL}/api/v1/reports/${reportId}/download`;
    const res = await fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'X-Workspace-ID': workspaceId,
      },
      credentials: 'include',
    });
    if (!res.ok) {
      throw new Error(`Failed to download report: HTTP ${res.status}`);
    }
    return res.blob();
  },

  async delete(workspaceId: string, reportId: string) {
    return apiClient<any>(`/api/v1/reports/${reportId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },
};

// ==========================================
// AI ANALYTICS API HELPERS
// ==========================================

export interface AIAskRequestPayload {
  dataset_id: string;
  question: string;
  version_id?: string;
  conversation_history?: Array<{ role: string; content: string }>;
  options?: Record<string, any>;
}

export interface AIMetricCardData {
  title: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  subtitle?: string;
}

export interface AIChartDataPayload {
  chart_type: 'bar' | 'line' | 'pie';
  title: string;
  x_key: string;
  y_keys: string[];
  series: Array<Record<string, any>>;
}

export interface AITableDataPayload {
  columns: string[];
  rows: Array<Record<string, any>>;
  total_rows?: number;
}

export interface AIEvidenceItemPayload {
  metric_name: string;
  computed_value: any;
  aggregation_type: string;
  source_column: string;
  formula?: string;
}

export interface AIAskResponsePayload {
  question: string;
  executive_summary: string;
  detailed_narrative: string;
  ai_status: 'operational' | 'disabled' | 'error';
  metric_cards: AIMetricCardData[];
  chart?: AIChartDataPayload;
  table?: AITableDataPayload;
  evidence: AIEvidenceItemPayload[];
  suggested_follow_ups: string[];
  execution_time_ms: number;
  dataset_version_id?: string;
  analysis_run_id?: string;
}

export interface AIStatusResponsePayload {
  ai_enabled: boolean;
  provider: string;
  model: string;
  operational: boolean;
  error?: string | null;
}

export const AiApi = {
  async getStatus(workspaceId?: string): Promise<AIStatusResponsePayload> {
    return apiClient<AIStatusResponsePayload>('/api/v1/ai/status', {
      method: 'GET',
      ...(workspaceId ? { workspaceId } : {}),
    });
  },

  async ask(workspaceId: string, req: AIAskRequestPayload): Promise<AIAskResponsePayload> {
    return apiClient<AIAskResponsePayload>('/api/v1/ai/ask', {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async clarify(
    workspaceId: string,
    req: {
      dataset_id: string;
      question: string;
      original_plan: any;
      user_clarification: string;
      version_id?: string;
    }
  ): Promise<AIAskResponsePayload> {
    return apiClient<AIAskResponsePayload>('/api/v1/ai/clarify', {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },

  async explain(
    workspaceId: string,
    req: {
      dataset_id: string;
      analysis_run_id: string;
      audience?: string;
    }
  ): Promise<{ analysis_run_id: string; explanation: string }> {
    return apiClient<{ analysis_run_id: string; explanation: string }>('/api/v1/ai/explain', {
      method: 'POST',
      body: JSON.stringify(req),
      workspaceId,
    });
  },
};

// =========================================================================
// PROMPT LAB API
// =========================================================================

export interface PromptTemplateItem {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  category: string;
  tags: string[];
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  versions_count: number;
  latest_version_number: number;
}

export interface PromptVersionItem {
  id: string;
  prompt_id: string;
  version_number: number;
  system_prompt: string;
  user_prompt_template: string;
  variables: Array<{ name: string; description?: string; required?: boolean; default?: string }>;
  model_config_snapshot: { provider: string; model: string; temperature: number; max_tokens: number };
  change_description: string | null;
  created_by: string | null;
  created_at: string;
}

export interface PromptDetailItem extends PromptTemplateItem {
  created_by: string | null;
  current_version: PromptVersionItem | null;
}

export interface PlaygroundExecutePayload {
  system_prompt: string;
  user_prompt_template: string;
  variables: Record<string, any>;
  provider?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  prompt_version_id?: string;
}

export interface PlaygroundExecuteResult {
  rendered_system_prompt: string;
  rendered_user_prompt: string;
  response_text: string;
  provider: string;
  model: string;
  prompt_version: string | null;
  execution_timestamp: string;
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  provider_status: string;
  is_simulated: boolean;
}

export interface TestCaseItem {
  id: string;
  experiment_id: string;
  name: string;
  variables: Record<string, any>;
  expected_output: string | null;
  expected_keywords: string[];
  created_at: string;
}

export interface ExperimentRunItem {
  id: string;
  experiment_id: string;
  prompt_version_id: string;
  test_case_id: string;
  rendered_system_prompt: string;
  rendered_user_prompt: string;
  response_text: string | null;
  provider: string;
  model: string;
  status: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number;
  estimated_cost_usd: number | null;
  error_message: string | null;
  created_at: string;
  evaluations: Array<{
    id: string;
    metric_name: string;
    score: number;
    max_score: number;
    evaluation_method: string;
    explanation: string | null;
    evaluated_by_model: string | null;
  }>;
}

export interface ExperimentItem {
  id: string;
  workspace_id: string;
  prompt_id: string | null;
  name: string;
  description: string | null;
  version_ids: string[];
  model_config_override: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_by: string | null;
  created_at: string;
  updated_at: string;
  test_cases: TestCaseItem[];
  runs_count: number;
  completed_runs_count: number;
}

export interface ExperimentComparisonItem {
  experiment_id: string;
  experiment_name: string;
  total_test_cases: number;
  versions_compared: Array<{
    version_id: string;
    version_number: number;
    runs_count: number;
    successful_runs: number;
    failed_runs: number;
    success_rate: number;
    avg_latency_ms: number;
    avg_input_tokens: number | null;
    avg_output_tokens: number | null;
    total_cost_usd: number | null;
    avg_overall_score: number;
    metric_scores: Record<string, number>;
  }>;
  best_version_id: string | null;
  best_version_rationale: string | null;
  observations: string[];
}

export const PromptLabApi = {
  async listPrompts(workspaceId: string, params?: { search?: string; category?: string; include_archived?: boolean }): Promise<PromptTemplateItem[]> {
    const q = new URLSearchParams();
    if (params?.search) q.set('search', params.search);
    if (params?.category) q.set('category', params.category);
    if (params?.include_archived) q.set('include_archived', 'true');
    const queryStr = q.toString() ? `?${q.toString()}` : '';

    return apiClient<PromptTemplateItem[]>(`/api/v1/prompts${queryStr}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async getPrompt(workspaceId: string, promptId: string): Promise<PromptDetailItem> {
    return apiClient<PromptDetailItem>(`/api/v1/prompts/${promptId}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async createPrompt(workspaceId: string, data: any): Promise<PromptDetailItem> {
    return apiClient<PromptDetailItem>('/api/v1/prompts', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async updatePrompt(workspaceId: string, promptId: string, data: any): Promise<PromptDetailItem> {
    return apiClient<PromptDetailItem>(`/api/v1/prompts/${promptId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async duplicatePrompt(workspaceId: string, promptId: string): Promise<PromptDetailItem> {
    return apiClient<PromptDetailItem>(`/api/v1/prompts/${promptId}/duplicate`, {
      method: 'POST',
      workspaceId,
    });
  },

  async archivePrompt(workspaceId: string, promptId: string): Promise<{ message: string; id: string }> {
    return apiClient<{ message: string; id: string }>(`/api/v1/prompts/${promptId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async listVersions(workspaceId: string, promptId: string): Promise<PromptVersionItem[]> {
    return apiClient<PromptVersionItem[]>(`/api/v1/prompts/${promptId}/versions`, {
      method: 'GET',
      workspaceId,
    });
  },

  async createVersion(workspaceId: string, promptId: string, data: any): Promise<PromptVersionItem> {
    return apiClient<PromptVersionItem>(`/api/v1/prompts/${promptId}/versions`, {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async restoreVersion(workspaceId: string, promptId: string, versionId: string): Promise<PromptVersionItem> {
    return apiClient<PromptVersionItem>(`/api/v1/prompts/${promptId}/versions/${versionId}/restore`, {
      method: 'POST',
      workspaceId,
    });
  },

  async compareVersions(workspaceId: string, promptId: string, versionA: string, versionB: string): Promise<any> {
    return apiClient<any>(`/api/v1/prompts/${promptId}/compare?version_a=${versionA}&version_b=${versionB}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async executePlayground(workspaceId: string, data: PlaygroundExecutePayload): Promise<PlaygroundExecuteResult> {
    return apiClient<PlaygroundExecuteResult>('/api/v1/prompts/execute', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async listExperiments(workspaceId: string, promptId?: string): Promise<ExperimentItem[]> {
    const q = promptId ? `?prompt_id=${promptId}` : '';
    return apiClient<ExperimentItem[]>(`/api/v1/experiments${q}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async getExperiment(workspaceId: string, experimentId: string): Promise<ExperimentItem> {
    return apiClient<ExperimentItem>(`/api/v1/experiments/${experimentId}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async createExperiment(workspaceId: string, data: any): Promise<ExperimentItem> {
    return apiClient<ExperimentItem>('/api/v1/experiments', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async runExperiment(workspaceId: string, experimentId: string): Promise<ExperimentItem> {
    return apiClient<ExperimentItem>(`/api/v1/experiments/${experimentId}/run`, {
      method: 'POST',
      workspaceId,
    });
  },

  async cancelExperiment(workspaceId: string, experimentId: string): Promise<{ message: string; status: string }> {
    return apiClient<{ message: string; status: string }>(`/api/v1/experiments/${experimentId}/cancel`, {
      method: 'POST',
      workspaceId,
    });
  },

  async getExperimentResults(workspaceId: string, experimentId: string): Promise<ExperimentRunItem[]> {
    return apiClient<ExperimentRunItem[]>(`/api/v1/experiments/${experimentId}/results`, {
      method: 'GET',
      workspaceId,
    });
  },

  async evaluateExperiment(workspaceId: string, experimentId: string, criteria: any[]): Promise<{ message: string; evaluations_created: number }> {
    return apiClient<{ message: string; evaluations_created: number }>(`/api/v1/experiments/${experimentId}/evaluate`, {
      method: 'POST',
      body: JSON.stringify({ criteria }),
      workspaceId,
    });
  },

  async getExperimentComparison(workspaceId: string, experimentId: string): Promise<ExperimentComparisonItem> {
    return apiClient<ExperimentComparisonItem>(`/api/v1/experiments/${experimentId}/comparison`, {
      method: 'GET',
      workspaceId,
    });
  },
};

// =========================================================================
// ADVANCED ANALYTICS & MACHINE LEARNING TYPES & API
// =========================================================================

export interface AnomalyPoint {
  row_index: number;
  timestamp?: string | null;
  actual_value: number;
  expected_value?: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
  anomaly_score: number;
  severity: 'low' | 'medium' | 'high';
  is_anomaly: boolean;
}

export interface AnomalyDetectResponse {
  model_run_id: string;
  dataset_id: string;
  dataset_version_id: string;
  target_column: string;
  algorithm: string;
  total_records_analyzed: number;
  anomalies_detected_count: number;
  anomaly_percentage: number;
  summary_metrics: Record<string, any>;
  anomalous_points: AnomalyPoint[];
  detection_method_explanation: string;
  caveats_and_limitations: string[];
  execution_time_ms: number;
}

export interface ForecastPoint {
  period_index: number;
  timestamp: string;
  forecast_value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  model_run_id: string;
  dataset_id: string;
  dataset_version_id: string;
  target_column: string;
  time_column: string;
  algorithm: string;
  forecast_horizon: number;
  historical_points: Array<{ timestamp: string; actual_value: number }>;
  forecast_points: ForecastPoint[];
  backtest_metrics: { mae?: number; rmse?: number; mape?: number };
  baseline_comparison: Record<string, any>;
  method_explanation: string;
  caveats_and_limitations: string[];
  execution_time_ms: number;
}

export interface ClusterProfile {
  cluster_id: number;
  cluster_name: string;
  record_count: number;
  percentage: number;
  feature_means: Record<string, number>;
  feature_minima: Record<string, number>;
  feature_maxima: Record<string, number>;
  characterization: string;
}

export interface SegmentationResponse {
  model_run_id: string;
  dataset_id: string;
  dataset_version_id: string;
  algorithm: string;
  cluster_count: number;
  total_records_clustered: number;
  feature_columns: string[];
  clusters: ClusterProfile[];
  silhouette_score: number | null;
  inertia: number | null;
  segment_comparison_summary: string;
  method_explanation: string;
  caveats_and_limitations: string[];
  execution_time_ms: number;
}

export interface ModelRunListItem {
  id: string;
  workspace_id: string;
  dataset_id: string;
  dataset_version_id: string;
  model_type: string;
  algorithm: string;
  status: string;
  parameters: Record<string, any>;
  feature_columns: string[];
  metrics: Record<string, any>;
  duration_ms: number;
  created_at: string;
}

export interface ModelRunDetailResponse extends ModelRunListItem {
  result_summary: Record<string, any>;
  ai_insight?: string | null;
}

export interface InsightResponse {
  model_run_id: string;
  insight_narrative: string;
  key_findings: string[];
  limitations: string[];
  suggested_actions: string[];
  is_ai_generated?: boolean;
}

export const MlApi = {
  async detectAnomalies(
    workspaceId: string,
    data: {
      dataset_id: string;
      version_id?: string;
      target_column: string;
      time_column?: string;
      algorithm?: 'z_score' | 'iqr' | 'isolation_forest';
      sensitivity?: number;
      max_anomalies_return?: number;
    }
  ): Promise<AnomalyDetectResponse> {
    return apiClient<AnomalyDetectResponse>('/api/v1/ml/anomaly', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async generateForecast(
    workspaceId: string,
    data: {
      dataset_id: string;
      version_id?: string;
      target_column: string;
      time_column: string;
      forecast_horizon?: number;
      algorithm?: 'moving_average' | 'exponential_smoothing' | 'seasonal_naive' | 'linear_trend';
      confidence_level?: number;
      seasonality_period?: number;
    }
  ): Promise<ForecastResponse> {
    return apiClient<ForecastResponse>('/api/v1/ml/forecast', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async runSegmentation(
    workspaceId: string,
    data: {
      dataset_id: string;
      version_id?: string;
      feature_columns: string[];
      algorithm?: 'kmeans' | 'hierarchical';
      cluster_count?: number;
      scale_features?: boolean;
      cluster_label_prefix?: string;
    }
  ): Promise<SegmentationResponse> {
    return apiClient<SegmentationResponse>('/api/v1/ml/segmentation', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async listModelRuns(
    workspaceId: string,
    datasetId?: string,
    modelType?: string
  ): Promise<ModelRunListItem[]> {
    const params = new URLSearchParams();
    if (datasetId) params.append('dataset_id', datasetId);
    if (modelType) params.append('model_type', modelType);
    const q = params.toString() ? `?${params.toString()}` : '';
    return apiClient<ModelRunListItem[]>(`/api/v1/ml/runs${q}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async getModelRun(workspaceId: string, runId: string): Promise<ModelRunDetailResponse> {
    return apiClient<ModelRunDetailResponse>(`/api/v1/ml/runs/${runId}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async generateInsight(
    workspaceId: string,
    runId: string,
    payload: { audience?: 'executive' | 'analyst' | 'operational'; include_recommendations?: boolean } = {}
  ): Promise<InsightResponse> {
    return apiClient<InsightResponse>(`/api/v1/ml/runs/${runId}/insights`, {
      method: 'POST',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  async downloadReport(workspaceId: string, runId: string, format: 'pdf' | 'docx' | 'xlsx' | 'csv' = 'pdf'): Promise<Blob> {
    const token = getAccessToken();
    const headers: Record<string, string> = {
      'X-Workspace-ID': workspaceId,
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE_URL}/api/v1/ml/runs/${runId}/report?format=${format}`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });
    if (!res.ok) {
      throw new Error(`Failed to download report (${res.status})`);
    }
    return res.blob();
  },
};





