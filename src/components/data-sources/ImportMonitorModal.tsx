import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Database,
  ArrowRight,
  StopCircle,
} from 'lucide-react';
import {
  DataSourceImport,
  dataSourceService,
} from '../../services/dataSourceService';

interface ImportMonitorModalProps {
  isOpen: boolean;
  onClose: () => void;
  importRecord: DataSourceImport | null;
  workspaceId: string;
}

export const ImportMonitorModal: React.FC<ImportMonitorModalProps> = ({
  isOpen,
  onClose,
  importRecord,
  workspaceId,
}) => {
  const navigate = useNavigate();
  const [currentImport, setCurrentImport] = useState<DataSourceImport | null>(importRecord);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    setCurrentImport(importRecord);
    if (!isOpen || !importRecord) return;

    if (importRecord.status === 'in_progress') {
      const interval = setInterval(async () => {
        try {
          const updated = await dataSourceService.getImportDetails(
            workspaceId,
            importRecord.connection_id,
            importRecord.id
          );
          setCurrentImport(updated);
          if (updated.status !== 'in_progress') {
            clearInterval(interval);
          }
        } catch {
          clearInterval(interval);
        }
      }, 1500);

      return () => clearInterval(interval);
    }
  }, [isOpen, importRecord, workspaceId]);

  if (!isOpen || !currentImport) return null;

  const handleCancel = async () => {
    setCancelling(true);
    try {
      const res = await dataSourceService.cancelImport(
        workspaceId,
        currentImport.connection_id,
        currentImport.id
      );
      setCurrentImport(res);
    } finally {
      setCancelling(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-[#102C46] to-[#0D3550] text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <h2 className="text-sm font-bold">Ingestion Status</h2>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                currentImport.status === 'completed'
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : currentImport.status === 'failed'
                  ? 'bg-rose-500/20 text-rose-300'
                  : currentImport.status === 'cancelled'
                  ? 'bg-gray-500/20 text-gray-300'
                  : 'bg-amber-500/20 text-amber-300 animate-pulse'
              }`}
            >
              {currentImport.status.replace('_', ' ')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[#BBDCE8] hover:text-white rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Status Body */}
        <div className="p-6 space-y-5 text-center">
          {currentImport.status === 'in_progress' ? (
            <div className="py-4">
              <Loader2 className="w-12 h-12 text-[#009F98] animate-spin mx-auto mb-3" />
              <h3 className="text-sm font-bold text-gray-800">Streaming Records into Parquet</h3>
              <p className="text-xs text-gray-500 mt-1 font-mono truncate px-4">
                {currentImport.source_resource}
              </p>
            </div>
          ) : currentImport.status === 'completed' ? (
            <div className="py-4">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-gray-800">Ingestion Succeeded</h3>
              <p className="text-xs text-gray-500 mt-1">
                Materialized as an immutable Parquet dataset version.
              </p>
            </div>
          ) : currentImport.status === 'cancelled' ? (
            <div className="py-4">
              <StopCircle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-gray-800">Ingestion Cancelled</h3>
              <p className="text-xs text-gray-500 mt-1">Operation terminated by user.</p>
            </div>
          ) : (
            <div className="py-4">
              <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-gray-800">Ingestion Failed</h3>
              <p className="text-xs text-rose-600 mt-1 px-4">{currentImport.error_message}</p>
            </div>
          )}

          {/* Metrics summary */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-gray-50 rounded-xl text-left border border-gray-100">
            <div>
              <span className="text-[10px] text-gray-400 uppercase font-semibold">Rows Ingested</span>
              <p className="text-base font-bold text-gray-800 font-mono">
                {currentImport.rows_imported.toLocaleString()}
              </p>
            </div>
            <div>
              <span className="text-[10px] text-gray-400 uppercase font-semibold">Data Size</span>
              <p className="text-base font-bold text-gray-800 font-mono">
                {formatBytes(currentImport.bytes_imported)}
              </p>
            </div>
            <div>
              <span className="text-[10px] text-gray-400 uppercase font-semibold">Mode</span>
              <p className="text-xs font-semibold text-gray-700 capitalize">
                {currentImport.import_mode}
              </p>
            </div>
            <div>
              <span className="text-[10px] text-gray-400 uppercase font-semibold">Watermark</span>
              <p className="text-xs font-mono text-gray-700 truncate">
                {currentImport.watermark_value || 'None'}
              </p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          {currentImport.status === 'in_progress' ? (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-colors flex items-center gap-1.5"
            >
              <StopCircle className="w-3.5 h-3.5" />
              {cancelling ? 'Cancelling...' : 'Cancel Sync'}
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-600 hover:text-gray-800"
            >
              Close
            </button>
          )}

          {currentImport.status === 'completed' && currentImport.dataset_id && (
            <button
              onClick={() => {
                onClose();
                navigate(`/data/${currentImport.dataset_id}`);
              }}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#009F98] to-[#007D78] text-white text-xs font-bold hover:shadow-md transition-all flex items-center gap-1.5"
            >
              <Database className="w-3.5 h-3.5" /> Open in Data Studio <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

