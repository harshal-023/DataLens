import { describe, expect, it, vi } from 'vitest';
import { automationService } from '../services/automationService';

// Mock apiClient
vi.mock('../services/apiClient', () => ({
  apiClient: vi.fn(async (url: string, options?: any) => {
    if (url.includes('/automation/overview')) {
      return {
        active_schedules_count: 5,
        running_jobs_count: 2,
        queued_jobs_count: 3,
        failed_jobs_count: 1,
        successful_jobs_count: 42,
        active_workflows_count: 4,
        recent_jobs: [
          {
            id: 'job-12345678-aaaa-bbbb-cccc-ddddeeeeffff',
            workspace_id: 'ws-123',
            job_type: 'data_import',
            status: 'SUCCESS',
            priority: 5,
            payload: {},
            scheduled_at: '2026-11-12T10:00:00Z',
            progress_pct: 100,
            retry_count: 0,
            max_retries: 3,
            retry_delay_seconds: 30,
            timeout_seconds: 600,
            source_dataset_version_ids: [],
            output_dataset_version_ids: ['v-1'],
            created_at: '2026-11-12T10:00:00Z',
            updated_at: '2026-11-12T10:05:00Z',
            executions: [],
          },
        ],
        recent_workflows: [],
      };
    }

    if (url.includes('/cancel')) {
      return {
        id: 'job-123',
        status: 'CANCELLED',
        progress_message: 'Cancelled by user request',
      };
    }

    if (url.includes('/automation/jobs') && options?.method === 'POST') {
      const body = options?.body ? JSON.parse(options.body) : {};
      return {
        id: 'new-job-1111',
        workspace_id: 'ws-123',
        job_type: body.job_type,
        status: 'QUEUED',
        priority: body.priority || 0,
        payload: body.payload || {},
        scheduled_at: new Date().toISOString(),
        progress_pct: 0,
        retry_count: 0,
        max_retries: body.max_retries || 3,
        retry_delay_seconds: 30,
        timeout_seconds: 600,
        source_dataset_version_ids: [],
        output_dataset_version_ids: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        executions: [],
      };
    }

    if (url.includes('/automation/schedules') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      return {
        id: 'sched-2222',
        workspace_id: 'ws-123',
        name: body.name,
        job_type: body.job_type,
        target_resource_type: body.target_resource_type || 'connection',
        payload: body.payload || {},
        frequency: body.frequency,
        timezone: body.timezone || 'UTC',
        hour: body.hour || 8,
        minute: body.minute || 0,
        is_active: true,
        next_run_at: '2026-11-13T08:00:00Z',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    if (url.includes('/automation/workflows') && url.includes('/validate')) {
      return {
        is_valid: true,
        errors: [],
        topological_order: ['step-1', 'step-2', 'step-3'],
      };
    }

    return { success: true };
  }),
}));

describe('Phase 5D Automation Service & Orchestration Client', () => {
  it('retrieves workspace automation overview telemetry', async () => {
    const overview = await automationService.getOverview('ws-123');
    expect(overview.active_schedules_count).toBe(5);
    expect(overview.running_jobs_count).toBe(2);
    expect(overview.successful_jobs_count).toBe(42);
    expect(overview.recent_jobs.length).toBe(1);
    expect(overview.recent_jobs[0].job_type).toBe('data_import');
  });

  it('enqueues a background job with retry and priority parameters', async () => {
    const job = await automationService.createJob('ws-123', {
      job_type: 'pipeline_execution',
      priority: 8,
      payload: { pipeline_id: 'pipe-999' },
      max_retries: 3,
    });
    expect(job.job_type).toBe('pipeline_execution');
    expect(job.status).toBe('QUEUED');
    expect(job.priority).toBe(8);
  });

  it('creates an automated timezone-aware schedule', async () => {
    const sched = await automationService.createSchedule('ws-123', {
      name: 'Daily Customer Sync',
      job_type: 'data_import',
      frequency: 'daily',
      timezone: 'America/New_York',
      hour: 9,
      minute: 30,
    });
    expect(sched.name).toBe('Daily Customer Sync');
    expect(sched.frequency).toBe('daily');
    expect(sched.is_active).toBe(true);
    expect(sched.next_run_at).toBeDefined();
  });

  it('validates workflow DAG dependencies without cycles', async () => {
    const res = await automationService.validateWorkflow('wf-100');
    expect(res.is_valid).toBe(true);
    expect(res.errors.length).toBe(0);
    expect(res.topological_order).toEqual(['step-1', 'step-2', 'step-3']);
  });

  it('cancels an active background job', async () => {
    const res = await automationService.cancelJob('job-123', 'Testing user cancel');
    expect(res.status).toBe('CANCELLED');
    expect(res.progress_message).toBe('Cancelled by user request');
  });
});
