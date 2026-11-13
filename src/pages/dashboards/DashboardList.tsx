import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Plus,
  Search,
  Copy,
  Trash2,
  Calendar,
  Grid,
  Filter,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { dashboardService, Dashboard } from '../../services/dashboardService';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';

export const DashboardList: React.FC = () => {
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // New Dashboard Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>('');
  const [newDesc, setNewDesc] = useState<string>('');
  const [creating, setCreating] = useState<boolean>(false);

  const fetchDashboards = useCallback(async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await dashboardService.listDashboards(workspaceId, search);
      setDashboards(res.items || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboards.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, search]);

  useEffect(() => {
    fetchDashboards();
  }, [fetchDashboards]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !workspaceId) return;

    try {
      setCreating(true);
      const created = await dashboardService.createDashboard(workspaceId, {
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
      });
      setIsCreateModalOpen(false);
      setNewTitle('');
      setNewDesc('');
      navigate(`/dashboards/${created.id}`);
    } catch (err: any) {
      setError(err?.message || 'Failed to create dashboard.');
    } finally {
      setCreating(false);
    }
  };

  const handleDuplicate = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!workspaceId) return;
    try {
      await dashboardService.duplicateDashboard(workspaceId, id);
      fetchDashboards();
    } catch (err: any) {
      setError(err?.message || 'Failed to duplicate dashboard.');
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!workspaceId || !window.confirm('Archive this dashboard?')) return;
    try {
      await dashboardService.deleteDashboard(workspaceId, id);
      fetchDashboards();
    } catch (err: any) {
      setError(err?.message || 'Failed to archive dashboard.');
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-150">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold text-[#009F98] bg-[#EDF7FA] px-2.5 py-0.5 rounded-full border border-[#BBDCE8] uppercase tracking-wider">
              Interactive Dashboards
            </span>
            <span className="text-xs text-[#52616C]">
              {dashboards.length} {dashboards.length === 1 ? 'dashboard' : 'dashboards'}
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-[#102C46] tracking-tight">
            Dashboards
          </h1>
          <p className="text-xs text-[#52616C] mt-0.5">
            Interactive, customizable BI dashboards powered by DuckDB calculations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsCreateModalOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            New Dashboard
          </Button>
        </div>
      </div>

      {/* Search and Filters toolbar */}
      <div className="flex items-center justify-between gap-4 bg-white p-3.5 rounded-xl border border-[#DCE5EB] shadow-2xs">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-[#52616C] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search dashboards by name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs border border-[#DCE5EB] rounded-lg text-[#102C46] placeholder-[#52616C]/60 focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
          />
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-[#FCE9E9] border border-[#F7C9C5] rounded-xl text-xs text-[#A63838] font-medium flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold underline">Dismiss</button>
        </div>
      )}

      {/* Grid of Dashboards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 bg-white rounded-2xl border border-[#DCE5EB] p-5 animate-pulse flex flex-col justify-between">
              <div className="space-y-2">
                <div className="w-1/2 h-5 bg-[#EEF3F6] rounded" />
                <div className="w-3/4 h-3 bg-[#EEF3F6] rounded" />
              </div>
              <div className="w-full h-8 bg-[#EEF3F6] rounded" />
            </div>
          ))}
        </div>
      ) : dashboards.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-[#DCE5EB] p-8">
          <div className="w-14 h-14 bg-[#EDF7FA] rounded-2xl flex items-center justify-center text-[#009F98] mx-auto mb-4">
            <LayoutDashboard className="w-7 h-7" />
          </div>
          <h3 className="text-base font-bold text-[#102C46]">No dashboards created yet</h3>
          <p className="text-xs text-[#52616C] max-w-md mx-auto mt-1 mb-6">
            Build interactive dashboards with KPI metrics, time-series charts, breakdowns, and live data tables.
          </p>
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsCreateModalOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Create Your First Dashboard
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {dashboards.map((dash) => (
            <div
              key={dash.id}
              onClick={() => navigate(`/dashboards/${dash.id}`)}
              className="bg-white rounded-2xl border border-[#DCE5EB] hover:border-[#009F98] p-5 shadow-2xs hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between group relative"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h3 className="text-base font-bold text-[#102C46] group-hover:text-[#009F98] transition-colors truncate leading-snug">
                    {dash.title}
                  </h3>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      type="button"
                      onClick={(e) => handleDuplicate(e, dash.id)}
                      className="p-1 rounded text-[#52616C] hover:text-[#009F98] hover:bg-[#EDF7FA]"
                      title="Duplicate"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, dash.id)}
                      className="p-1 rounded text-[#52616C] hover:text-[#A63838] hover:bg-[#FCE9E9]"
                      title="Archive"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-[#52616C] line-clamp-2 min-h-[32px] mb-4">
                  {dash.description || 'No description provided.'}
                </p>
              </div>

              <div className="pt-4 border-t border-[#DCE5EB]/60 flex items-center justify-between text-xs text-[#52616C]">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 font-medium">
                    <Grid className="w-3.5 h-3.5 text-[#009F98]" />
                    {dash.widget_count || 0} widgets
                  </span>
                  <span className="flex items-center gap-1 font-medium">
                    <Filter className="w-3.5 h-3.5 text-[#52616C]" />
                    {dash.filter_count || 0} filters
                  </span>
                </div>

                <span className="text-[11px] font-semibold text-[#009F98] group-hover:translate-x-1 transition-transform flex items-center gap-1">
                  Open <ArrowRight className="w-3 h-3" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Dashboard Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Dashboard"
        subtitle="Set a dashboard name and description to begin assembling widgets."
        maxWidth="md"
      >
        <form onSubmit={handleCreate} className="space-y-4 pt-2">
          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Dashboard Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Executive Revenue & Sales Pulse"
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[#102C46] mb-1">
              Description (Optional)
            </label>
            <textarea
              rows={3}
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="Brief overview of goals and key metrics..."
              className="w-full px-3 py-2 text-xs border border-[#DCE5EB] rounded-xl text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]/40"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#DCE5EB]">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setIsCreateModalOpen(false)}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={creating}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              Create Dashboard
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

