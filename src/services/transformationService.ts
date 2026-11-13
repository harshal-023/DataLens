import { apiClient } from './apiClient';

export type TransformationOpType =
  | 'join'
  | 'append'
  | 'clean_nulls'
  | 'clean_duplicates'
  | 'type_cast'
  | 'string_op'
  | 'formula'
  | 'filter'
  | 'select_columns';

export interface TransformationStep {
  id: string;
  pipeline_id: string;
  step_order: number;
  operation_type: TransformationOpType;
  configuration: Record<string, any>;
  input_references: Record<string, any>;
  output_schema: Array<{ name: string; data_type: string }>;
  created_at: string;
  updated_at: string;
}

export interface TransformationPipeline {
  id: string;
  workspace_id: string;
  created_by?: string | null;
  name: string;
  description?: string | null;
  source_dataset_ids: string[];
  status: string;
  steps: TransformationStep[];
  created_at: string;
  updated_at: string;
}

export interface TransformationPipelineSummary {
  id: string;
  workspace_id: string;
  created_by?: string | null;
  name: string;
  description?: string | null;
  source_dataset_ids: string[];
  status: string;
  step_count: number;
  last_run_status?: string | null;
  last_run_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransformationRun {
  id: string;
  pipeline_id: string;
  workspace_id: string;
  triggered_by?: string | null;
  source_dataset_versions: Record<string, any>;
  output_dataset_id?: string | null;
  output_dataset_version_id?: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_details?: string | null;
  execution_duration_ms: number;
  row_count: number;
  created_at: string;
  updated_at: string;
}

export interface PreviewColumn {
  name: string;
  data_type: string;
}

export interface PreviewResponse {
  columns: PreviewColumn[];
  rows: Record<string, any>[];
  total_rows_sampled: number;
  step_executed: number;
  execution_duration_ms: number;
}

export interface ValidateFormulaResponse {
  valid: boolean;
  ast_summary?: string | null;
  referenced_columns: string[];
  sql_expression?: string | null;
  error?: string | null;
}

export const transformationService = {
  async listPipelines(workspaceId: string): Promise<TransformationPipelineSummary[]> {
    return apiClient<TransformationPipelineSummary[]>('/api/v1/transformations/pipelines', {
      workspaceId,
    });
  },

  async getPipeline(workspaceId: string, pipelineId: string): Promise<TransformationPipeline> {
    return apiClient<TransformationPipeline>(`/api/v1/transformations/pipelines/${pipelineId}`, {
      workspaceId,
    });
  },

  async createPipeline(
    workspaceId: string,
    data: {
      name: string;
      description?: string;
      source_dataset_ids?: string[];
      status?: string;
    }
  ): Promise<TransformationPipeline> {
    return apiClient<TransformationPipeline>('/api/v1/transformations/pipelines', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async updatePipeline(
    workspaceId: string,
    pipelineId: string,
    data: {
      name?: string;
      description?: string;
      source_dataset_ids?: string[];
      status?: string;
    }
  ): Promise<TransformationPipeline> {
    return apiClient<TransformationPipeline>(`/api/v1/transformations/pipelines/${pipelineId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async deletePipeline(workspaceId: string, pipelineId: string): Promise<void> {
    return apiClient<void>(`/api/v1/transformations/pipelines/${pipelineId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async addStep(
    workspaceId: string,
    pipelineId: string,
    data: {
      step_order?: number;
      operation_type: TransformationOpType;
      configuration?: Record<string, any>;
      input_references?: Record<string, any>;
      output_schema?: Array<{ name: string; data_type: string }>;
    }
  ): Promise<TransformationStep> {
    return apiClient<TransformationStep>(`/api/v1/transformations/pipelines/${pipelineId}/steps`, {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async updateStep(
    workspaceId: string,
    pipelineId: string,
    stepId: string,
    data: {
      step_order?: number;
      operation_type?: TransformationOpType;
      configuration?: Record<string, any>;
      input_references?: Record<string, any>;
      output_schema?: Array<{ name: string; data_type: string }>;
    }
  ): Promise<TransformationStep> {
    return apiClient<TransformationStep>(
      `/api/v1/transformations/pipelines/${pipelineId}/steps/${stepId}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
        workspaceId,
      }
    );
  },

  async deleteStep(workspaceId: string, pipelineId: string, stepId: string): Promise<void> {
    return apiClient<void>(`/api/v1/transformations/pipelines/${pipelineId}/steps/${stepId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async reorderSteps(
    workspaceId: string,
    pipelineId: string,
    stepIds: string[]
  ): Promise<TransformationStep[]> {
    return apiClient<TransformationStep[]>(
      `/api/v1/transformations/pipelines/${pipelineId}/reorder`,
      {
        method: 'POST',
        body: JSON.stringify({ step_ids: stepIds }),
        workspaceId,
      }
    );
  },

  async previewPipeline(
    workspaceId: string,
    pipelineId: string,
    options: {
      step_index?: number;
      limit?: number;
    } = {}
  ): Promise<PreviewResponse> {
    return apiClient<PreviewResponse>(`/api/v1/transformations/pipelines/${pipelineId}/preview`, {
      method: 'POST',
      body: JSON.stringify(options),
      workspaceId,
    });
  },

  async runPipeline(
    workspaceId: string,
    pipelineId: string,
    data: {
      output_dataset_name?: string;
      output_dataset_description?: string;
    } = {}
  ): Promise<TransformationRun> {
    return apiClient<TransformationRun>(`/api/v1/transformations/pipelines/${pipelineId}/run`, {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },

  async validateFormula(
    workspaceId: string,
    data: {
      expression: string;
      columns: Array<{ name: string; data_type?: string }>;
    }
  ): Promise<ValidateFormulaResponse> {
    return apiClient<ValidateFormulaResponse>('/api/v1/transformations/validate-formula', {
      method: 'POST',
      body: JSON.stringify(data),
      workspaceId,
    });
  },
};

