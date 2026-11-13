import { apiClient } from './apiClient';

export interface ColumnSemantic {
  id: string;
  dataset_version_id: string;
  dataset_id: string;
  column_name: string;
  business_name: string;
  description?: string | null;
  semantic_type: string;
  logical_type: string;
  physical_type: string;
  aggregation_method: string;
  format_string?: string | null;
  is_dimension: boolean;
  is_measure: boolean;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  mapping_status: 'AI_SUGGESTED' | 'USER_CONFIRMED' | 'SYSTEM_INFERRED';
  confidence_score: number;
  confirmed_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetProfileDetail {
  id: string;
  dataset_version_id: string;
  dataset_id: string;
  row_count: number;
  column_count: number;
  duplicate_rows: number;
  quality_score: number;
  profile_metadata: Record<string, any>;
  warnings: Array<{ severity: string; column?: string; type: string; message: string }>;
  created_at: string;
}

export interface DatasetRelationship {
  id: string;
  workspace_id: string;
  source_dataset_id: string;
  source_version_id?: string | null;
  source_column: string;
  target_dataset_id: string;
  target_version_id?: string | null;
  target_column: string;
  relationship_type: 'ONE_TO_ONE' | 'ONE_TO_MANY' | 'MANY_TO_ONE' | 'MANY_TO_MANY';
  confidence_score: number;
  status: 'SUGGESTED' | 'CONFIRMED' | 'REJECTED';
  evidence: Record<string, any>;
  join_warning?: string | null;
  confirmed_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessContext {
  id: string;
  dataset_version_id: string;
  dataset_id: string;
  business_domain: string;
  purpose: string;
  important_entities: string[];
  key_dimensions: string[];
  important_measures: string[];
  suggested_kpis: Array<{ name: string; formula: string; description: string }>;
  data_quality_limitations: string[];
  business_assumptions: string[];
  is_user_confirmed: boolean;
  created_at: string;
  updated_at: string;
}

export interface MetricDefinition {
  id: string;
  workspace_id: string;
  dataset_id?: string | null;
  name: string;
  description?: string | null;
  formula: string;
  source_columns: string[];
  aggregation: string;
  filters: any[];
  formatting: string;
  applicable_dimensions: string[];
  validation_status: 'VALID' | 'INVALID' | 'DRAFT';
  validation_error?: string | null;
  version: number;
  approval_status: 'DRAFT' | 'APPROVED' | 'DEPRECATED';
  owner_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MetricVersion {
  id: string;
  metric_id: string;
  version_number: number;
  formula: string;
  source_columns: string[];
  aggregation: string;
  formatting: string;
  change_summary?: string | null;
  created_by_user_id?: string | null;
  created_at: string;
}

export interface DatasetIntelligenceBundle {
  dataset_id: string;
  version_id: string;
  version_number: string;
  profile?: DatasetProfileDetail | null;
  columns: ColumnSemantic[];
  relationships: DatasetRelationship[];
  business_context?: BusinessContext | null;
  metrics: MetricDefinition[];
}

export const IntelligenceService = {
  async getIntelligenceBundle(datasetId: string, versionId?: string): Promise<DatasetIntelligenceBundle> {
    const url = `/api/v1/datasets/${datasetId}/intelligence${versionId ? `?version_id=${versionId}` : ''}`;
    return apiClient<DatasetIntelligenceBundle>(url);
  },

  async runProfiling(datasetId: string, versionId?: string): Promise<DatasetIntelligenceBundle> {
    const url = `/api/v1/datasets/${datasetId}/intelligence/profile${versionId ? `?version_id=${versionId}` : ''}`;
    return apiClient<DatasetIntelligenceBundle>(url, { method: 'POST' });
  },

  async getColumnSemantics(datasetId: string, versionId?: string): Promise<ColumnSemantic[]> {
    const url = `/api/v1/datasets/${datasetId}/columns/semantics${versionId ? `?version_id=${versionId}` : ''}`;
    return apiClient<ColumnSemantic[]>(url);
  },

  async updateColumnSemantics(
    datasetId: string,
    columnName: string,
    updates: Partial<ColumnSemantic>,
    versionId?: string
  ): Promise<ColumnSemantic> {
    const url = `/api/v1/datasets/${datasetId}/columns/semantics/${encodeURIComponent(columnName)}${versionId ? `?version_id=${versionId}` : ''}`;
    return apiClient<ColumnSemantic>(url, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async getRelationships(datasetId: string): Promise<DatasetRelationship[]> {
    return apiClient<DatasetRelationship[]>(`/api/v1/datasets/${datasetId}/relationships`);
  },

  async discoverRelationships(datasetId: string): Promise<DatasetRelationship[]> {
    return apiClient<DatasetRelationship[]>(`/api/v1/datasets/${datasetId}/relationships/discover`, {
      method: 'POST',
    });
  },

  async updateRelationship(
    datasetId: string,
    relationshipId: string,
    status: 'CONFIRMED' | 'REJECTED' | 'SUGGESTED',
    relationshipType?: string
  ): Promise<DatasetRelationship> {
    return apiClient<DatasetRelationship>(
      `/api/v1/datasets/${datasetId}/relationships/${relationshipId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status, relationship_type: relationshipType }),
      }
    );
  },

  async getBusinessContext(datasetId: string, versionId?: string): Promise<BusinessContext> {
    const url = `/api/v1/datasets/${datasetId}/business-context${versionId ? `?version_id=${versionId}` : ''}`;
    return apiClient<BusinessContext>(url);
  },

  async updateBusinessContext(
    datasetId: string,
    updates: Partial<BusinessContext>,
    versionId?: string
  ): Promise<BusinessContext> {
    const url = `/api/v1/datasets/${datasetId}/business-context${versionId ? `?version_id=${versionId}` : ''}`;
    return apiClient<BusinessContext>(url, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  // Metrics API
  async listMetrics(datasetId?: string): Promise<MetricDefinition[]> {
    const url = `/api/v1/metrics${datasetId ? `?dataset_id=${datasetId}` : ''}`;
    return apiClient<MetricDefinition[]>(url);
  },

  async createMetric(data: {
    dataset_id?: string | null;
    name: string;
    description?: string;
    formula: string;
    aggregation?: string;
    formatting?: string;
    source_columns?: string[];
  }): Promise<MetricDefinition> {
    return apiClient<MetricDefinition>('/api/v1/metrics', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateMetric(metricId: string, updates: Partial<MetricDefinition> & { change_summary?: string }): Promise<MetricDefinition> {
    return apiClient<MetricDefinition>(`/api/v1/metrics/${metricId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async deleteMetric(metricId: string): Promise<void> {
    await apiClient<void>(`/api/v1/metrics/${metricId}`, { method: 'DELETE' });
  },

  async getMetricVersions(metricId: string): Promise<MetricVersion[]> {
    return apiClient<MetricVersion[]>(`/api/v1/metrics/${metricId}/versions`);
  },

  async validateFormula(formula: string, availableColumns?: string[]): Promise<{
    is_valid: boolean;
    referenced_columns: string[];
    errors: string[];
    compiled_sql?: string | null;
  }> {
    return apiClient<{
      is_valid: boolean;
      referenced_columns: string[];
      errors: string[];
      compiled_sql?: string | null;
    }>('/api/v1/metrics/validate', {
      method: 'POST',
      body: JSON.stringify({
        formula,
        available_columns: availableColumns,
      }),
    });
  },

  async calculateMetric(datasetId: string, formula: string, aggregation: string = 'SUM'): Promise<{
    metric_value: number | null;
    is_null: boolean;
    formula: string;
    compiled_sql: string;
  }> {
    return apiClient<{
      metric_value: number | null;
      is_null: boolean;
      formula: string;
      compiled_sql: string;
    }>('/api/v1/metrics/calculate', {
      method: 'POST',
      body: JSON.stringify({
        dataset_id: datasetId,
        formula,
        aggregation,
      }),
    });
  },
};
