import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Workflow,
  Plus,
  Search,
  Trash2,
  Calendar,
  Layers,
  ArrowRight,
  Database,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  transformationService,
  TransformationPipelineSummary,
} from '../../services/transformationService';
import { DatasetApi } from '../../services/apiClient';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';

export const DataPreparationList: React.FC = () => {
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [pipelines, setPipelines] = useState<TransformationPipelineSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // New Pipeline Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newName, setNewName] = useState<string>('');
  const [newDesc, setNewDesc] = useState<string>('');
  const [availableDatasets, setAvailableDatasets] = useState<any[]>([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<string[]>([]);
  const [creating, setCreating] = useState<boolean>(false);

  // Delete Confirmation Modal
  const [pipelineToDelete, setPipelineToDelete] = useState<TransformationPipelineSummary | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  const fetchPipelines = useCallback(async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await transformationService.listPipelines(workspaceId);
      setPipelines(res || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load transformation pipelines.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  // Load datasets when modal opens
  useEffect(() => {
    if (!isCreateModalOpen || !workspaceId) return;
    DatasetApi.list(workspaceId, { pageSize: 50 })
      .then((res) => setAvailableDatasets(res.items || []))
      .catch(() => {});
  }, [isCreateModalOpen, workspaceId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !workspaceId) return;

    try {
      setCreating(true);
      const created = await transformationService.createPipeline(workspaceId, {
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        source_dataset_ids: selectedDatasetIds,
      });
      setIsCreateModalOpen(false);
      setNewName('');
      setNewDesc('');
      setSelectedDatasetIds([]);
      navigate(`/data-preparation/${created.id}`);
    } catch (err: any) {
      setError(err?.message || 'Failed to create pipeline.');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!pipelineToDelete || !workspaceId) return;
    try {
      setDeleting(true);
      await transformationService.deletePipeline(workspaceId, pipelineToDelete.id);
      setPipelineToDelete(null);
      fetchPipelines();
    } catch (err: any) {
      setError(err?.message || 'Failed to delete pipeline.');
    } finally {
      setDeleting(false);
    }
  };

  const toggleDatasetSelection = (id: string) => {
    setSelectedDatasetIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const filteredPipelines = pipelines.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200/80 dark:border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-50 dark:bg-teal-950/40 text-[#009F98] border border-teal-200/60 dark:border-teal-800/60 shadow-sm">
              <Workflow className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#102C46] dark:text-slate-100">
                Data Preparation & Transformations
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                Clean, combine, join, and enrich multiple datasets into high-fidelity analytical models
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 bg-[#009F98] hover:bg-[#008c86] text-white shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Pipeline
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search transformation pipelines..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#009F98]/20 focus:border-[#009F98] transition-all"
          />
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/40 text-red-700 dark:text-red-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-xs font-semibold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Pipelines Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-48 rounded-2xl bg-slate-100 dark:bg-slate-900/50 animate-pulse border border-slate-200/60 dark:border-slate-800/60"
            />
          ))}
        </div>
      ) : filteredPipelines.length === 0 ? (
        <div className="text-center py-16 px-4 bg-white dark:bg-slate-900/40 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800">
          <div className="w-12 h-12 rounded-2xl bg-teal-50 dark:bg-teal-950/40 text-[#009F98] flex items-center justify-center mx-auto mb-4">
            <Workflow className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-[#102C46] dark:text-slate-100">
            {search ? 'No pipelines matching your search' : 'No transformation pipelines yet'}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
            {search
              ? 'Try adjusting your search keywords'
              : 'Create an automated data pipeline to join, clean, filter, and compute calculated columns across your datasets.'}
          </p>
          {!search && (
            <Button
              onClick={() => setIsCreateModalOpen(true)}
              className="mt-5 inline-flex items-center gap-2 bg-[#009F98] text-white"
            >
              <Plus className="w-4 h-4" />
              Create Pipeline
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPipelines.map((pipe) => (
            <div
              key={pipe.id}
              onClick={() => navigate(`/data-preparation/${pipe.id}`)}
              className="group relative bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-5 hover:border-[#009F98]/60 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="p-2 rounded-xl bg-teal-50 dark:bg-teal-950/30 text-[#009F98] border border-teal-100 dark:border-teal-900/30">
                    <Workflow className="w-5 h-5" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                        pipe.status === 'active'
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40'
                          : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                      }`}
                    >
                      {pipe.status}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPipelineToDelete(pipe);
                      }}
                      className="p-1.5 text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                      title="Delete pipeline"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <h3 className="font-semibold text-base text-[#102C46] dark:text-slate-100 group-hover:text-[#009F98] transition-colors line-clamp-1">
                  {pipe.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 min-h-[32px]">
                  {pipe.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    {pipe.step_count} {pipe.step_count === 1 ? 'step' : 'steps'}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-slate-400" />
                    {pipe.source_dataset_ids.length} source{pipe.source_dataset_ids.length === 1 ? '' : 's'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  {pipe.last_run_status ? (
                    <span
                      className={`flex items-center gap-1 font-medium ${
                        pipe.last_run_status === 'completed'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {pipe.last_run_status === 'completed' ? (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5" />
                      )}
                      Run {pipe.last_run_status}
                    </span>
                  ) : (
                    <span className="text-slate-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Not run yet
                    </span>
                  )}

                  <span className="text-[#009F98] font-medium inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                    Open <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Pipeline Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Transformation Pipeline"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
              Pipeline Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g., Customer Orders & Churn Prep"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#009F98]/20 focus:border-[#009F98]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
              Description
            </label>
            <textarea
              rows={2}
              placeholder="Describe the transformations applied in this pipeline..."
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#009F98]/20 focus:border-[#009F98]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
              Source Datasets (Select Primary & Join Candidates)
            </label>
            {availableDatasets.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">
                No datasets uploaded yet in this workspace.
              </p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-1.5 border border-slate-200 dark:border-slate-800 rounded-xl p-2 bg-slate-50/50 dark:bg-slate-950/20">
                {availableDatasets.map((ds) => {
                  const isChecked = selectedDatasetIds.includes(ds.id);
                  return (
                    <div
                      key={ds.id}
                      onClick={() => toggleDatasetSelection(ds.id)}
                      className={`flex items-center justify-between p-2 rounded-lg cursor-pointer text-xs transition-colors ${
                        isChecked
                          ? 'bg-teal-50 dark:bg-teal-950/40 text-teal-900 dark:text-teal-200 border border-teal-200/60 dark:border-teal-800/60'
                          : 'hover:bg-slate-100 dark:hover:bg-slate-800/60 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Database className="w-3.5 h-3.5 text-[#009F98]" />
                        <span className="font-medium">{ds.name}</span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {ds.row_count ?? 0} rows
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCreateModalOpen(false)}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-[#009F98] hover:bg-[#008c86] text-white"
              disabled={creating || !newName.trim()}
            >
              {creating ? 'Creating...' : 'Create Pipeline'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!pipelineToDelete}
        onClose={() => setPipelineToDelete(null)}
        title="Delete Transformation Pipeline"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Are you sure you want to delete{' '}
            <strong className="text-[#102C46] dark:text-slate-100">
              "{pipelineToDelete?.name}"
            </strong>
            ? This will remove all configured transformation steps. Derived datasets already
            materialized from this pipeline will not be deleted.
          </p>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPipelineToDelete(null)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700 text-white"
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete Pipeline'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

