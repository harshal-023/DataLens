import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Workflow,
  Plus,
  Play,
  Save,
  Trash2,
  ChevronUp,
  ChevronDown,
  Layers,
  GitMerge,
  Filter,
  Calculator,
  Eraser,
  CopyCheck,
  Type,
  SpellCheck,
  CheckSquare,
  Database,
  Table as TableIcon,
  Clock,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Search,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  transformationService,
  TransformationPipeline,
  TransformationStep,
  TransformationOpType,
  PreviewResponse,
} from '../../services/transformationService';
import { DatasetApi } from '../../services/apiClient';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';

export const DataPreparationEditor: React.FC = () => {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id || '';

  const [pipeline, setPipeline] = useState<TransformationPipeline | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // Available datasets in workspace
  const [workspaceDatasets, setWorkspaceDatasets] = useState<any[]>([]);
  const [datasetSearch, setDatasetSearch] = useState<string>('');

  // Preview state
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewTab, setPreviewTab] = useState<'table' | 'schema'>('table');
  const [activeStepIndex, setActiveStepIndex] = useState<number | null>(null);

  // Step modal state
  const [isStepModalOpen, setIsStepModalOpen] = useState<boolean>(false);
  const [editingStep, setEditingStep] = useState<TransformationStep | null>(null);
  const [selectedOpType, setSelectedOpType] = useState<TransformationOpType>('clean_nulls');
  const [stepConfig, setStepConfig] = useState<Record<string, any>>({});
  const [savingStep, setSavingStep] = useState<boolean>(false);

  // Formula validation state inside modal
  const [formulaValidating, setFormulaValidating] = useState<boolean>(false);
  const [formulaResult, setFormulaResult] = useState<{ valid: boolean; error?: string; sql?: string } | null>(null);

  // Run pipeline modal state
  const [isRunModalOpen, setIsRunModalOpen] = useState<boolean>(false);
  const [outputDatasetName, setOutputDatasetName] = useState<string>('');
  const [outputDatasetDesc, setOutputDatasetDesc] = useState<string>('');
  const [runningPipeline, setRunningPipeline] = useState<boolean>(false);
  const [runSuccessResult, setRunSuccessResult] = useState<any | null>(null);

  // Load pipeline and workspace datasets
  const fetchPipeline = useCallback(async () => {
    if (!workspaceId || !pipelineId) return;
    try {
      setLoading(true);
      setError(null);
      const pipe = await transformationService.getPipeline(workspaceId, pipelineId);
      setPipeline(pipe);
      setOutputDatasetName(`Transformed - ${pipe.name}`);
    } catch (err: any) {
      setError(err?.message || 'Failed to load pipeline.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, pipelineId]);

  const fetchWorkspaceDatasets = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const res = await DatasetApi.list(workspaceId, { pageSize: 100 });
      setWorkspaceDatasets(res.items || []);
    } catch {
      // Ignored
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchPipeline();
    fetchWorkspaceDatasets();
  }, [fetchPipeline, fetchWorkspaceDatasets]);

  // Trigger preview
  const runPreview = useCallback(
    async (stepIdx?: number) => {
      if (!workspaceId || !pipelineId) return;
      try {
        setPreviewLoading(true);
        setPreviewError(null);
        const targetStep = stepIdx !== undefined ? stepIdx : (pipeline?.steps.length ? pipeline.steps.length - 1 : undefined);
        setActiveStepIndex(targetStep ?? null);
        const res = await transformationService.previewPipeline(workspaceId, pipelineId, {
          step_index: targetStep,
          limit: 25,
        });
        setPreviewData(res);
      } catch (err: any) {
        setPreviewError(err?.message || 'Preview generation failed.');
      } finally {
        setPreviewLoading(false);
      }
    },
    [workspaceId, pipelineId, pipeline]
  );

  // Initial preview when pipeline is loaded
  useEffect(() => {
    if (pipeline && pipeline.source_dataset_ids.length > 0 && !previewData && !previewLoading) {
      runPreview();
    }
  }, [pipeline]);

  // Save Pipeline Metadata
  const handleSavePipeline = async () => {
    if (!pipeline || !workspaceId) return;
    try {
      setSaving(true);
      setError(null);
      await transformationService.updatePipeline(workspaceId, pipeline.id, {
        name: pipeline.name,
        description: pipeline.description || undefined,
        source_dataset_ids: pipeline.source_dataset_ids,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (err: any) {
      setError(err?.message || 'Failed to save pipeline.');
    } finally {
      setSaving(false);
    }
  };

  // Add or Update Step
  const openAddStepModal = (op: TransformationOpType) => {
    setEditingStep(null);
    setSelectedOpType(op);
    setFormulaResult(null);

    // Initial default configs
    if (op === 'join') {
      const otherDs = workspaceDatasets.find((d) => !pipeline?.source_dataset_ids.includes(d.id));
      setStepConfig({
        right_dataset_id: otherDs?.id || workspaceDatasets[0]?.id || '',
        join_type: 'inner',
        join_keys: [{ left: '', right: '' }],
        conflict_suffix_left: '_left',
        conflict_suffix_right: '_right',
      });
    } else if (op === 'append') {
      setStepConfig({
        dataset_ids: [],
        mode: 'all',
      });
    } else if (op === 'clean_nulls') {
      const firstCol = previewData?.columns[0]?.name || '';
      setStepConfig({
        strategies: [{ column: firstCol, strategy: 'drop', fill_value: '' }],
      });
    } else if (op === 'clean_duplicates') {
      setStepConfig({
        subset_columns: [],
      });
    } else if (op === 'type_cast') {
      const firstCol = previewData?.columns[0]?.name || '';
      setStepConfig({
        casts: [{ column: firstCol, target_type: 'string' }],
      });
    } else if (op === 'string_op') {
      const firstCol = previewData?.columns[0]?.name || '';
      setStepConfig({
        operations: [{ column: firstCol, op: 'trim' }],
      });
    } else if (op === 'formula') {
      setStepConfig({
        output_column: 'new_metric',
        expression: '',
      });
    } else if (op === 'filter') {
      const firstCol = previewData?.columns[0]?.name || '';
      setStepConfig({
        logical_op: 'AND',
        conditions: [{ column: firstCol, operator: 'eq', value: '' }],
      });
    } else if (op === 'select_columns') {
      setStepConfig({
        columns: previewData?.columns.map((c) => c.name) || [],
        renames: {},
      });
    }

    setIsStepModalOpen(true);
  };

  const openEditStepModal = (step: TransformationStep) => {
    setEditingStep(step);
    setSelectedOpType(step.operation_type);
    setStepConfig(JSON.parse(JSON.stringify(step.configuration || {})));
    setFormulaResult(null);
    setIsStepModalOpen(true);
  };

  const handleSaveStep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pipeline || !workspaceId) return;

    try {
      setSavingStep(true);
      setError(null);

      // If Join step adds a dataset not yet in source_dataset_ids, update source_dataset_ids
      if (selectedOpType === 'join' && stepConfig.right_dataset_id) {
        if (!pipeline.source_dataset_ids.includes(stepConfig.right_dataset_id)) {
          const updatedSources = [...pipeline.source_dataset_ids, stepConfig.right_dataset_id];
          await transformationService.updatePipeline(workspaceId, pipeline.id, {
            source_dataset_ids: updatedSources,
          });
        }
      }

      if (editingStep) {
        await transformationService.updateStep(workspaceId, pipeline.id, editingStep.id, {
          operation_type: selectedOpType,
          configuration: stepConfig,
        });
      } else {
        await transformationService.addStep(workspaceId, pipeline.id, {
          operation_type: selectedOpType,
          configuration: stepConfig,
          step_order: pipeline.steps.length,
        });
      }

      setIsStepModalOpen(false);
      await fetchPipeline();
      runPreview();
    } catch (err: any) {
      setError(err?.message || 'Failed to save transformation step.');
    } finally {
      setSavingStep(false);
    }
  };

  const handleDeleteStep = async (stepId: string) => {
    if (!pipeline || !workspaceId) return;
    try {
      await transformationService.deleteStep(workspaceId, pipeline.id, stepId);
      await fetchPipeline();
      runPreview();
    } catch (err: any) {
      setError(err?.message || 'Failed to delete step.');
    }
  };

  const handleMoveStep = async (index: number, direction: 'up' | 'down') => {
    if (!pipeline || !workspaceId) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= pipeline.steps.length) return;

    const newSteps = [...pipeline.steps];
    const [moved] = newSteps.splice(index, 1);
    newSteps.splice(targetIdx, 0, moved);

    try {
      await transformationService.reorderSteps(
        workspaceId,
        pipeline.id,
        newSteps.map((s) => s.id)
      );
      await fetchPipeline();
      runPreview();
    } catch (err: any) {
      setError(err?.message || 'Failed to reorder steps.');
    }
  };

  // Test Formula Validation
  const handleValidateFormula = async () => {
    if (!workspaceId || !stepConfig.expression) return;
    try {
      setFormulaValidating(true);
      const cols = previewData?.columns || [];
      const res = await transformationService.validateFormula(workspaceId, {
        expression: stepConfig.expression,
        columns: cols.map((c) => ({ name: c.name, data_type: c.data_type })),
      });
      setFormulaResult({
        valid: res.valid,
        error: res.error || undefined,
        sql: res.sql_expression || undefined,
      });
    } catch (err: any) {
      setFormulaResult({ valid: false, error: err?.message || 'Formula validation failed.' });
    } finally {
      setFormulaValidating(false);
    }
  };

  // Run Pipeline & Materialize
  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pipeline || !workspaceId) return;

    try {
      setRunningPipeline(true);
      setError(null);
      const run = await transformationService.runPipeline(workspaceId, pipeline.id, {
        output_dataset_name: outputDatasetName.trim() || undefined,
        output_dataset_description: outputDatasetDesc.trim() || undefined,
      });
      setRunSuccessResult(run);
      fetchPipeline();
    } catch (err: any) {
      setError(err?.message || 'Execution failed.');
    } finally {
      setRunningPipeline(false);
    }
  };

  // Helper icons and labels for operations
  const opMeta = {
    join: { label: 'Join Datasets', icon: GitMerge, color: 'text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40' },
    append: { label: 'Append (Union)', icon: Layers, color: 'text-blue-600 bg-blue-50 dark:bg-blue-950/40' },
    clean_nulls: { label: 'Clean Nulls', icon: Eraser, color: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40' },
    clean_duplicates: { label: 'Deduplicate', icon: CopyCheck, color: 'text-teal-600 bg-teal-50 dark:bg-teal-950/40' },
    type_cast: { label: 'Cast Types', icon: Type, color: 'text-purple-600 bg-purple-50 dark:bg-purple-950/40' },
    string_op: { label: 'String Operations', icon: SpellCheck, color: 'text-amber-600 bg-amber-50 dark:bg-amber-950/40' },
    formula: { label: 'Calculated Column', icon: Calculator, color: 'text-[#009F98] bg-teal-50 dark:bg-teal-950/40' },
    filter: { label: 'Filter Rows', icon: Filter, color: 'text-rose-600 bg-rose-50 dark:bg-rose-950/40' },
    select_columns: { label: 'Select / Rename', icon: CheckSquare, color: 'text-slate-600 bg-slate-50 dark:bg-slate-800' },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-3 border-[#009F98] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="p-8 text-center text-slate-500">
        <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        Pipeline not found.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden bg-slate-50 dark:bg-slate-950">
      {/* Top Action Bar */}
      <div className="h-16 px-6 bg-white dark:bg-slate-900 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between gap-4 z-10 flex-shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={() => navigate('/data-preparation')}
            className="p-2 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={pipeline.name}
                onChange={(e) => setPipeline({ ...pipeline, name: e.target.value })}
                className="font-bold text-base text-[#102C46] dark:text-slate-100 bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-700 focus:border-[#009F98] focus:outline-none transition-colors px-1 -mx-1"
              />
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {pipeline.steps.length} {pipeline.steps.length === 1 ? 'step' : 'steps'}
              </span>
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-500 truncate">
              {pipeline.description || 'No description provided.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => runPreview()}
            disabled={previewLoading}
            className="flex items-center gap-2 border-slate-200 dark:border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${previewLoading ? 'animate-spin' : ''}`} />
            Preview Data
          </Button>

          <Button
            variant="outline"
            onClick={handleSavePipeline}
            disabled={saving}
            className="flex items-center gap-2 border-slate-200 dark:border-slate-700"
          >
            {saveSuccess ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? 'Saving...' : saveSuccess ? 'Saved' : 'Save'}
          </Button>

          <Button
            onClick={() => setIsRunModalOpen(true)}
            className="flex items-center gap-2 bg-[#009F98] hover:bg-[#008c86] text-white shadow-sm"
          >
            <Play className="w-4 h-4 fill-white" />
            Run & Materialize
          </Button>
        </div>
      </div>

      {/* Error alert if any */}
      {error && (
        <div className="px-6 py-2 bg-red-50 dark:bg-red-950/30 border-b border-red-200 dark:border-red-900/40 text-red-700 dark:text-red-400 text-xs flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="font-semibold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Main 3-Column Studio Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Data Catalog & Sources */}
        <div className="w-72 bg-white dark:bg-slate-900 border-r border-slate-200/80 dark:border-slate-800 flex flex-col flex-shrink-0">
          <div className="p-4 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <Database className="w-4 h-4 text-[#009F98]" />
              Data Sources ({pipeline.source_dataset_ids.length})
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {pipeline.source_dataset_ids.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-400">
                No source datasets selected yet.
              </div>
            ) : (
              pipeline.source_dataset_ids.map((dsId, idx) => {
                const ds = workspaceDatasets.find((d) => d.id === dsId);
                const isPrimary = idx === 0;
                return (
                  <div
                    key={dsId}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="font-semibold text-xs text-[#102C46] dark:text-slate-200 truncate block">
                          {ds?.name || `Dataset ${dsId.slice(0, 8)}`}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {ds?.row_count ?? 0} rows · {isPrimary ? 'Primary Source' : 'Join Source'}
                        </span>
                      </div>
                      {isPrimary && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-teal-50 text-[#009F98] dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800/40 font-bold">
                          BASE
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {/* Add Source Dataset Dropdown */}
            <div className="pt-2">
              <label className="block text-[11px] font-medium text-slate-500 mb-1.5">
                Add Workspace Dataset
              </label>
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    const updated = [...pipeline.source_dataset_ids, e.target.value];
                    setPipeline({ ...pipeline, source_dataset_ids: updated });
                  }
                }}
                className="w-full px-2.5 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#009F98]"
              >
                <option value="">+ Add another dataset...</option>
                {workspaceDatasets
                  .filter((d) => !pipeline.source_dataset_ids.includes(d.id))
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.row_count} rows)
                    </option>
                  ))}
              </select>
            </div>
          </div>
        </div>

        {/* Center Column: Transformation Pipeline Step Chain */}
        <div className="w-96 bg-slate-50/50 dark:bg-slate-950/50 border-r border-slate-200/80 dark:border-slate-800 flex flex-col flex-shrink-0">
          <div className="p-4 bg-white dark:bg-slate-900 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <Workflow className="w-4 h-4 text-[#009F98]" />
              Transformation Steps
            </h3>

            {/* Add Step Dropdown Button */}
            <div className="relative group">
              <Button
                size="sm"
                className="flex items-center gap-1.5 bg-[#009F98] text-white text-xs py-1 px-2.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Step
              </Button>

              <div className="absolute right-0 top-full mt-1 w-52 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg p-1.5 hidden group-hover:block z-20 space-y-0.5">
                {(
                  [
                    'join',
                    'append',
                    'clean_nulls',
                    'clean_duplicates',
                    'type_cast',
                    'string_op',
                    'formula',
                    'filter',
                    'select_columns',
                  ] as TransformationOpType[]
                ).map((op) => {
                  const meta = opMeta[op];
                  const Icon = meta.icon;
                  return (
                    <button
                      key={op}
                      onClick={() => openAddStepModal(op)}
                      className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs text-left text-slate-700 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-teal-950/30 hover:text-[#009F98] transition-colors"
                    >
                      <div className={`p-1 rounded-md ${meta.color}`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span>{meta.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {pipeline.steps.length === 0 ? (
              <div className="text-center py-12 px-4 border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900/40">
                <Workflow className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  No steps in this pipeline
                </p>
                <p className="text-[11px] text-slate-400 mt-1 max-w-[200px] mx-auto">
                  Click "+ Add Step" above to add your first data transformation
                </p>
              </div>
            ) : (
              pipeline.steps.map((step, idx) => {
                const meta = opMeta[step.operation_type] || opMeta.select_columns;
                const Icon = meta.icon;
                const isCurrentPreview = activeStepIndex === idx;

                return (
                  <div
                    key={step.id}
                    className={`group bg-white dark:bg-slate-900 border rounded-xl p-3.5 transition-all shadow-sm ${
                      isCurrentPreview
                        ? 'border-[#009F98] ring-2 ring-[#009F98]/10'
                        : 'border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div
                          className={`p-1.5 rounded-lg mt-0.5 flex-shrink-0 ${meta.color}`}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] font-bold text-slate-400">
                              #{idx + 1}
                            </span>
                            <span className="font-semibold text-xs text-[#102C46] dark:text-slate-100 truncate">
                              {meta.label}
                            </span>
                          </div>

                          {/* Quick description based on op */}
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                            {step.operation_type === 'formula' &&
                              `${step.configuration?.output_column || 'metric'} = ${step.configuration?.expression || ''}`}
                            {step.operation_type === 'clean_nulls' &&
                              `Handling nulls for ${step.configuration?.strategies?.length || 1} column(s)`}
                            {step.operation_type === 'join' &&
                              `${step.configuration?.join_type?.toUpperCase()} join`}
                            {step.operation_type === 'clean_duplicates' && 'Deduplicating rows'}
                            {step.operation_type === 'filter' &&
                              `Filter (${step.configuration?.conditions?.length || 1} condition)`}
                            {step.operation_type === 'type_cast' && 'Casting column types'}
                            {step.operation_type === 'string_op' && 'String transformations'}
                            {step.operation_type === 'append' && 'Appending dataset rows'}
                            {step.operation_type === 'select_columns' && 'Selecting columns'}
                          </p>
                        </div>
                      </div>

                      {/* Reorder and Actions */}
                      <div className="flex items-center gap-0.5 opacity-80 group-hover:opacity-100">
                        <button
                          disabled={idx === 0}
                          onClick={() => handleMoveStep(idx, 'up')}
                          className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-20 rounded"
                          title="Move Up"
                        >
                          <ChevronUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          disabled={idx === pipeline.steps.length - 1}
                          onClick={() => handleMoveStep(idx, 'down')}
                          className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-20 rounded"
                          title="Move Down"
                        >
                          <ChevronDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px]">
                      <button
                        onClick={() => runPreview(idx)}
                        className={`inline-flex items-center gap-1 font-medium hover:underline ${
                          isCurrentPreview
                            ? 'text-[#009F98]'
                            : 'text-slate-500 dark:text-slate-400'
                        }`}
                      >
                        <Eye className="w-3 h-3" />
                        {isCurrentPreview ? 'Previewing here' : 'Preview this step'}
                      </button>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditStepModal(step)}
                          className="text-[#009F98] font-medium hover:underline"
                        >
                          Configure
                        </button>
                        <button
                          onClick={() => handleDeleteStep(step.id)}
                          className="text-red-500 font-medium hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Live Data & Schema Preview */}
        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-slate-900">
          {/* Preview Header */}
          <div className="h-12 px-6 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between flex-shrink-0 bg-slate-50/40 dark:bg-slate-950/30">
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center bg-slate-200/60 dark:bg-slate-800 p-0.5 rounded-lg">
                <button
                  onClick={() => setPreviewTab('table')}
                  className={`px-3 py-1 rounded-md font-medium transition-colors ${
                    previewTab === 'table'
                      ? 'bg-white dark:bg-slate-900 text-[#102C46] dark:text-slate-100 shadow-sm'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Data Table
                </button>
                <button
                  onClick={() => setPreviewTab('schema')}
                  className={`px-3 py-1 rounded-md font-medium transition-colors ${
                    previewTab === 'schema'
                      ? 'bg-white dark:bg-slate-900 text-[#102C46] dark:text-slate-100 shadow-sm'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Schema ({previewData?.columns.length || 0} cols)
                </button>
              </div>

              {previewData && (
                <div className="flex items-center gap-3 text-slate-400 text-[11px]">
                  <span>
                    Executed up to step #{previewData.step_executed}
                  </span>
                  <span>·</span>
                  <span>{previewData.total_rows_sampled} total rows</span>
                  <span>·</span>
                  <span>{previewData.execution_duration_ms}ms</span>
                </div>
              )}
            </div>

            <div>
              {previewLoading && (
                <span className="text-xs text-[#009F98] flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Updating preview...
                </span>
              )}
            </div>
          </div>

          {/* Preview Body */}
          <div className="flex-1 overflow-auto">
            {previewError ? (
              <div className="p-8 text-center max-w-lg mx-auto">
                <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto mb-3">
                  <AlertCircle className="w-6 h-6" />
                </div>
                <h4 className="font-semibold text-slate-800 dark:text-slate-200 text-sm">
                  Transformation Error
                </h4>
                <p className="text-xs text-red-600 dark:text-red-400 mt-1.5 font-mono bg-red-50 dark:bg-red-950/40 p-3 rounded-xl text-left overflow-x-auto">
                  {previewError}
                </p>
              </div>
            ) : !previewData || previewData.rows.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-400">
                <TableIcon className="w-10 h-10 mb-2 opacity-30" />
                <p className="text-sm font-medium">No preview data</p>
                <p className="text-xs mt-1">
                  Click "Preview Data" to run DuckDB across your configured pipeline steps
                </p>
              </div>
            ) : previewTab === 'table' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="sticky top-0 bg-slate-100/90 dark:bg-slate-800/90 backdrop-blur border-b border-slate-200 dark:border-slate-700 z-10">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold text-slate-400 text-[10px] uppercase w-12 text-center">
                        #
                      </th>
                      {previewData.columns.map((col) => (
                        <th key={col.name} className="py-2.5 px-4 font-semibold text-slate-700 dark:text-slate-200">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate">{col.name}</span>
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-normal text-slate-400 bg-slate-200 dark:bg-slate-700">
                              {col.data_type}
                            </span>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                    {previewData.rows.map((row, rIdx) => (
                      <tr
                        key={rIdx}
                        className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                      >
                        <td className="py-2 px-4 text-center text-[10px] text-slate-400 font-mono">
                          {rIdx + 1}
                        </td>
                        {previewData.columns.map((col) => {
                          const val = row[col.name];
                          return (
                            <td key={col.name} className="py-2 px-4 text-slate-600 dark:text-slate-300 whitespace-nowrap">
                              {val === null || val === undefined ? (
                                <span className="text-slate-300 dark:text-slate-600 italic">null</span>
                              ) : typeof val === 'boolean' ? (
                                val ? 'TRUE' : 'FALSE'
                              ) : (
                                String(val)
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Schema View */
              <div className="p-6 max-w-4xl">
                <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700">
                      <tr>
                        <th className="py-2.5 px-4 font-semibold text-slate-600 dark:text-slate-300">Column Name</th>
                        <th className="py-2.5 px-4 font-semibold text-slate-600 dark:text-slate-300">Data Type</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {previewData.columns.map((c) => (
                        <tr key={c.name}>
                          <td className="py-2.5 px-4 font-medium text-[#102C46] dark:text-slate-200">{c.name}</td>
                          <td className="py-2.5 px-4">
                            <span className="text-xs px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-950/40 text-[#009F98] border border-teal-200 dark:border-teal-800/40 font-mono">
                              {c.data_type}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Step Configuration Modal */}
      <Modal
        isOpen={isStepModalOpen}
        onClose={() => setIsStepModalOpen(false)}
        title={editingStep ? `Configure ${opMeta[selectedOpType]?.label}` : `Add ${opMeta[selectedOpType]?.label}`}
      >
        <form onSubmit={handleSaveStep} className="space-y-4">
          {/* JOIN CONFIGURATION */}
          {selectedOpType === 'join' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Right Dataset to Join *
                </label>
                <select
                  value={stepConfig.right_dataset_id || ''}
                  onChange={(e) => setStepConfig({ ...stepConfig, right_dataset_id: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  required
                >
                  <option value="">Select dataset...</option>
                  {workspaceDatasets.map((ds) => (
                    <option key={ds.id} value={ds.id}>
                      {ds.name} ({ds.row_count} rows)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Join Type
                </label>
                <select
                  value={stepConfig.join_type || 'inner'}
                  onChange={(e) => setStepConfig({ ...stepConfig, join_type: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                >
                  <option value="inner">INNER JOIN (Only matching rows)</option>
                  <option value="left">LEFT JOIN (All rows from left, matching from right)</option>
                  <option value="right">RIGHT JOIN (All rows from right, matching from left)</option>
                  <option value="full">FULL OUTER JOIN (All rows from both)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">
                    Left Key Column *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. customer_id"
                    value={stepConfig.join_keys?.[0]?.left || ''}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        join_keys: [{ ...stepConfig.join_keys?.[0], left: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">
                    Right Key Column *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. id"
                    value={stepConfig.join_keys?.[0]?.right || ''}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        join_keys: [{ ...stepConfig.join_keys?.[0], right: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  />
                </div>
              </div>
            </div>
          )}

          {/* FORMULA CONFIGURATION */}
          {selectedOpType === 'formula' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  New Output Column Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. net_revenue"
                  value={stepConfig.output_column || ''}
                  onChange={(e) => setStepConfig({ ...stepConfig, output_column: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Formula Expression *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. [price] * [quantity] * (1 - [discount]) or IF([sales] > 1000, 'High', 'Low')"
                  value={stepConfig.expression || ''}
                  onChange={(e) => setStepConfig({ ...stepConfig, expression: e.target.value })}
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-800 border rounded-lg"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Supported: +, -, *, /, %, ^, IF(cond, then, else), COALESCE(), UPPER(), LOWER(), ROUND()
                </p>
              </div>

              <div className="flex items-center justify-between pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleValidateFormula}
                  disabled={formulaValidating || !stepConfig.expression}
                  className="text-xs"
                >
                  {formulaValidating ? 'Validating...' : 'Validate Syntax'}
                </Button>

                {formulaResult && (
                  <span
                    className={`text-xs font-medium ${
                      formulaResult.valid ? 'text-emerald-600' : 'text-red-500'
                    }`}
                  >
                    {formulaResult.valid ? '✓ Valid formula' : `✗ ${formulaResult.error}`}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* CLEAN NULLS CONFIGURATION */}
          {selectedOpType === 'clean_nulls' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Target Column *
                </label>
                <select
                  value={stepConfig.strategies?.[0]?.column || ''}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      strategies: [{ ...stepConfig.strategies?.[0], column: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  required
                >
                  <option value="">Select column...</option>
                  {previewData?.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.data_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Null Handling Strategy
                </label>
                <select
                  value={stepConfig.strategies?.[0]?.strategy || 'drop'}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      strategies: [{ ...stepConfig.strategies?.[0], strategy: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                >
                  <option value="drop">Drop rows with NULLs</option>
                  <option value="fill_value">Fill with static value</option>
                  <option value="fill_mean">Fill with column Mean (Average)</option>
                  <option value="fill_median">Fill with column Median</option>
                  <option value="fill_mode">Fill with column Mode (Most frequent)</option>
                </select>
              </div>

              {stepConfig.strategies?.[0]?.strategy === 'fill_value' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">
                    Static Replacement Value
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 0 or Unknown"
                    value={stepConfig.strategies?.[0]?.fill_value ?? ''}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        strategies: [{ ...stepConfig.strategies?.[0], fill_value: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  />
                </div>
              )}
            </div>
          )}

          {/* DEDUPLICATE CONFIGURATION */}
          {selectedOpType === 'clean_duplicates' && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                Removes duplicate rows. Leave blank to check duplicates across all columns, or select specific key columns.
              </p>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">
                  Key Columns to Deduplicate (Comma separated, or blank for all)
                </label>
                <input
                  type="text"
                  placeholder="e.g. email, user_id"
                  value={stepConfig.subset_columns?.join(', ') || ''}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      subset_columns: e.target.value
                        ? e.target.value.split(',').map((s) => s.trim())
                        : [],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                />
              </div>
            </div>
          )}

          {/* TYPE CAST CONFIGURATION */}
          {selectedOpType === 'type_cast' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Target Column *</label>
                <select
                  value={stepConfig.casts?.[0]?.column || ''}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      casts: [{ ...stepConfig.casts?.[0], column: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  required
                >
                  <option value="">Select column...</option>
                  {previewData?.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Target Type</label>
                <select
                  value={stepConfig.casts?.[0]?.target_type || 'string'}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      casts: [{ ...stepConfig.casts?.[0], target_type: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                >
                  <option value="integer">Integer (Whole number)</option>
                  <option value="float">Float (Decimal)</option>
                  <option value="string">String (Text)</option>
                  <option value="boolean">Boolean (True/False)</option>
                  <option value="date">Date</option>
                  <option value="timestamp">Timestamp</option>
                </select>
              </div>
            </div>
          )}

          {/* STRING OP CONFIGURATION */}
          {selectedOpType === 'string_op' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Target Column *</label>
                <select
                  value={stepConfig.operations?.[0]?.column || ''}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      operations: [{ ...stepConfig.operations?.[0], column: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  required
                >
                  <option value="">Select column...</option>
                  {previewData?.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Operation</label>
                <select
                  value={stepConfig.operations?.[0]?.op || 'trim'}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      operations: [{ ...stepConfig.operations?.[0], op: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                >
                  <option value="trim">Trim Whitespace</option>
                  <option value="upper">UPPERCASE</option>
                  <option value="lower">lowercase</option>
                  <option value="capitalize">Capitalize</option>
                  <option value="replace">Replace Text</option>
                </select>
              </div>

              {stepConfig.operations?.[0]?.op === 'replace' && (
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="text"
                    placeholder="Search text"
                    value={stepConfig.operations?.[0]?.search || ''}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        operations: [{ ...stepConfig.operations?.[0], search: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  />
                  <input
                    type="text"
                    placeholder="Replace with"
                    value={stepConfig.operations?.[0]?.replace_with || ''}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        operations: [{ ...stepConfig.operations?.[0], replace_with: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  />
                </div>
              )}
            </div>
          )}

          {/* FILTER CONFIGURATION */}
          {selectedOpType === 'filter' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Filter Column *</label>
                <select
                  value={stepConfig.conditions?.[0]?.column || ''}
                  onChange={(e) =>
                    setStepConfig({
                      ...stepConfig,
                      conditions: [{ ...stepConfig.conditions?.[0], column: e.target.value }],
                    })
                  }
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  required
                >
                  <option value="">Select column...</option>
                  {previewData?.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Operator</label>
                  <select
                    value={stepConfig.conditions?.[0]?.operator || 'eq'}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        conditions: [{ ...stepConfig.conditions?.[0], operator: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  >
                    <option value="eq">Equals (=)</option>
                    <option value="neq">Not Equals (!=)</option>
                    <option value="gt">Greater Than (&gt;)</option>
                    <option value="gte">Greater or Equal (&gt;=)</option>
                    <option value="lt">Less Than (&lt;)</option>
                    <option value="lte">Less or Equal (&lt;=)</option>
                    <option value="contains">Contains (ILIKE)</option>
                    <option value="is_null">Is NULL</option>
                    <option value="not_null">Is NOT NULL</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Value</label>
                  <input
                    type="text"
                    placeholder="Comparison value"
                    value={stepConfig.conditions?.[0]?.value ?? ''}
                    onChange={(e) =>
                      setStepConfig({
                        ...stepConfig,
                        conditions: [{ ...stepConfig.conditions?.[0], value: e.target.value }],
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                  />
                </div>
              </div>
            </div>
          )}

          {/* APPEND (UNION) CONFIGURATION */}
          {selectedOpType === 'append' && (
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-500 mb-1">
                Select Datasets to Append (Union)
              </label>
              <div className="max-h-36 overflow-y-auto space-y-1 border rounded-lg p-2">
                {workspaceDatasets.map((ds) => {
                  const isChecked = stepConfig.dataset_ids?.includes(ds.id);
                  return (
                    <label key={ds.id} className="flex items-center gap-2 text-xs cursor-pointer p-1 rounded hover:bg-slate-50 dark:hover:bg-slate-800">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          const current = stepConfig.dataset_ids || [];
                          const updated = e.target.checked
                            ? [...current, ds.id]
                            : current.filter((id: string) => id !== ds.id);
                          setStepConfig({ ...stepConfig, dataset_ids: updated });
                        }}
                      />
                      <span>{ds.name}</span>
                    </label>
                  );
                })}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Union Mode</label>
                <select
                  value={stepConfig.mode || 'all'}
                  onChange={(e) => setStepConfig({ ...stepConfig, mode: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border rounded-lg"
                >
                  <option value="all">UNION ALL (Keep all rows)</option>
                  <option value="distinct">UNION DISTINCT (Remove duplicate rows)</option>
                </select>
              </div>
            </div>
          )}

          {/* SELECT COLUMNS CONFIGURATION */}
          {selectedOpType === 'select_columns' && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                Choose which columns to keep in the final dataset:
              </p>
              <div className="max-h-48 overflow-y-auto space-y-1 border rounded-lg p-2">
                {previewData?.columns.map((col) => {
                  const isChecked = stepConfig.columns?.includes(col.name);
                  return (
                    <label key={col.name} className="flex items-center gap-2 text-xs cursor-pointer p-1 rounded hover:bg-slate-50 dark:hover:bg-slate-800">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          const current = stepConfig.columns || [];
                          const updated = e.target.checked
                            ? [...current, col.name]
                            : current.filter((c: string) => c !== col.name);
                          setStepConfig({ ...stepConfig, columns: updated });
                        }}
                      />
                      <span>{col.name}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsStepModalOpen(false)}
              disabled={savingStep}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-[#009F98] hover:bg-[#008c86] text-white"
              disabled={savingStep}
            >
              {savingStep ? 'Saving...' : 'Apply Step'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Run Pipeline & Materialize Modal */}
      <Modal
        isOpen={isRunModalOpen}
        onClose={() => {
          setIsRunModalOpen(false);
          setRunSuccessResult(null);
        }}
        title="Execute Pipeline & Materialize Derived Dataset"
      >
        {runSuccessResult ? (
          <div className="text-center py-6 space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-base text-[#102C46] dark:text-slate-100">
                Dataset Materialized Successfully!
              </h4>
              <p className="text-xs text-slate-500 mt-1">
                Generated {runSuccessResult.row_count} rows in {runSuccessResult.execution_duration_ms}ms
              </p>
            </div>

            <div className="flex items-center justify-center gap-3 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setIsRunModalOpen(false);
                  setRunSuccessResult(null);
                }}
              >
                Done
              </Button>
              <Button
                onClick={() => navigate('/datasets')}
                className="bg-[#009F98] text-white flex items-center gap-2"
              >
                View Datasets <ExternalLink className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleRunPipeline} className="space-y-4">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              This executes all {pipeline.steps.length} transformation steps in DuckDB and saves
              the output as a permanent, first-class immutable Parquet dataset in your workspace.
            </p>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-500 mb-1.5">
                Derived Dataset Name *
              </label>
              <input
                type="text"
                required
                value={outputDatasetName}
                onChange={(e) => setOutputDatasetName(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border rounded-xl"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-500 mb-1.5">
                Description
              </label>
              <textarea
                rows={2}
                value={outputDatasetDesc}
                onChange={(e) => setOutputDatasetDesc(e.target.value)}
                placeholder="Optional description of this transformed dataset..."
                className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border rounded-xl"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsRunModalOpen(false)}
                disabled={runningPipeline}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="bg-[#009F98] hover:bg-[#008c86] text-white flex items-center gap-2"
                disabled={runningPipeline || !outputDatasetName.trim()}
              >
                {runningPipeline ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Executing Pipeline...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Execute & Save
                  </>
                )}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};

