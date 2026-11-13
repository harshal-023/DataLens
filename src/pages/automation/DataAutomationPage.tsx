import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Calendar,
  CheckCircle2,
  Clock,
  Database,
  Filter,
  GitBranch,
  Layers,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCw,
  Search,
  ShieldCheck,
  Trash2,
  XCircle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  automationService,
  AutomationOverview,
  BackgroundJob,
  JobSchedule,
  Workflow,
  WorkflowExecution,
} from '../../services/automationService';

type TabKey = 'overview' | 'schedules' | 'workflows' | 'jobs' | 'executions' | 'quality' | 'history';

export const DataAutomationPage: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id;

  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [overview, setOverview] = useState<AutomationOverview | null>(null);
  const [schedules, setSchedules] = useState<JobSchedule[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<BackgroundJob | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<WorkflowExecution | null>(null);

  // Filter states
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('');
  const [jobSearch, setJobSearch] = useState<string>('');

  // Schedule Modal
  const [showScheduleModal, setShowScheduleModal] = useState<boolean>(false);
  const [scheduleName, setScheduleName] = useState('');
  const [scheduleType, setScheduleType] = useState('data_import');
  const [scheduleFreq, setScheduleFreq] = useState('daily');
  const [scheduleCron, setScheduleCron] = useState('');
  const [scheduleTimezone, setScheduleTimezone] = useState('UTC');
  const [scheduleHour, setScheduleHour] = useState(8);
  const [scheduleMinute, setScheduleMinute] = useState(0);

  // Workflow Modal
  const [showWorkflowModal, setShowWorkflowModal] = useState<boolean>(false);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDesc, setWorkflowDesc] = useState('');
  const [workflowPolicy, setWorkflowPolicy] = useState('STOP_IMMEDIATELY');
  const [workflowSteps, setWorkflowSteps] = useState<Array<{
    step_name: string;
    step_type: string;
    target_resource_id?: string;
  }>>([
    { step_name: 'Source Ingestion', step_type: 'SOURCE_REFRESH' },
    { step_name: 'Data Quality Check', step_type: 'DATA_VALIDATION' },
    { step_name: 'Transform & Clean', step_type: 'TRANSFORMATION' },
  ]);

  // Load Overview & Active Tab Data
  const loadData = async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const ov = await automationService.getOverview(workspaceId);
      setOverview(ov);

      if (activeTab === 'schedules') {
        const schedRes = await automationService.listSchedules(workspaceId);
        setSchedules(schedRes.schedules);
      } else if (activeTab === 'workflows') {
        const wfRes = await automationService.listWorkflows(workspaceId);
        setWorkflows(wfRes.workflows);
      } else if (activeTab === 'jobs' || activeTab === 'history') {
        const jobRes = await automationService.listJobs(workspaceId, {
          status: jobStatusFilter || undefined,
          limit: 50,
        });
        setJobs(jobRes.jobs);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load automation data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [workspaceId, activeTab, jobStatusFilter]);

  // Actions: Jobs
  const handleCancelJob = async (jobId: string) => {
    try {
      await automationService.cancelJob(jobId, 'Manual cancellation from dashboard');
      await loadData();
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    }
  };

  const handleRetryJob = async (jobId: string) => {
    try {
      await automationService.retryJob(jobId);
      await loadData();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    }
  };

  // Actions: Schedules
  const handleToggleSchedule = async (sched: JobSchedule) => {
    try {
      if (sched.is_active) {
        await automationService.pauseSchedule(sched.id);
      } else {
        await automationService.resumeSchedule(sched.id);
      }
      await loadData();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await automationService.deleteSchedule(scheduleId);
      await loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await automationService.createSchedule(workspaceId, {
        name: scheduleName,
        job_type: scheduleType,
        frequency: scheduleFreq,
        cron_expression: scheduleFreq === 'cron' ? scheduleCron : undefined,
        timezone: scheduleTimezone,
        hour: scheduleHour,
        minute: scheduleMinute,
      });
      setShowScheduleModal(false);
      setScheduleName('');
      await loadData();
    } catch (err: any) {
      alert(`Failed to create schedule: ${err.message}`);
    }
  };

  // Actions: Workflows
  const handleCreateWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await automationService.createWorkflow(workspaceId, {
        name: workflowName,
        description: workflowDesc,
        failure_policy: workflowPolicy,
        steps: workflowSteps.map((s, idx) => ({
          step_name: s.step_name,
          step_order: idx,
          step_type: s.step_type,
          depends_on_step_ids: [],
        })),
      });
      setShowWorkflowModal(false);
      setWorkflowName('');
      await loadData();
    } catch (err: any) {
      alert(`Failed to create workflow: ${err.message}`);
    }
  };

  const handleTriggerWorkflow = async (workflowId: string) => {
    try {
      await automationService.triggerWorkflow(workflowId);
      alert('Workflow execution queued successfully!');
      setActiveTab('jobs');
    } catch (err: any) {
      alert(`Trigger failed: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-[#102C46] rounded-xl text-white shadow-md">
              <RefreshCw className="w-6 h-6 text-[#39C3B8]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#102C46]">Data Automation & Orchestration</h1>
              <p className="text-sm text-slate-500">
                Scheduled refreshes, DAG pipelines, data quality gates, and background execution
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData()}
            className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition"
          >
            <RotateCw className="w-4 h-4 text-[#009F98]" />
            Refresh
          </button>
          <button
            onClick={() => setShowScheduleModal(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#009F98] hover:bg-[#102C46] rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            New Schedule
          </button>
          <button
            onClick={() => setShowWorkflowModal(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#102C46] hover:bg-slate-800 rounded-lg shadow-sm transition"
          >
            <GitBranch className="w-4 h-4 text-[#39C3B8]" />
            New Workflow
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 mb-6 space-x-2 overflow-x-auto">
        {[
          { key: 'overview', label: 'Overview', icon: Activity },
          { key: 'schedules', label: 'Schedule Manager', icon: Calendar },
          { key: 'workflows', label: 'Workflow Builder', icon: GitBranch },
          { key: 'jobs', label: 'Job Monitor', icon: Clock },
          { key: 'executions', label: 'Execution Details', icon: Layers },
          { key: 'quality', label: 'Data Quality Rules', icon: ShieldCheck },
          { key: 'history', label: 'Automation History', icon: Database },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as TabKey)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? 'border-[#009F98] text-[#009F98]'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {error && (
        <div className="p-4 mb-6 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* 1. OVERVIEW TAB */}
      {activeTab === 'overview' && overview && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
              <div className="flex justify-between items-center text-slate-500 text-sm font-medium mb-1">
                <span>Active Schedules</span>
                <Calendar className="w-4 h-4 text-[#009F98]" />
              </div>
              <div className="text-3xl font-bold text-[#102C46]">{overview.active_schedules_count}</div>
              <div className="text-xs text-slate-400 mt-1">Automated recurring syncs</div>
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
              <div className="flex justify-between items-center text-slate-500 text-sm font-medium mb-1">
                <span>Running Jobs</span>
                <RefreshCw className="w-4 h-4 text-amber-500 animate-spin" />
              </div>
              <div className="text-3xl font-bold text-amber-600">{overview.running_jobs_count}</div>
              <div className="text-xs text-slate-400 mt-1">Currently processing in background</div>
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
              <div className="flex justify-between items-center text-slate-500 text-sm font-medium mb-1">
                <span>Successful Jobs</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-3xl font-bold text-emerald-600">{overview.successful_jobs_count}</div>
              <div className="text-xs text-slate-400 mt-1">Completed without errors</div>
            </div>

            <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
              <div className="flex justify-between items-center text-slate-500 text-sm font-medium mb-1">
                <span>Failed Jobs</span>
                <XCircle className="w-4 h-4 text-red-500" />
              </div>
              <div className="text-3xl font-bold text-red-600">{overview.failed_jobs_count}</div>
              <div className="text-xs text-slate-400 mt-1">Requires inspection or retry</div>
            </div>
          </div>

          {/* Recent Jobs Table */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-base font-semibold text-[#102C46]">Recent Background Executions</h2>
              <button
                onClick={() => setActiveTab('jobs')}
                className="text-xs font-semibold text-[#009F98] hover:underline"
              >
                View all jobs →
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-400 border-b border-slate-100">
                  <tr>
                    <th className="py-3 px-4">Job ID</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Progress</th>
                    <th className="py-3 px-4">Scheduled At</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {overview.recent_jobs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        No background jobs recorded yet.
                      </td>
                    </tr>
                  ) : (
                    overview.recent_jobs.map((j) => (
                      <tr key={j.id} className="hover:bg-slate-50/60">
                        <td className="py-3 px-4 font-mono text-xs text-slate-500">{j.id.slice(0, 8)}...</td>
                        <td className="py-3 px-4 font-medium text-[#102C46] capitalize">
                          {j.job_type.replace('_', ' ')}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                              j.status === 'SUCCESS'
                                ? 'bg-emerald-50 text-emerald-700'
                                : j.status === 'RUNNING'
                                ? 'bg-amber-50 text-amber-700 animate-pulse'
                                : j.status === 'FAILED'
                                ? 'bg-red-50 text-red-700'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {j.status}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="w-32 bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-[#009F98] h-2 transition-all duration-300"
                              style={{ width: `${j.progress_pct}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400">{j.progress_pct}%</span>
                        </td>
                        <td className="py-3 px-4 text-xs text-slate-500">
                          {new Date(j.scheduled_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          {j.status === 'RUNNING' && (
                            <button
                              onClick={() => handleCancelJob(j.id)}
                              className="text-xs text-red-600 hover:underline"
                            >
                              Cancel
                            </button>
                          )}
                          {(j.status === 'FAILED' || j.status === 'CANCELLED') && (
                            <button
                              onClick={() => handleRetryJob(j.id)}
                              className="text-xs text-[#009F98] hover:underline"
                            >
                              Retry
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. SCHEDULE MANAGER TAB */}
      {activeTab === 'schedules' && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-[#102C46]">Automated Schedules</h2>
              <p className="text-sm text-slate-500">
                Configure timezone-aware recurring external syncs and pipeline runs
              </p>
            </div>
            <button
              onClick={() => setShowScheduleModal(true)}
              className="px-3.5 py-1.5 text-sm font-medium text-white bg-[#009F98] hover:bg-[#102C46] rounded-lg shadow-sm"
            >
              + Create Schedule
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-400 border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">Target Type</th>
                  <th className="py-3 px-4">Frequency</th>
                  <th className="py-3 px-4">Timezone</th>
                  <th className="py-3 px-4">Next Execution</th>
                  <th className="py-3 px-4">Active</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {schedules.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No schedules created yet. Click "+ Create Schedule" to configure one.
                    </td>
                  </tr>
                ) : (
                  schedules.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-semibold text-[#102C46]">{s.name}</td>
                      <td className="py-3 px-4 capitalize">{s.job_type.replace('_', ' ')}</td>
                      <td className="py-3 px-4 uppercase text-xs font-semibold text-slate-500">
                        {s.frequency}
                        {s.cron_expression && ` (${s.cron_expression})`}
                      </td>
                      <td className="py-3 px-4 text-xs font-mono text-slate-500">{s.timezone}</td>
                      <td className="py-3 px-4 text-xs text-slate-600">
                        {s.next_run_at ? new Date(s.next_run_at).toLocaleString() : '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            s.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {s.is_active ? 'Active' : 'Paused'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => handleToggleSchedule(s)}
                          className="text-xs font-medium text-slate-600 hover:text-[#009F98]"
                        >
                          {s.is_active ? 'Pause' : 'Resume'}
                        </button>
                        <button
                          onClick={() => handleDeleteSchedule(s.id)}
                          className="text-xs font-medium text-red-600 hover:underline"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. WORKFLOW BUILDER TAB */}
      {activeTab === 'workflows' && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-[#102C46]">Orchestration Workflows (DAGs)</h2>
              <p className="text-sm text-slate-500">
                End-to-end multi-step pipelines: source refresh → validation → transform → report
              </p>
            </div>
            <button
              onClick={() => setShowWorkflowModal(true)}
              className="px-3.5 py-1.5 text-sm font-medium text-white bg-[#102C46] hover:bg-slate-800 rounded-lg shadow-sm"
            >
              + Create Workflow
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workflows.length === 0 ? (
              <div className="col-span-2 py-12 text-center text-slate-400">
                No workflows configured yet. Click "+ Create Workflow" to chain data pipelines.
              </div>
            ) : (
              workflows.map((wf) => (
                <div key={wf.id} className="p-5 border border-slate-200 rounded-xl hover:shadow-md transition">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="text-base font-bold text-[#102C46]">{wf.name}</h3>
                      <p className="text-xs text-slate-500">{wf.description || 'No description provided'}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 bg-slate-100 rounded text-slate-600 font-mono">
                      {wf.failure_policy}
                    </span>
                  </div>

                  <div className="my-4 space-y-2">
                    <div className="text-xs font-semibold uppercase text-slate-400">Steps ({wf.steps?.length || 0}):</div>
                    <div className="flex flex-wrap gap-2">
                      {wf.steps?.map((step, idx) => (
                        <div
                          key={step.id || idx}
                          className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 border border-slate-200 rounded-md text-xs font-medium text-slate-700"
                        >
                          <span className="w-4 h-4 rounded-full bg-[#009F98] text-white flex items-center justify-center text-[10px]">
                            {idx + 1}
                          </span>
                          <span>{step.step_name}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                    <button
                      onClick={() => handleTriggerWorkflow(wf.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#009F98] hover:bg-[#102C46] rounded-md shadow-sm transition"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Trigger Run
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* 4. JOB MONITOR TAB */}
      {(activeTab === 'jobs' || activeTab === 'history') && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h2 className="text-lg font-bold text-[#102C46]">
                {activeTab === 'jobs' ? 'Background Job Monitor' : 'Automation Execution History'}
              </h2>
              <p className="text-sm text-slate-500">
                Inspect atomic claiming, worker execution, heartbeats, and retry status
              </p>
            </div>

            <div className="flex items-center gap-3">
              <select
                value={jobStatusFilter}
                onChange={(e) => setJobStatusFilter(e.target.value)}
                className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg text-slate-600 focus:outline-none"
              >
                <option value="">All Statuses</option>
                <option value="QUEUED">Queued</option>
                <option value="RUNNING">Running</option>
                <option value="SUCCESS">Success</option>
                <option value="FAILED">Failed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-400 border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">Job ID</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Worker ID</th>
                  <th className="py-3 px-4">Retries</th>
                  <th className="py-3 px-4">Scheduled / Started</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No background jobs match the current filter.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => setSelectedJob(job)}
                      className="hover:bg-slate-50/80 cursor-pointer"
                    >
                      <td className="py-3 px-4 font-mono text-xs text-slate-500">{job.id.slice(0, 8)}...</td>
                      <td className="py-3 px-4 font-semibold text-[#102C46] capitalize">
                        {job.job_type.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                            job.status === 'SUCCESS'
                              ? 'bg-emerald-50 text-emerald-700'
                              : job.status === 'RUNNING'
                              ? 'bg-amber-50 text-amber-700 animate-pulse'
                              : job.status === 'FAILED'
                              ? 'bg-red-50 text-red-700'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-xs font-mono text-slate-500">{job.worker_id || 'unassigned'}</td>
                      <td className="py-3 px-4 text-xs">
                        {job.retry_count} / {job.max_retries}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-500">
                        {new Date(job.scheduled_at).toLocaleTimeString()}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        {job.status === 'RUNNING' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCancelJob(job.id);
                            }}
                            className="text-xs text-red-600 hover:underline"
                          >
                            Cancel
                          </button>
                        )}
                        {(job.status === 'FAILED' || job.status === 'CANCELLED') && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRetryJob(job.id);
                            }}
                            className="text-xs text-[#009F98] hover:underline"
                          >
                            Retry
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Job Detail Modal / Panel */}
          {selectedJob && (
            <div className="p-6 bg-slate-50 border border-slate-200 rounded-xl mt-6 space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-base font-bold text-[#102C46]">Job Execution Trace: {selectedJob.id}</h3>
                  <p className="text-xs text-slate-500">
                    Type: {selectedJob.job_type} | Worker: {selectedJob.worker_id || 'none'}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-xs text-slate-400 hover:text-slate-600"
                >
                  Close
                </button>
              </div>

              {selectedJob.error_details && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 font-mono">
                  <strong>Error ({selectedJob.error_classification || 'UNKNOWN'}):</strong> {selectedJob.error_details}
                </div>
              )}

              <div>
                <h4 className="text-xs font-semibold uppercase text-slate-400 mb-2">Execution Attempts & Logs:</h4>
                <div className="space-y-2">
                  {selectedJob.executions && selectedJob.executions.length > 0 ? (
                    selectedJob.executions.map((exec) => (
                      <div key={exec.id} className="p-3 bg-white border border-slate-200 rounded-lg text-xs space-y-2">
                        <div className="flex justify-between text-slate-500">
                          <span>Attempt #{exec.attempt_number} ({exec.status})</span>
                          <span>Duration: {exec.duration_ms}ms</span>
                        </div>
                        <div className="bg-slate-900 text-slate-200 p-2.5 rounded font-mono text-[11px] max-h-36 overflow-y-auto">
                          {exec.logs?.map((log, lIdx) => (
                            <div key={lIdx}>
                              [{log.timestamp.slice(11, 19)}] [{log.level}] {log.message}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400">No execution logs available yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5. EXECUTION DETAILS TAB */}
      {activeTab === 'executions' && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
          <h2 className="text-lg font-bold text-[#102C46]">Step-by-Step DAG Execution Details</h2>
          <p className="text-sm text-slate-500">
            View detailed telemetry, input/output version lineage, and task step statuses
          </p>
          <div className="p-8 border border-dashed border-slate-200 rounded-xl text-center text-slate-400">
            Select an active or historical workflow run from the Workflow Builder to inspect step executions.
          </div>
        </div>
      )}

      {/* 6. DATA QUALITY RULES TAB */}
      {activeTab === 'quality' && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-[#102C46]">Data Quality Gateways</h2>
            <p className="text-sm text-slate-500">
              Configure validation thresholds before refreshed datasets are materialized or published
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-5 border border-slate-200 rounded-xl space-y-2">
              <h3 className="font-semibold text-[#102C46]">Null Value Tolerance</h3>
              <p className="text-xs text-slate-500">Threshold: Maximum 20% null values per column</p>
              <div className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded inline-block">
                Policy: BLOCK
              </div>
            </div>

            <div className="p-5 border border-slate-200 rounded-xl space-y-2">
              <h3 className="font-semibold text-[#102C46]">Duplicate Row Rate</h3>
              <p className="text-xs text-slate-500">Threshold: Maximum 10% duplicate row tolerance</p>
              <div className="text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-1 rounded inline-block">
                Policy: WARN
              </div>
            </div>

            <div className="p-5 border border-slate-200 rounded-xl space-y-2">
              <h3 className="font-semibold text-[#102C46]">Schema Drift Check</h3>
              <p className="text-xs text-slate-500">Verifies required columns and data types against schema</p>
              <div className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded inline-block">
                Policy: BLOCK
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Create Schedule */}
      {showScheduleModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-[#102C46]">Create Automated Schedule</h3>
            <form onSubmit={handleCreateSchedule} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Schedule Name</label>
                <input
                  type="text"
                  required
                  value={scheduleName}
                  onChange={(e) => setScheduleName(e.target.value)}
                  placeholder="Daily Production Data Refresh"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Target Task Type</label>
                <select
                  value={scheduleType}
                  onChange={(e) => setScheduleType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none"
                >
                  <option value="data_import">External Data Source Sync</option>
                  <option value="dataset_refresh">Full Dataset Refresh</option>
                  <option value="incremental_refresh">Incremental Data Refresh</option>
                  <option value="pipeline_execution">Transformation Pipeline Execution</option>
                  <option value="report_generation">Scheduled Business Report</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Frequency</label>
                  <select
                    value={scheduleFreq}
                    onChange={(e) => setScheduleFreq(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none"
                  >
                    <option value="hourly">Hourly</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="cron">Custom Cron</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Timezone</label>
                  <input
                    type="text"
                    value={scheduleTimezone}
                    onChange={(e) => setScheduleTimezone(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none"
                  />
                </div>
              </div>

              {scheduleFreq === 'cron' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Cron Expression</label>
                  <input
                    type="text"
                    value={scheduleCron}
                    onChange={(e) => setScheduleCron(e.target.value)}
                    placeholder="0 8 * * 1-5"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none"
                  />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Hour (0-23)</label>
                    <input
                      type="number"
                      min={0}
                      max={23}
                      value={scheduleHour}
                      onChange={(e) => setScheduleHour(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Minute (0-59)</label>
                    <input
                      type="number"
                      min={0}
                      max={59}
                      value={scheduleMinute}
                      onChange={(e) => setScheduleMinute(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none"
                    />
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-semibold text-white bg-[#009F98] hover:bg-[#102C46] rounded-lg shadow-sm"
                >
                  Create Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Create Workflow */}
      {showWorkflowModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-[#102C46]">Build DAG Workflow</h3>
            <form onSubmit={handleCreateWorkflow} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Workflow Name</label>
                <input
                  type="text"
                  required
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  placeholder="End-to-End Analytics Refresh Pipeline"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Failure Policy</label>
                <select
                  value={workflowPolicy}
                  onChange={(e) => setWorkflowPolicy(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none"
                >
                  <option value="STOP_IMMEDIATELY">Stop Immediately on Step Error</option>
                  <option value="RETRY_FAILED_STEP">Retry Failed Step with Backoff</option>
                  <option value="CONTINUE_INDEPENDENT_BRANCHES">Continue Independent Branches</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">Chained Steps (DAG):</label>
                <div className="space-y-2">
                  {workflowSteps.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs">
                      <span className="font-bold text-[#009F98]">{idx + 1}.</span>
                      <input
                        type="text"
                        value={step.step_name}
                        onChange={(e) => {
                          const updated = [...workflowSteps];
                          updated[idx].step_name = e.target.value;
                          setWorkflowSteps(updated);
                        }}
                        className="flex-1 px-2 py-1 bg-white border border-slate-200 rounded"
                      />
                      <span className="text-[10px] px-2 py-0.5 bg-slate-200 rounded font-mono">{step.step_type}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowWorkflowModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-semibold text-white bg-[#102C46] hover:bg-slate-800 rounded-lg shadow-sm"
                >
                  Save Workflow
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

