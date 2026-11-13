/**
 * API client service for DataLens Phase 5D: Automated Data Refresh, Pipeline Orchestration & Background Jobs
 */

import { apiClient } from './apiClient';

export interface BackgroundJob {
  id: string;
  workspace_id: string;
  job_type: string;
  status: 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED';
  priority: number;
  payload: Record<string, any>;
  idempotency_key?: string | null;
  scheduled_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  progress_pct: number;
  progress_message?: string | null;
  retry_count: number;
  max_retries: number;
  retry_delay_seconds: number;
  error_classification?: string | null;
  error_details?: string | null;
  worker_id?: string | null;
  heartbeat_at?: string | null;
  timeout_seconds: number;
  source_dataset_version_ids: string[];
  output_dataset_version_ids: string[];
  created_by?: string | null;
  schedule_id?: string | null;
  workflow_execution_id?: string | null;
  created_at: string;
  updated_at: string;
  executions: JobExecution[];
}

export interface JobExecution {
  id: string;
  job_id: string;
  attempt_number: number;
  status: string;
  worker_id: string;
  started_at: string;
  finished_at?: string | null;
  duration_ms: number;
  error_classification?: string | null;
  error_details?: string | null;
  logs: Array<{ timestamp: string; level: string; message: string }>;
  metrics: Record<string, any>;
  created_at: string;
}

export interface JobSchedule {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  job_type: string;
  target_resource_id?: string | null;
  target_resource_type: string;
  payload: Record<string, any>;
  frequency: string;
  cron_expression?: string | null;
  timezone: string;
  hour: number;
  minute: number;
  day_of_week?: number | null;
  day_of_month?: number | null;
  is_active: boolean;
  last_run_at?: string | null;
  last_run_status?: string | null;
  next_run_at?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowStep {
  id: string;
  workflow_id: string;
  step_name: string;
  step_order: number;
  step_type: string;
  target_resource_id?: string | null;
  configuration: Record<string, any>;
  depends_on_step_ids: string[];
  timeout_seconds: number;
  max_retries: number;
  created_at: string;
}

export interface Workflow {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  failure_policy: string;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  steps: WorkflowStep[];
}

export interface WorkflowStepExecution {
  id: string;
  workflow_execution_id: string;
  step_id: string;
  status: string;
  job_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms: number;
  error_details?: string | null;
  input_version_ids: string[];
  output_version_ids: string[];
  metrics: Record<string, any>;
  step_name?: string | null;
  step_type?: string | null;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  workspace_id: string;
  triggered_by?: string | null;
  trigger_type: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms: number;
  error_details?: string | null;
  created_at: string;
  updated_at: string;
  step_executions: WorkflowStepExecution[];
}

export interface AutomationOverview {
  active_schedules_count: number;
  running_jobs_count: number;
  queued_jobs_count: number;
  failed_jobs_count: number;
  successful_jobs_count: number;
  active_workflows_count: number;
  recent_jobs: BackgroundJob[];
  recent_workflows: WorkflowExecution[];
}

export const automationService = {
  // Overview
  async getOverview(workspaceId: string): Promise<AutomationOverview> {
    return apiClient<AutomationOverview>(`/api/v1/automation/overview?workspace_id=${workspaceId}`);
  },

  // Jobs
  async listJobs(
    workspaceId: string,
    params?: { status?: string; job_type?: string; limit?: number; offset?: number }
  ): Promise<{ jobs: BackgroundJob[]; total: number }> {
    const searchParams = new URLSearchParams({ workspace_id: workspaceId });
    if (params?.status) searchParams.append('status', params.status);
    if (params?.job_type) searchParams.append('job_type', params.job_type);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));

    return apiClient<{ jobs: BackgroundJob[]; total: number }>(`/api/v1/automation/jobs?${searchParams}`);
  },

  async getJob(jobId: string): Promise<BackgroundJob> {
    return apiClient<BackgroundJob>(`/api/v1/automation/jobs/${jobId}`);
  },

  async createJob(workspaceId: string, payload: {
    job_type: string;
    priority?: number;
    payload?: Record<string, any>;
    idempotency_key?: string;
    max_retries?: number;
  }): Promise<BackgroundJob> {
    return apiClient<BackgroundJob>(`/api/v1/automation/jobs?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async cancelJob(jobId: string, reason?: string): Promise<BackgroundJob> {
    return apiClient<BackgroundJob>(
      `/api/v1/automation/jobs/${jobId}/cancel${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`,
      { method: 'POST' }
    );
  },

  async retryJob(jobId: string): Promise<BackgroundJob> {
    return apiClient<BackgroundJob>(`/api/v1/automation/jobs/${jobId}/retry`, {
      method: 'POST',
    });
  },

  // Schedules
  async listSchedules(workspaceId: string, isActive?: boolean): Promise<{ schedules: JobSchedule[]; total: number }> {
    let url = `/api/v1/automation/schedules?workspace_id=${workspaceId}`;
    if (isActive !== undefined) url += `&is_active=${isActive}`;
    return apiClient<{ schedules: JobSchedule[]; total: number }>(url);
  },

  async createSchedule(workspaceId: string, schedule: {
    name: string;
    description?: string;
    job_type: string;
    target_resource_id?: string;
    target_resource_type?: string;
    payload?: Record<string, any>;
    frequency: string;
    cron_expression?: string;
    timezone?: string;
    hour?: number;
    minute?: number;
    day_of_week?: number;
    day_of_month?: number;
  }): Promise<JobSchedule> {
    return apiClient<JobSchedule>(`/api/v1/automation/schedules?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(schedule),
    });
  },

  async updateSchedule(scheduleId: string, updates: Partial<JobSchedule>): Promise<JobSchedule> {
    return apiClient<JobSchedule>(`/api/v1/automation/schedules/${scheduleId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  async pauseSchedule(scheduleId: string): Promise<JobSchedule> {
    return apiClient<JobSchedule>(`/api/v1/automation/schedules/${scheduleId}/pause`, {
      method: 'POST',
    });
  },

  async resumeSchedule(scheduleId: string): Promise<JobSchedule> {
    return apiClient<JobSchedule>(`/api/v1/automation/schedules/${scheduleId}/resume`, {
      method: 'POST',
    });
  },

  async deleteSchedule(scheduleId: string): Promise<void> {
    await apiClient(`/api/v1/automation/schedules/${scheduleId}`, {
      method: 'DELETE',
    });
  },

  // Workflows
  async listWorkflows(workspaceId: string): Promise<{ workflows: Workflow[]; total: number }> {
    return apiClient<{ workflows: Workflow[]; total: number }>(
      `/api/v1/automation/workflows?workspace_id=${workspaceId}`
    );
  },

  async getWorkflow(workflowId: string): Promise<Workflow> {
    return apiClient<Workflow>(`/api/v1/automation/workflows/${workflowId}`);
  },

  async createWorkflow(workspaceId: string, workflow: {
    name: string;
    description?: string;
    failure_policy?: string;
    steps: Array<{
      step_name: string;
      step_order?: number;
      step_type: string;
      target_resource_id?: string;
      configuration?: Record<string, any>;
      depends_on_step_ids?: string[];
    }>;
  }): Promise<Workflow> {
    return apiClient<Workflow>(`/api/v1/automation/workflows?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify(workflow),
    });
  },

  async validateWorkflow(workflowId: string): Promise<{ is_valid: boolean; errors: string[]; topological_order: string[] }> {
    return apiClient<{ is_valid: boolean; errors: string[]; topological_order: string[] }>(
      `/api/v1/automation/workflows/${workflowId}/validate`,
      { method: 'POST' }
    );
  },

  async triggerWorkflow(workflowId: string): Promise<BackgroundJob> {
    return apiClient<BackgroundJob>(`/api/v1/automation/workflows/${workflowId}/trigger`, {
      method: 'POST',
    });
  },

  async listWorkflowExecutions(workflowId: string): Promise<{ executions: WorkflowExecution[]; total: number }> {
    return apiClient<{ executions: WorkflowExecution[]; total: number }>(
      `/api/v1/automation/workflows/${workflowId}/executions`
    );
  },

  async getExecution(executionId: string): Promise<WorkflowExecution> {
    return apiClient<WorkflowExecution>(`/api/v1/automation/executions/${executionId}`);
  },
};
