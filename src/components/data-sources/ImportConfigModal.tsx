import React, { useState, useEffect } from 'react';
import {
  X,
  DownloadCloud,
  Clock,
  Layers,
  ArrowRight,
  Loader2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import {
  DataSourceConnection,
  ColumnMetadata,
  dataSourceService,
  DataSourceImport,
} from '../../services/dataSourceService';

interface ImportConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  connection: DataSourceConnection | null;
  resourcePath: string;
  workspaceId: string;
  onImportStarted: (imp: DataSourceImport) => void;
}

export const ImportConfigModal: React.FC<ImportConfigModalProps> = ({
  isOpen,
  onClose,
  connection,
  resourcePath,
  workspaceId,
  onImportStarted,
}) => {
  const [datasetName, setDatasetName] = useState('');
  const [importMode, setImportMode] = useState<'full' | 'incremental'>('full');
  const [watermarkColumn, setWatermarkColumn] = useState('');
  const [scheduleFrequency, setScheduleFrequency] = useState<'none' | 'hourly' | 'daily' | 'weekly'>('none');
  const [columns, setColumns] = useState<ColumnMetadata[]>([]);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && connection && resourcePath) {
      setDatasetName(`${connection.name} - ${resourcePath}`);
      setImportMode('full');
      setWatermarkColumn('');
      setScheduleFrequency('none');
      setError(null);
      loadSchema();
    }
  }, [isOpen, connection, resourcePath]);

  const loadSchema = async () => {
    if (!connection || !resourcePath) return;
    setLoadingSchema(true);
    try {
      const res = await dataSourceService.getResourceSchema(workspaceId, connection.id, resourcePath);
      setColumns(res.columns || []);
      // Auto-suggest potential watermark column (e.g. updated_at, timestamp, id)
      const wmCandidate = res.columns.find(
        (c) =>
          c.name.toLowerCase().includes('update') ||
          c.name.toLowerCase().includes('time') ||
          c.name.toLowerCase().includes('date') ||
          c.name.toLowerCase() === 'id' ||
          c.name.toLowerCase() === '_id'
      );
      if (wmCandidate) {
        setWatermarkColumn(wmCandidate.name);
      }
    } catch {
      // Schema inspection optional for import
    } finally {
      setLoadingSchema(false);
    }
  };

  if (!isOpen || !connection) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetName.trim()) {
      setError('Dataset name is required');
      return;
    }
    if (importMode === 'incremental' && !watermarkColumn) {
      setError('A watermark column must be selected for incremental imports');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const imp = await dataSourceService.triggerImport(workspaceId, connection.id, {
        resource_path: resourcePath,
        import_mode: importMode,
        target_dataset_name: datasetName.trim(),
        watermark_column: importMode === 'incremental' ? watermarkColumn : undefined,
      });

      // If user enabled schedule, save refresh config
      if (scheduleFrequency !== 'none') {
        await dataSourceService.createRefreshConfig(workspaceId, connection.id, {
          frequency: scheduleFrequency,
          refresh_mode: importMode,
          target_resource: resourcePath,
          dataset_id: imp.dataset_id || undefined,
          watermark_column: importMode === 'incremental' ? watermarkColumn : undefined,
          is_active: true,
        });
      }

      onImportStarted(imp);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to start import job');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-[#102C46] to-[#0D3550] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-xl">
              <DownloadCloud className="w-5 h-5 text-[#39C3B8]" />
            </div>
            <div>
              <h2 className="text-base font-bold">Configure Ingestion</h2>
              <p className="text-xs text-[#BBDCE8] font-mono truncate max-w-xs">{resourcePath}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#BBDCE8] hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Target Dataset Name */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wider">
              Target Dataset Name *
            </label>
            <input
              type="text"
              required
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g. Postgres Orders Live"
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/20 focus:border-[#009F98]"
            />
            <p className="text-[11px] text-gray-500 mt-1">
              Data will be partitioned and written to immutable Parquet storage format.
            </p>
          </div>

          {/* Import Mode */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider">
              Ingestion Strategy
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setImportMode('full')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  importMode === 'full'
                    ? 'border-[#009F98] bg-[#E6F6F5]/40 ring-1 ring-[#009F98]'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-gray-800">Full Snapshot</span>
                  <Layers className={`w-4 h-4 ${importMode === 'full' ? 'text-[#009F98]' : 'text-gray-400'}`} />
                </div>
                <p className="text-[11px] text-gray-500">
                  Streams all records from the resource and establishes a clean version.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setImportMode('incremental')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  importMode === 'incremental'
                    ? 'border-[#009F98] bg-[#E6F6F5]/40 ring-1 ring-[#009F98]'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-gray-800">Incremental Sync</span>
                  <ArrowRight className={`w-4 h-4 ${importMode === 'incremental' ? 'text-[#009F98]' : 'text-gray-400'}`} />
                </div>
                <p className="text-[11px] text-gray-500">
                  Fetches only records where watermark column value exceeds previous run.
                </p>
              </button>
            </div>
          </div>

          {/* Watermark Column Picker */}
          {importMode === 'incremental' && (
            <div className="p-3.5 bg-gray-50 border border-gray-200 rounded-xl space-y-2 animate-fade-in">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-gray-700">Watermark Column *</label>
                <span className="text-[11px] text-gray-400">Timestamp or Sequential ID</span>
              </div>
              {loadingSchema ? (
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[#009F98]" />
                  <span>Loading column metadata...</span>
                </div>
              ) : columns.length > 0 ? (
                <select
                  value={watermarkColumn}
                  onChange={(e) => setWatermarkColumn(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-xs bg-white font-mono"
                >
                  <option value="">Select watermark column...</option>
                  {columns.map((col) => (
                    <option key={col.name} value={col.name}>
                      {col.name} ({col.type})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={watermarkColumn}
                  onChange={(e) => setWatermarkColumn(e.target.value)}
                  placeholder="e.g. updated_at or id"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-xs font-mono"
                />
              )}
            </div>
          )}

          {/* Schedule Frequency */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
              <Clock className="w-3.5 h-3.5 text-[#009F98]" /> Automated Sync Schedule
            </label>
            <select
              value={scheduleFrequency}
              onChange={(e: any) => setScheduleFrequency(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm bg-white"
            >
              <option value="none">Manual Trigger Only (No automated schedule)</option>
              <option value="hourly">Hourly Auto-Refresh</option>
              <option value="daily">Daily Auto-Refresh (Every 24 hours)</option>
              <option value="weekly">Weekly Auto-Refresh</option>
            </select>
          </div>

          {/* Submit Actions */}
          <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>DuckDB-queryable immediately</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-gray-600 hover:text-gray-800 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#009F98] to-[#007D78] text-white text-xs font-bold hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {submitting ? 'Starting...' : 'Start Ingestion'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

