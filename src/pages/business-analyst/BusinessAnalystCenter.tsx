import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  ShieldAlert,
  Clock,
  Play,
  Calendar,
  Layers,
  ChevronRight,
  MessageSquare,
  RefreshCw,
  X,
  Plus,
  Trash2,
  Send,
  CheckCircle2,
  Pause,
  ArrowUpRight,
  Filter,
} from 'lucide-react';
import { StorageService } from '../../services/storageService';
import {
  BusinessAnalystService,
  BusinessInsight,
  ExecutiveOverview,
  InsightSchedule,
  InsightRunHistory,
} from '../../services/businessAnalystService';
import { DatasetApi } from '../../services/apiClient';
import { useAuth } from '../../context/AuthContext';
import { Dataset } from '../../types';

export const BusinessAnalystCenter: React.FC = () => {
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const wsId = currentWorkspace?.id || '';

  const [datasets, setDatasets] = useState<Dataset[]>(StorageService.getDatasets());
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'overview' | 'trends' | 'anomalies' | 'risks' | 'opportunities' | 'schedules'>('overview');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived'>('active');

  const [overview, setOverview] = useState<ExecutiveOverview | null>(null);
  const [insights, setInsights] = useState<BusinessInsight[]>([]);
  const [schedules, setSchedules] = useState<InsightSchedule[]>([]);
  const [runHistory, setRunHistory] = useState<InsightRunHistory[]>([]);
  const [selectedInsight, setSelectedInsight] = useState<BusinessInsight | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [runningScheduleId, setRunningScheduleId] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const [newComment, setNewComment] = useState<string>('');
  const [showScheduleModal, setShowScheduleModal] = useState<boolean>(false);
  const [newScheduleName, setNewScheduleName] = useState<string>('Daily Morning Analysis');
  const [newScheduleFreq, setNewScheduleFreq] = useState<'daily' | 'weekly' | 'monthly' | 'on_refresh'>('daily');
  const [newScheduleDatasetId, setNewScheduleDatasetId] = useState<string>('');
  const [newScheduleCron, setNewScheduleCron] = useState<string>('');

  // 1. Load real datasets from workspace
  useEffect(() => {
    if (!wsId) return;
    let isMounted = true;

    DatasetApi.list(wsId, { pageSize: 100 })
      .then((res: any) => {
        if (!isMounted) return;
        const items = res?.items || (Array.isArray(res) ? res : []);
        if (items.length > 0) {
          setDatasets(items);
          setSelectedDatasetId((prev) => (prev && items.some((d: any) => d.id === prev) ? prev : items[0].id));
        } else {
          StorageService.getDatasetsAsync().then((list) => {
            if (!isMounted) return;
            if (list && list.length > 0) {
              setDatasets(list);
              setSelectedDatasetId((prev) => (prev && list.some((d: any) => d.id === prev) ? prev : list[0].id));
            }
          });
        }
      })
      .catch((err) => {
        console.warn('DatasetApi.list fallback to StorageService:', err);
        StorageService.getDatasetsAsync().then((list) => {
          if (!isMounted) return;
          if (list && list.length > 0) {
            setDatasets(list);
            setSelectedDatasetId((prev) => (prev && list.some((d: any) => d.id === prev) ? prev : list[0].id));
          }
        });
      });

    return () => {
      isMounted = false;
    };
  }, [wsId]);

  // 2. Load overview, insights, and schedules
  const loadData = async () => {
    if (!wsId) return;
    setIsLoading(true);
    setErrorBanner(null);
    try {
      const [ovData, insData, schedData, histData] = await Promise.all([
        BusinessAnalystService.getOverview(wsId, selectedDatasetId || undefined).catch((e) => {
          console.warn('Error loading overview:', e);
          return null;
        }),
        BusinessAnalystService.getInsights(wsId, {
          dataset_id: selectedDatasetId || undefined,
          limit: 100,
        }).catch((e) => {
          console.warn('Error loading insights:', e);
          return [];
        }),
        BusinessAnalystService.getSchedules(wsId).catch((e) => {
          console.warn('Error loading schedules:', e);
          return [];
        }),
        BusinessAnalystService.getRunHistory(wsId, selectedDatasetId || undefined, 10).catch(() => []),
      ]);

      setOverview(ovData);
      setInsights(insData || []);
      setSchedules(schedData || []);
      setRunHistory(histData || []);
    } catch (err: any) {
      console.error('Error loading Business Analyst data:', err);
      setErrorBanner(err?.message || 'Failed to load business intelligence findings.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [wsId, selectedDatasetId]);

  // 3. Handle Autonomous Sweep Trigger
  const handleGenerate = async () => {
    if (!selectedDatasetId || isGenerating || !wsId) return;
    setIsGenerating(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const res = await BusinessAnalystService.generateInsights(wsId, {
        dataset_id: selectedDatasetId,
      });
      setSuccessBanner(
        `Autonomous sweep complete: generated ${res.insights_generated_count} verified business insights in ${res.execution_duration_ms}ms.`
      );
      await loadData();
    } catch (err: any) {
      console.error('Insight generation failed:', err);
      setErrorBanner(err?.message || 'Insight generation sweep failed. Ensure dataset has analytical records.');
    } finally {
      setIsGenerating(false);
    }
  };

  // 4. Status Lifecycle Update
  const handleStatusChange = async (insightId: string, newStatus: string) => {
    if (!wsId) return;
    try {
      const updated = await BusinessAnalystService.updateStatus(insightId, wsId, newStatus);
      setInsights((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
      if (selectedInsight?.id === updated.id) {
        setSelectedInsight(updated);
      }
      setSuccessBanner(`Insight status updated to ${newStatus}.`);
    } catch (err: any) {
      console.error('Error updating status:', err);
      setErrorBanner(err?.message || 'Failed to update insight status.');
    }
  };

  // 5. Add Comment
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInsight || !newComment.trim() || !wsId) return;
    try {
      const added = await BusinessAnalystService.addComment(selectedInsight.id, wsId, newComment.trim());
      const updatedComments = [...(selectedInsight.comments || []), added];
      const updatedInsight = { ...selectedInsight, comments: updatedComments };
      setSelectedInsight(updatedInsight);
      setInsights((prev) => prev.map((i) => (i.id === updatedInsight.id ? updatedInsight : i)));
      setNewComment('');
    } catch (err: any) {
      console.error('Error adding comment:', err);
      setErrorBanner(err?.message || 'Failed to submit comment.');
    }
  };

  // 6. Schedule Actions
  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newScheduleName.trim() || !wsId) return;
    try {
      const created = await BusinessAnalystService.createSchedule(wsId, {
        name: newScheduleName.trim(),
        frequency: newScheduleFreq,
        dataset_id: newScheduleDatasetId || selectedDatasetId || undefined,
        cron_expression: newScheduleCron.trim() || undefined,
        timezone: 'UTC',
      });
      setSchedules((prev) => [created, ...prev]);
      setShowScheduleModal(false);
      setNewScheduleName('Daily Morning Analysis');
      setNewScheduleCron('');
      setSuccessBanner(`Schedule "${created.name}" created successfully.`);
    } catch (err: any) {
      console.error('Error creating schedule:', err);
      setErrorBanner(err?.message || 'Failed to create automated schedule.');
    }
  };

  const handleToggleSchedule = async (sched: InsightSchedule) => {
    if (!wsId) return;
    try {
      const updated = await BusinessAnalystService.toggleScheduleActive(sched.id, wsId, !sched.is_active);
      setSchedules((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      setSuccessBanner(`Schedule "${updated.name}" is now ${updated.is_active ? 'Active' : 'Paused'}.`);
    } catch (err: any) {
      console.error('Error toggling schedule:', err);
      setErrorBanner(err?.message || 'Failed to toggle schedule state.');
    }
  };

  const handleRunScheduleNow = async (sched: InsightSchedule) => {
    if (!wsId || runningScheduleId) return;
    setRunningScheduleId(sched.id);
    setErrorBanner(null);
    try {
      const res = await BusinessAnalystService.runScheduleNow(sched.id, wsId);
      setSuccessBanner(`Schedule "${sched.name}" executed: generated ${res.insights_generated} insights.`);
      await loadData();
    } catch (err: any) {
      console.error('Error running schedule:', err);
      setErrorBanner(err?.message || 'Failed to execute scheduled sweep immediately.');
    } finally {
      setRunningScheduleId(null);
    }
  };

  const handleDeleteSchedule = async (schedId: string) => {
    if (!wsId) return;
    try {
      await BusinessAnalystService.deleteSchedule(schedId, wsId);
      setSchedules((prev) => prev.filter((s) => s.id !== schedId));
      setSuccessBanner('Schedule deleted successfully.');
    } catch (err: any) {
      console.error('Error deleting schedule:', err);
      setErrorBanner(err?.message || 'Failed to delete schedule.');
    }
  };

  // Filtered views by category and status
  const filteredInsights = useMemo(() => {
    return insights.filter((i) => {
      if (statusFilter === 'active') {
        return i.status !== 'RESOLVED' && i.status !== 'DISMISSED';
      }
      if (statusFilter === 'archived') {
        return i.status === 'RESOLVED' || i.status === 'DISMISSED';
      }
      return true;
    });
  }, [insights, statusFilter]);

  const trendInsights = useMemo(() => filteredInsights.filter((i) => i.category === 'trend'), [filteredInsights]);
  const anomalyInsights = useMemo(() => filteredInsights.filter((i) => i.category === 'anomaly'), [filteredInsights]);
  const riskInsights = useMemo(() => filteredInsights.filter((i) => i.category === 'risk'), [filteredInsights]);
  const opportunityInsights = useMemo(() => filteredInsights.filter((i) => i.category === 'opportunity'), [filteredInsights]);

  // Navigate to Ask Your Data with preloaded prompt
  const handleOpenInAskYourData = (ins: BusinessInsight) => {
    navigate('/ask', {
      state: {
        datasetId: ins.dataset_id,
        initialPrompt: `Explain the business impact of this ${ins.category} finding: "${ins.title}". ${ins.summary}`,
      },
    });
  };

  const severityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#FDE8E8] text-[#9B1C1C] border border-[#F8B4B4]">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#FEF08A] text-[#854D0E] border border-[#FDE047]">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E0F2FE] text-[#0369A1] border border-[#BAE6FD]">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]">LOW</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#009F98] shadow-2xs">
            <Sparkles className="w-6 h-6 text-[#009F98]" />
          </div>
          <div>
            <h1 className="text-2xl font-serif text-[#102C46] tracking-tight">AI Business Analyst</h1>
            <p className="text-xs text-[#52616C] font-medium">
              Autonomous trend discovery, statistical anomaly detection, risk registers, and opportunity identification.
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
          {/* Dataset Selector */}
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-[#DCE5EB] bg-white text-xs font-semibold text-[#102C46] shadow-2xs focus:outline-none focus:border-[#009F98]"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
            {datasets.length === 0 && <option value="">No datasets available</option>}
          </select>

          {/* Sweep Button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !selectedDatasetId}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-[#007D78] to-[#009F98] text-white text-xs font-bold hover:shadow-md transition-all disabled:opacity-50 cursor-pointer shadow-2xs"
          >
            {isGenerating ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>{isGenerating ? 'Running Sweep...' : 'Run Sweep'}</span>
          </button>
        </div>
      </div>

      {/* Alert Banners */}
      {errorBanner && (
        <div className="p-3 bg-[#FDE8E8] border border-[#F8B4B4] rounded-xl text-xs text-[#9B1C1C] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-[#9B1C1C]" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-[#9B1C1C] hover:opacity-75 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successBanner && (
        <div className="p-3 bg-[#E4F3EC] border border-[#B7E2CE] rounded-xl text-xs text-[#216548] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-[#216548]" />
            <span>{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)} className="text-[#216548] hover:opacity-75 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 2. Executive Metric Cards Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[#52616C]">Total Insights</span>
            <Layers className="w-4 h-4 text-[#009F98]" />
          </div>
          <div className="text-2xl font-bold text-[#102C46] mt-2">
            {filteredInsights.length}
          </div>
          <span className="text-[11px] text-[#52616C] mt-0.5 block">
            {statusFilter === 'active' ? 'Active in current workspace' : 'All lifetime findings'}
          </span>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[#9B1C1C]">Critical Risks</span>
            <ShieldAlert className="w-4 h-4 text-[#9B1C1C]" />
          </div>
          <div className="text-2xl font-bold text-[#9B1C1C] mt-2">
            {riskInsights.filter((r) => r.severity === 'CRITICAL' || r.severity === 'HIGH').length}
          </div>
          <span className="text-[11px] text-[#52616C] mt-0.5 block">Concentration & margin alerts</span>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[#007D78]">Opportunities</span>
            <Lightbulb className="w-4 h-4 text-[#007D78]" />
          </div>
          <div className="text-2xl font-bold text-[#007D78] mt-2">
            {opportunityInsights.length}
          </div>
          <span className="text-[11px] text-[#52616C] mt-0.5 block">Expansion & growth signals</span>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-[#DCE5EB] shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[#D97706]">Anomalies</span>
            <AlertTriangle className="w-4 h-4 text-[#D97706]" />
          </div>
          <div className="text-2xl font-bold text-[#D97706] mt-2">
            {anomalyInsights.length}
          </div>
          <span className="text-[11px] text-[#52616C] mt-0.5 block">Statistical outliers detected</span>
        </div>
      </div>

      {/* 3. Navigation Tabs and Status Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#DCE5EB] pb-px">
        <div className="flex items-center gap-1 text-xs font-bold text-[#52616C] overflow-x-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-t-xl transition-colors cursor-pointer whitespace-nowrap ${
              activeTab === 'overview'
                ? 'text-[#009F98] border-b-2 border-[#009F98] bg-white'
                : 'hover:text-[#102C46]'
            }`}
          >
            Executive Overview
          </button>
          <button
            onClick={() => setActiveTab('trends')}
            className={`px-4 py-2 rounded-t-xl transition-colors cursor-pointer whitespace-nowrap ${
              activeTab === 'trends'
                ? 'text-[#009F98] border-b-2 border-[#009F98] bg-white'
                : 'hover:text-[#102C46]'
            }`}
          >
            Trends ({trendInsights.length})
          </button>
          <button
            onClick={() => setActiveTab('anomalies')}
            className={`px-4 py-2 rounded-t-xl transition-colors cursor-pointer whitespace-nowrap ${
              activeTab === 'anomalies'
                ? 'text-[#009F98] border-b-2 border-[#009F98] bg-white'
                : 'hover:text-[#102C46]'
            }`}
          >
            Anomalies ({anomalyInsights.length})
          </button>
          <button
            onClick={() => setActiveTab('risks')}
            className={`px-4 py-2 rounded-t-xl transition-colors cursor-pointer whitespace-nowrap ${
              activeTab === 'risks'
                ? 'text-[#009F98] border-b-2 border-[#009F98] bg-white'
                : 'hover:text-[#102C46]'
            }`}
          >
            Business Risks ({riskInsights.length})
          </button>
          <button
            onClick={() => setActiveTab('opportunities')}
            className={`px-4 py-2 rounded-t-xl transition-colors cursor-pointer whitespace-nowrap ${
              activeTab === 'opportunities'
                ? 'text-[#009F98] border-b-2 border-[#009F98] bg-white'
                : 'hover:text-[#102C46]'
            }`}
          >
            Opportunities ({opportunityInsights.length})
          </button>
          <button
            onClick={() => setActiveTab('schedules')}
            className={`px-4 py-2 rounded-t-xl transition-colors cursor-pointer whitespace-nowrap ${
              activeTab === 'schedules'
                ? 'text-[#009F98] border-b-2 border-[#009F98] bg-white'
                : 'hover:text-[#102C46]'
            }`}
          >
            Schedules ({schedules.length})
          </button>
        </div>

        {/* Lifecycle Status Filter */}
        <div className="flex items-center gap-1.5 self-end sm:self-auto pb-1 text-xs font-semibold text-[#52616C]">
          <Filter className="w-3.5 h-3.5 text-[#64748B]" />
          <span className="text-[11px] text-[#64748B]">View:</span>
          <div className="inline-flex rounded-lg bg-[#F1F5F9] p-0.5 text-[11px]">
            <button
              onClick={() => setStatusFilter('active')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                statusFilter === 'active' ? 'bg-white text-[#102C46] shadow-2xs font-bold' : 'text-[#64748B] hover:text-[#102C46]'
              }`}
            >
              Active
            </button>
            <button
              onClick={() => setStatusFilter('all')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                statusFilter === 'all' ? 'bg-white text-[#102C46] shadow-2xs font-bold' : 'text-[#64748B] hover:text-[#102C46]'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setStatusFilter('archived')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                statusFilter === 'archived' ? 'bg-white text-[#102C46] shadow-2xs font-bold' : 'text-[#64748B] hover:text-[#102C46]'
              }`}
            >
              Resolved
            </button>
          </div>
        </div>
      </div>

      {/* 4. Tab Contents */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] p-12 flex flex-col items-center justify-center text-center">
          <RefreshCw className="w-6 h-6 text-[#009F98] animate-spin mb-3" />
          <p className="text-xs font-bold text-[#102C46]">Analyzing dataset intelligence...</p>
        </div>
      ) : (
        <>
          {/* TAB A: EXECUTIVE OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Critical Findings Panel */}
                <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-[#102C46] flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-[#9B1C1C]" />
                      <span>Priority Business Risks</span>
                    </h3>
                    <span className="text-[10px] text-[#52616C]">Ranked by severity & risk score</span>
                  </div>

                  <div className="divide-y divide-[#EEF3F6]">
                    {riskInsights.slice(0, 5).map((ins) => (
                      <div
                        key={ins.id}
                        onClick={() => setSelectedInsight(ins)}
                        className="py-3 flex items-start justify-between gap-3 hover:bg-[#F8FAFC] -mx-2 px-2 rounded-xl transition-colors cursor-pointer"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {severityBadge(ins.severity)}
                            <span className="text-xs font-bold text-[#102C46]">{ins.title}</span>
                          </div>
                          <p className="text-[11px] text-[#52616C] line-clamp-2">{ins.summary}</p>
                          <div className="flex items-center gap-2 text-[10px] text-[#64748B]">
                            <span>Metric: <strong>{ins.affected_metric}</strong></span>
                            {ins.affected_segment && <span>• Segment: {ins.affected_segment}</span>}
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[#94A3B8] shrink-0 mt-1" />
                      </div>
                    ))}
                    {riskInsights.length === 0 && (
                      <p className="text-xs text-[#64748B] py-6 text-center">
                        No critical business risks identified in current active view.
                      </p>
                    )}
                  </div>
                </div>

                {/* Opportunities Panel */}
                <div className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-[#102C46] flex items-center gap-2">
                      <Lightbulb className="w-4 h-4 text-[#007D78]" />
                      <span>Expansion & Margin Opportunities</span>
                    </h3>
                    <span className="text-[10px] text-[#52616C]">High-performing products & cohorts</span>
                  </div>

                  <div className="divide-y divide-[#EEF3F6]">
                    {opportunityInsights.slice(0, 5).map((ins) => (
                      <div
                        key={ins.id}
                        onClick={() => setSelectedInsight(ins)}
                        className="py-3 flex items-start justify-between gap-3 hover:bg-[#F8FAFC] -mx-2 px-2 rounded-xl transition-colors cursor-pointer"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E0F5F3] text-[#007D78] border border-[#B2E6E2]">
                              OPPORTUNITY
                            </span>
                            <span className="text-xs font-bold text-[#102C46]">{ins.title}</span>
                          </div>
                          <p className="text-[11px] text-[#52616C] line-clamp-2">{ins.summary}</p>
                          <div className="flex items-center gap-2 text-[10px] text-[#64748B]">
                            <span>Segment: <strong>{ins.affected_segment || 'All'}</strong></span>
                            <span>• Impact Score: {Math.round(ins.score * 100)}%</span>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[#94A3B8] shrink-0 mt-1" />
                      </div>
                    ))}
                    {opportunityInsights.length === 0 && (
                      <p className="text-xs text-[#64748B] py-6 text-center">
                        No active expansion signals recorded yet. Run a sweep to uncover high-margin segments.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Recent Sweeps History Bar */}
              {runHistory.length > 0 && (
                <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-2xs">
                  <h4 className="text-xs font-bold text-[#102C46] mb-3 flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-[#009F98]" />
                    <span>Recent Autonomous Sweeps History</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    {runHistory.slice(0, 4).map((run) => (
                      <div key={run.id} className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#EEF3F6] space-y-1">
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="uppercase font-bold text-[#009F98]">{run.trigger_type}</span>
                          <span className={`px-1.5 py-0.5 rounded font-bold ${
                            run.status === 'completed' ? 'bg-[#E4F3EC] text-[#216548]' : 'bg-[#FDE8E8] text-[#9B1C1C]'
                          }`}>
                            {run.status}
                          </span>
                        </div>
                        <div className="font-bold text-[#102C46]">
                          {run.insights_generated_count} findings ({run.execution_duration_ms}ms)
                        </div>
                        <div className="text-[10px] text-[#64748B]">
                          {new Date(run.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB B: TRENDS */}
          {activeTab === 'trends' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {trendInsights.map((ins) => (
                <div
                  key={ins.id}
                  onClick={() => setSelectedInsight(ins)}
                  className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-2xs hover:border-[#009F98] transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs text-[#009F98] font-bold">
                        <TrendingUp className="w-3.5 h-3.5" />
                        <span>Trend Finding</span>
                      </div>
                      {severityBadge(ins.severity)}
                    </div>
                    <h4 className="text-xs font-bold text-[#102C46]">{ins.title}</h4>
                    <p className="text-[11px] text-[#52616C] leading-relaxed">{ins.summary}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#EEF3F6] flex items-center justify-between text-[11px] text-[#52616C]">
                    <span>Metric: <strong className="text-[#102C46]">{ins.affected_metric}</strong></span>
                    <span className="text-[#009F98] font-semibold flex items-center gap-1">
                      View calculation <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              ))}
              {trendInsights.length === 0 && (
                <div className="col-span-2 bg-white rounded-2xl border border-[#DCE5EB] p-12 text-center text-xs text-[#64748B]">
                  No significant trend inflections detected in this dataset version.
                </div>
              )}
            </div>
          )}

          {/* TAB C: ANOMALIES */}
          {activeTab === 'anomalies' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {anomalyInsights.map((ins) => (
                <div
                  key={ins.id}
                  onClick={() => setSelectedInsight(ins)}
                  className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-2xs hover:border-[#D97706] transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs text-[#D97706] font-bold">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>Statistical Anomaly</span>
                      </div>
                      {severityBadge(ins.severity)}
                    </div>
                    <h4 className="text-xs font-bold text-[#102C46]">{ins.title}</h4>
                    <p className="text-[11px] text-[#52616C] leading-relaxed">{ins.summary}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#EEF3F6] flex items-center justify-between text-[11px] text-[#52616C]">
                    <span>Point: <strong className="text-[#102C46]">{ins.affected_segment || 'Observation'}</strong></span>
                    <span className="text-[#009F98] font-semibold flex items-center gap-1">
                      Inspect baseline <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              ))}
              {anomalyInsights.length === 0 && (
                <div className="col-span-2 bg-white rounded-2xl border border-[#DCE5EB] p-12 text-center text-xs text-[#64748B]">
                  No statistical anomalies discovered exceeding sensitivity thresholds.
                </div>
              )}
            </div>
          )}

          {/* TAB D: RISKS */}
          {activeTab === 'risks' && (
            <div className="bg-white rounded-2xl border border-[#DCE5EB] shadow-2xs overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAFC] border-b border-[#DCE5EB] text-[#52616C] uppercase text-[10px] font-bold">
                  <tr>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3">Risk Title & Summary</th>
                    <th className="px-4 py-3">Affected Metric</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EEF3F6] text-[#102C46]">
                  {riskInsights.map((ins) => (
                    <tr key={ins.id} className="hover:bg-[#F8FAFC]">
                      <td className="px-4 py-3 whitespace-nowrap">{severityBadge(ins.severity)}</td>
                      <td className="px-4 py-3">
                        <div className="font-bold">{ins.title}</div>
                        <div className="text-[11px] text-[#64748B] line-clamp-1">{ins.summary}</div>
                      </td>
                      <td className="px-4 py-3 font-semibold">{ins.affected_metric}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#F1F5F9] text-[#475569]">
                          {ins.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setSelectedInsight(ins)}
                          className="px-2.5 py-1 rounded-lg border border-[#DCE5EB] bg-white text-xs font-semibold hover:border-[#009F98] text-[#009F98] cursor-pointer"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  ))}
                  {riskInsights.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-xs text-[#64748B]">
                        No active business risks recorded in register.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB E: OPPORTUNITIES */}
          {activeTab === 'opportunities' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {opportunityInsights.map((ins) => (
                <div
                  key={ins.id}
                  onClick={() => setSelectedInsight(ins)}
                  className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-2xs hover:border-[#009F98] transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs text-[#007D78] font-bold">
                        <Lightbulb className="w-3.5 h-3.5" />
                        <span>Opportunity Signal</span>
                      </div>
                      <span className="text-[10px] font-bold text-[#007D78] bg-[#E0F5F3] px-2 py-0.5 rounded-full">
                        Score: {Math.round(ins.score * 100)}%
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-[#102C46]">{ins.title}</h4>
                    <p className="text-[11px] text-[#52616C] leading-relaxed">{ins.summary}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#EEF3F6] flex items-center justify-between text-[11px] text-[#52616C]">
                    <span>Segment: <strong className="text-[#102C46]">{ins.affected_segment || 'Growth Segment'}</strong></span>
                    <span className="text-[#009F98] font-semibold flex items-center gap-1">
                      Explore actions <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              ))}
              {opportunityInsights.length === 0 && (
                <div className="col-span-2 bg-white rounded-2xl border border-[#DCE5EB] p-12 text-center text-xs text-[#64748B]">
                  No high-margin or expansion opportunities discovered in active scan.
                </div>
              )}
            </div>
          )}

          {/* TAB F: SCHEDULES */}
          {activeTab === 'schedules' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-[#102C46]">Automated Analysis Schedules</h3>
                  <p className="text-xs text-[#52616C]">Run autonomous background sweeps daily, weekly, monthly, or on data refresh.</p>
                </div>
                <button
                  onClick={() => setShowScheduleModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#009F98] text-white text-xs font-bold shadow-2xs hover:bg-[#007D78] cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Schedule</span>
                </button>
              </div>

              <div className="bg-white rounded-2xl border border-[#DCE5EB] overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#F8FAFC] border-b border-[#DCE5EB] text-[#52616C] uppercase text-[10px] font-bold">
                    <tr>
                      <th className="px-4 py-3">Schedule Name</th>
                      <th className="px-4 py-3">Frequency</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Next Execution</th>
                      <th className="px-4 py-3">Last Run</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EEF3F6] text-[#102C46]">
                    {schedules.map((s) => (
                      <tr key={s.id} className="hover:bg-[#F8FAFC]">
                        <td className="px-4 py-3 font-bold">{s.name}</td>
                        <td className="px-4 py-3 uppercase text-[10px] font-semibold">{s.frequency}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            s.is_active ? 'bg-[#E4F3EC] text-[#216548]' : 'bg-[#F1F5F9] text-[#64748B]'
                          }`}>
                            {s.is_active ? 'Active' : 'Paused'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[#64748B]">
                          {s.next_run_at ? new Date(s.next_run_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'On Event'}
                        </td>
                        <td className="px-4 py-3 text-[#64748B]">
                          {s.last_run_at ? new Date(s.last_run_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'Never'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex items-center gap-1">
                            {/* Run Now Button */}
                            <button
                              onClick={() => handleRunScheduleNow(s)}
                              disabled={runningScheduleId === s.id}
                              className="p-1.5 rounded-lg border border-[#DCE5EB] text-[#009F98] hover:bg-[#EDF7FA] disabled:opacity-50 cursor-pointer"
                              title="Run Sweep Now"
                            >
                              {runningScheduleId === s.id ? (
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Play className="w-3.5 h-3.5 fill-current" />
                              )}
                            </button>

                            {/* Toggle Pause/Resume */}
                            <button
                              onClick={() => handleToggleSchedule(s)}
                              className="p-1.5 rounded-lg border border-[#DCE5EB] text-[#52616C] hover:bg-[#F1F5F9] cursor-pointer"
                              title={s.is_active ? 'Pause Schedule' : 'Resume Schedule'}
                            >
                              {s.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                            </button>

                            {/* Delete Button */}
                            <button
                              onClick={() => handleDeleteSchedule(s.id)}
                              className="p-1.5 rounded-lg border border-[#DCE5EB] text-[#94A3B8] hover:text-[#9B1C1C] hover:bg-[#FDE8E8] cursor-pointer"
                              title="Delete Schedule"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {schedules.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-xs text-[#64748B]">
                          No automated schedules configured. Create one to enable automated insight sweeps.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* 5. Insight Detail Drawer / Modal */}
      {selectedInsight && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-[#DCE5EB] w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-[#DCE5EB] flex items-center justify-between bg-[#F8FAFC]">
              <div className="flex items-center gap-2">
                {severityBadge(selectedInsight.severity)}
                <span className="text-xs font-bold uppercase tracking-wider text-[#009F98]">
                  {selectedInsight.category} Finding
                </span>
              </div>
              <button
                onClick={() => setSelectedInsight(null)}
                className="p-1 rounded-lg text-[#64748B] hover:bg-[#EEF3F6] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Body */}
            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              <div>
                <h3 className="text-base font-bold text-[#102C46]">{selectedInsight.title}</h3>
                <p className="text-[#52616C] mt-1 leading-relaxed">{selectedInsight.summary}</p>
              </div>

              {/* Detailed Grounded Explanation */}
              <div className="bg-[#EDF7FA] p-3.5 rounded-xl border border-[#BBDCE8] space-y-1">
                <span className="font-bold text-[#007D78] block">Executive Analytical Interpretation</span>
                <p className="text-[#102C46] leading-relaxed text-[11px]">
                  {selectedInsight.detailed_explanation}
                </p>
                <div className="flex items-center gap-2 text-[10px] text-[#52616C] pt-1">
                  <span>Engine: <strong>{selectedInsight.ai_provider}</strong></span>
                  <span>•</span>
                  <span>100% Deterministic Evidence Grounding</span>
                </div>
              </div>

              {/* Recommended Action & Investigation */}
              {(selectedInsight.recommended_action || selectedInsight.suggested_investigation) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {selectedInsight.suggested_investigation && (
                    <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] space-y-1">
                      <span className="font-bold text-[#102C46] text-[10px] uppercase block tracking-wider">
                        Suggested Investigation
                      </span>
                      <p className="text-[11px] text-[#52616C] leading-relaxed">
                        {selectedInsight.suggested_investigation}
                      </p>
                    </div>
                  )}
                  {selectedInsight.recommended_action && (
                    <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] space-y-1">
                      <span className="font-bold text-[#007D78] text-[10px] uppercase block tracking-wider">
                        Recommended Action
                      </span>
                      <p className="text-[11px] text-[#52616C] leading-relaxed">
                        {selectedInsight.recommended_action}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Verified Evidence Box */}
              {selectedInsight.evidence_items && selectedInsight.evidence_items.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#102C46] uppercase text-[10px] tracking-wider">
                      Verified Calculated Evidence
                    </span>
                    <span className="text-[10px] text-[#216548] font-bold bg-[#E4F3EC] px-2 py-0.5 rounded-full flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Verified (DuckDB)
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {selectedInsight.evidence_items.map((ev) => (
                      <div key={ev.id} className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#DCE5EB]">
                        <span className="text-[10px] text-[#64748B] uppercase block font-semibold">{ev.metric_name}</span>
                        <div className="flex items-baseline gap-2 mt-1">
                          <span className="text-sm font-bold text-[#102C46]">{ev.observed_value}</span>
                          {ev.deviation_pct !== null && ev.deviation_pct !== undefined && (
                            <span className={`text-[10px] font-bold ${ev.deviation_pct >= 0 ? 'text-[#007D78]' : 'text-[#9B1C1C]'}`}>
                              ({ev.deviation_pct >= 0 ? '+' : ''}{ev.deviation_pct.toFixed(1)}%)
                            </span>
                          )}
                        </div>
                        {ev.baseline_value && (
                          <span className="text-[10px] text-[#64748B] block mt-0.5">Baseline: {ev.baseline_value}</span>
                        )}
                        {ev.calculation_formula && (
                          <span className="text-[9px] text-[#94A3B8] font-mono block mt-1">
                            Formula: {ev.calculation_formula}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Lifecycle Status & Controls */}
              <div className="pt-2 border-t border-[#EEF3F6] flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-[#64748B] block mb-1">
                    Lifecycle Status
                  </span>
                  <select
                    value={selectedInsight.status}
                    onChange={(e) => handleStatusChange(selectedInsight.id, e.target.value)}
                    className="px-2.5 py-1 rounded-lg border border-[#DCE5EB] bg-white text-xs font-semibold text-[#102C46]"
                  >
                    <option value="NEW">NEW</option>
                    <option value="REVIEWED">REVIEWED</option>
                    <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
                    <option value="INVESTIGATING">INVESTIGATING</option>
                    <option value="RESOLVED">RESOLVED</option>
                    <option value="DISMISSED">DISMISSED</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleOpenInAskYourData(selectedInsight)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#009F98] text-[#009F98] hover:bg-[#E0F5F3] font-semibold text-xs cursor-pointer"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Ask Your Data</span>
                  </button>
                </div>
              </div>

              {/* Team Comments Thread */}
              <div className="pt-2 border-t border-[#EEF3F6] space-y-2">
                <span className="font-bold text-[#102C46] block uppercase text-[10px] tracking-wider">
                  Analyst Comments & Notes
                </span>

                <div className="space-y-1.5 max-h-32 overflow-y-auto">
                  {selectedInsight.comments?.map((c) => (
                    <div key={c.id} className="p-2 bg-[#F8FAFC] rounded-lg border border-[#DCE5EB]">
                      <div className="flex items-center justify-between text-[10px] text-[#64748B]">
                        <span className="font-bold text-[#102C46]">{c.author_name || 'Team Member'}</span>
                        <span>{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-[11px] text-[#102C46] mt-0.5">{c.content}</p>
                    </div>
                  ))}
                  {(!selectedInsight.comments || selectedInsight.comments.length === 0) && (
                    <p className="text-[11px] text-[#94A3B8] italic">No comments recorded yet.</p>
                  )}
                </div>

                <form onSubmit={handleAddComment} className="flex gap-2 pt-1">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add investigation note..."
                    className="flex-1 px-3 py-1.5 rounded-xl border border-[#DCE5EB] text-xs focus:outline-none focus:border-[#009F98]"
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 rounded-xl bg-[#009F98] text-white text-xs font-bold hover:bg-[#007D78] cursor-pointer"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6. Schedule Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-[#DCE5EB] w-full max-w-md p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#DCE5EB] pb-2">
              <h3 className="text-sm font-bold text-[#102C46]">New Autonomous Schedule</h3>
              <button onClick={() => setShowScheduleModal(false)} className="text-[#64748B] hover:text-[#102C46] cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSchedule} className="space-y-3 text-xs">
              <div>
                <label className="block text-[#52616C] font-semibold mb-1">Schedule Name</label>
                <input
                  type="text"
                  value={newScheduleName}
                  onChange={(e) => setNewScheduleName(e.target.value)}
                  required
                  placeholder="e.g. Daily Morning Sweep"
                  className="w-full px-3 py-2 rounded-xl border border-[#DCE5EB] text-xs font-medium focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <div>
                <label className="block text-[#52616C] font-semibold mb-1">Target Dataset</label>
                <select
                  value={newScheduleDatasetId || selectedDatasetId}
                  onChange={(e) => setNewScheduleDatasetId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#DCE5EB] text-xs font-semibold focus:outline-none focus:border-[#009F98]"
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[#52616C] font-semibold mb-1">Frequency</label>
                <select
                  value={newScheduleFreq}
                  onChange={(e: any) => setNewScheduleFreq(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#DCE5EB] text-xs font-semibold focus:outline-none focus:border-[#009F98]"
                >
                  <option value="daily">Daily Morning Sweep</option>
                  <option value="weekly">Weekly Executive Scan</option>
                  <option value="monthly">Monthly Audit</option>
                  <option value="on_refresh">On Successful Dataset Refresh</option>
                </select>
              </div>

              <div>
                <label className="block text-[#52616C] font-semibold mb-1">Custom Cron (Optional)</label>
                <input
                  type="text"
                  value={newScheduleCron}
                  onChange={(e) => setNewScheduleCron(e.target.value)}
                  placeholder="e.g. 0 8 * * 1-5"
                  className="w-full px-3 py-2 rounded-xl border border-[#DCE5EB] text-xs font-medium focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="px-3 py-1.5 rounded-xl border border-[#DCE5EB] text-[#52616C] hover:bg-[#F8FAFC] font-semibold text-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#009F98] text-white font-bold text-xs hover:bg-[#007D78] shadow-2xs cursor-pointer"
                >
                  Save Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
