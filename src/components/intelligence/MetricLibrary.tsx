import React, { useState } from 'react';
import {
  Calculator,
  Plus,
  Play,
  CheckCircle,
  AlertCircle,
  History,
  Trash2,
  Sparkles,
} from 'lucide-react';
import {
  MetricDefinition,
  MetricVersion,
  IntelligenceService,
} from '../../services/intelligenceService';

interface Props {
  datasetId?: string;
  metrics: MetricDefinition[];
  onRefresh: () => void;
}

export const MetricLibrary: React.FC<Props> = ({ datasetId, metrics, onRefresh }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [formula, setFormula] = useState('');
  const [formatting, setFormatting] = useState('CURRENCY');
  const [aggregation, setAggregation] = useState('SUM');

  // Live validation state
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    is_valid: boolean;
    referenced_columns: string[];
    errors: string[];
    compiled_sql?: string | null;
  } | null>(null);

  // Live calculation preview state
  const [isCalculating, setIsCalculating] = useState(false);
  const [calcPreview, setCalcPreview] = useState<{
    metric_value: number | null;
    is_null: boolean;
  } | null>(null);

  // Version history modal state
  const [viewingVersionsMetric, setViewingVersionsMetric] = useState<MetricDefinition | null>(null);
  const [versionHistory, setVersionHistory] = useState<MetricVersion[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleValidate = async () => {
    if (!formula.trim()) return;
    setIsValidating(true);
    setCalcPreview(null);
    try {
      const res = await IntelligenceService.validateFormula(formula);
      setValidationResult(res);
    } catch (err) {
      console.error('Validation error', err);
    } finally {
      setIsValidating(false);
    }
  };

  const handlePreviewCalculate = async () => {
    if (!datasetId || !formula.trim()) return;
    setIsCalculating(true);
    try {
      const res = await IntelligenceService.calculateMetric(datasetId, formula, aggregation);
      setCalcPreview(res);
    } catch (err) {
      console.error('Calculation error', err);
    } finally {
      setIsCalculating(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !formula.trim()) return;
    setIsSubmitting(true);
    try {
      await IntelligenceService.createMetric({
        dataset_id: datasetId,
        name,
        description,
        formula,
        formatting,
        aggregation,
        source_columns: validationResult?.referenced_columns || [],
      });
      setIsModalOpen(false);
      setName('');
      setDescription('');
      setFormula('');
      setValidationResult(null);
      setCalcPreview(null);
      onRefresh();
    } catch (err) {
      console.error('Failed to create metric', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewVersions = async (m: MetricDefinition) => {
    setViewingVersionsMetric(m);
    setIsLoadingVersions(true);
    try {
      const vers = await IntelligenceService.getMetricVersions(m.id);
      setVersionHistory(vers);
    } catch (err) {
      console.error('Failed to fetch versions', err);
    } finally {
      setIsLoadingVersions(false);
    }
  };

  const handleDelete = async (mId: string) => {
    if (!confirm('Are you sure you want to delete this metric?')) return;
    try {
      await IntelligenceService.deleteMetric(mId);
      onRefresh();
    } catch (err) {
      console.error('Failed to delete metric', err);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
            <Calculator className="w-4 h-4 text-[#009F98]" />
            <span>Reusable Metric Registry & Formula Engine</span>
            <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-normal">
              {metrics.length} metrics
            </span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Verified business formulas, division-by-zero protection, and version audit history.
          </p>
        </div>
        <div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-3 py-1.5 bg-[#009F98] hover:bg-[#008983] text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> New Business Metric
          </button>
        </div>
      </div>

      <div className="p-4">
        {metrics.length === 0 ? (
          <div className="text-center py-8">
            <Calculator className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-slate-700">No Metrics Registered</h4>
            <p className="text-xs text-slate-500 mt-1 mb-3">
              Define standard formulas like 'Revenue / Total Orders' or 'SUM(revenue)' for reusable reporting.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium"
            >
              Add Your First Metric
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {metrics.map((m) => (
              <div
                key={m.id}
                className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-semibold text-slate-900 text-xs truncate">
                      {m.name}
                    </span>
                    <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                      v{m.version}
                    </span>
                  </div>

                  <div className="font-mono text-[11px] text-[#009F98] bg-slate-50 p-2 rounded border border-slate-100 mb-2 truncate">
                    {m.formula}
                  </div>

                  {m.description && (
                    <p className="text-[11px] text-slate-500 line-clamp-2 mb-2">
                      {m.description}
                    </p>
                  )}

                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 font-medium">
                      {m.formatting}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 font-medium">
                      {m.aggregation}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2.5 mt-2.5 border-t border-slate-100 text-xs">
                  <button
                    onClick={() => handleViewVersions(m)}
                    className="text-slate-400 hover:text-slate-700 text-[11px] flex items-center gap-1"
                    title="View version history"
                  >
                    <History className="w-3.5 h-3.5" /> History
                  </button>

                  <button
                    onClick={() => handleDelete(m.id)}
                    className="text-slate-400 hover:text-rose-600 p-1 rounded"
                    title="Delete metric"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Metric Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-[#009F98]" />
                Register Business Metric
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-4 space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Metric Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Average Order Value, Gross Profit Margin"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#009F98]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Formula Expression *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. Revenue / Total_Orders or SUM(revenue) - SUM(cost)"
                    value={formula}
                    onChange={(e) => setFormula(e.target.value)}
                    className="flex-1 font-mono text-xs p-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#009F98]"
                    required
                  />
                  <button
                    type="button"
                    onClick={handleValidate}
                    disabled={isValidating || !formula.trim()}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg transition-colors shrink-0"
                  >
                    {isValidating ? 'Validating...' : 'Validate'}
                  </button>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Safe AST evaluation with automatic division-by-zero protection.
                </p>
              </div>

              {/* Validation Result Box */}
              {validationResult && (
                <div
                  className={`p-2.5 rounded-lg border text-xs ${
                    validationResult.is_valid
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : 'bg-rose-50 border-rose-200 text-rose-800'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-semibold">
                    {validationResult.is_valid ? (
                      <>
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Valid mathematical expression</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                        <span>Formula validation failed:</span>
                      </>
                    )}
                  </div>
                  {validationResult.errors.length > 0 && (
                    <ul className="list-disc pl-4 mt-1 text-[11px] space-y-0.5">
                      {validationResult.errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  )}
                  {validationResult.referenced_columns.length > 0 && (
                    <div className="mt-1 text-[11px]">
                      Referenced identifiers:{' '}
                      <span className="font-mono">
                        {validationResult.referenced_columns.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Live Preview Calculation Button */}
              {datasetId && validationResult?.is_valid && (
                <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <div>
                    <span className="text-[11px] font-semibold text-slate-700 block">
                      Live DuckDB Preview:
                    </span>
                    <span className="text-xs font-mono font-bold text-[#009F98]">
                      {calcPreview ? (
                        calcPreview.is_null ? (
                          'NULL'
                        ) : (
                          `${calcPreview.metric_value?.toLocaleString()}`
                        )
                      ) : (
                        'Not tested yet'
                      )}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handlePreviewCalculate}
                    disabled={isCalculating}
                    className="px-2.5 py-1 bg-slate-200 hover:bg-slate-300 text-slate-800 text-[11px] font-medium rounded flex items-center gap-1"
                  >
                    <Play className="w-3 h-3 text-[#009F98]" />
                    {isCalculating ? 'Computing...' : 'Calculate on Dataset'}
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Formatting
                  </label>
                  <select
                    value={formatting}
                    onChange={(e) => setFormatting(e.target.value)}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg"
                  >
                    <option value="CURRENCY">Currency ($ / USD)</option>
                    <option value="INR">Indian Rupee (₹ / INR)</option>
                    <option value="PERCENTAGE">Percentage (%)</option>
                    <option value="INTEGER">Integer Number</option>
                    <option value="DECIMAL">Decimal Number</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Aggregation
                  </label>
                  <select
                    value={aggregation}
                    onChange={(e) => setAggregation(e.target.value)}
                    className="w-full text-xs p-2 border border-slate-300 rounded-lg"
                  >
                    <option value="SUM">SUM</option>
                    <option value="AVG">AVG</option>
                    <option value="COUNT">COUNT</option>
                    <option value="COUNT_DISTINCT">COUNT DISTINCT</option>
                    <option value="CALCULATED">CALCULATED</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Description
                </label>
                <textarea
                  placeholder="Optional business definition and usage notes..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full text-xs p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !name.trim() || !formula.trim()}
                  className="px-4 py-1.5 bg-[#009F98] hover:bg-[#008983] text-white text-xs font-semibold rounded-lg disabled:opacity-50"
                >
                  {isSubmitting ? 'Registering...' : 'Save Metric'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {viewingVersionsMetric && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-1.5">
                <History className="w-4 h-4 text-[#009F98]" />
                Version History: {viewingVersionsMetric.name}
              </h3>
              <button
                onClick={() => setViewingVersionsMetric(null)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-4 max-h-80 overflow-y-auto space-y-2.5">
              {isLoadingVersions ? (
                <div className="text-center py-6 text-xs text-slate-400">Loading versions...</div>
              ) : versionHistory.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-400">
                  No historical changes recorded.
                </div>
              ) : (
                versionHistory.map((v) => (
                  <div
                    key={v.id}
                    className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-slate-900">Version {v.version_number}</span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(v.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="font-mono text-[#009F98] text-[11px] mb-1">{v.formula}</div>
                    {v.change_summary && (
                      <p className="text-[10px] text-slate-500 italic">{v.change_summary}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

