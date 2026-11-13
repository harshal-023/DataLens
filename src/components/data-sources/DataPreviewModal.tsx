import React, { useState, useEffect } from 'react';
import {
  X,
  Table,
  Loader2,
  AlertCircle,
  DownloadCloud,
  CheckCircle,
} from 'lucide-react';
import {
  DataSourceConnection,
  ResourcePreview,
  dataSourceService,
} from '../../services/dataSourceService';

interface DataPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  connection: DataSourceConnection | null;
  resourcePath: string;
  workspaceId: string;
  onProceedToImport: (resource: string) => void;
}

export const DataPreviewModal: React.FC<DataPreviewModalProps> = ({
  isOpen,
  onClose,
  connection,
  resourcePath,
  workspaceId,
  onProceedToImport,
}) => {
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<ResourcePreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && connection && resourcePath) {
      loadPreview();
    } else {
      setPreview(null);
      setError(null);
    }
  }, [isOpen, connection, resourcePath]);

  const loadPreview = async () => {
    if (!connection || !resourcePath) return;
    setLoading(true);
    setError(null);
    try {
      const data = await dataSourceService.previewResource(workspaceId, connection.id, {
        resource_path: resourcePath,
        limit: 50,
      });
      setPreview(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch preview records from data source');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !connection) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-[#102C46] to-[#0D3550] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-xl">
              <Table className="w-5 h-5 text-[#39C3B8]" />
            </div>
            <div>
              <h2 className="text-base font-bold flex items-center gap-2">
                Preview: <span className="font-mono text-white/90">{resourcePath}</span>
              </h2>
              <p className="text-xs text-[#BBDCE8]">
                {preview ? `${preview.total_rows} sample records • ${preview.columns.length} columns inferred` : 'Loading sample rows...'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#BBDCE8] hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Table Body Area */}
        <div className="p-6 overflow-auto flex-1">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center text-gray-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-[#009F98]" />
              <p className="text-xs font-medium">Fetching remote records from {connection.name}...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-700 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : !preview || preview.rows.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-sm font-medium text-gray-600">No records returned</p>
              <p className="text-xs text-gray-400 mt-1">This resource appears to be currently empty.</p>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-xl overflow-hidden shadow-inner max-h-[500px] overflow-y-auto overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-[#102C46] text-white sticky top-0 z-10">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold text-[11px] text-[#BBDCE8] border-r border-[#1D4664]/60 w-12 text-center">
                      #
                    </th>
                    {preview.columns.map((col) => (
                      <th
                        key={col.name}
                        className="py-2.5 px-3 font-semibold text-xs border-r border-[#1D4664]/60 last:border-r-0 whitespace-nowrap"
                      >
                        <div className="flex items-center gap-1.5">
                          <span>{col.name}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-white/10 text-[#8BE5DE]">
                            {col.type}
                          </span>
                          {col.is_primary_key && (
                            <span className="text-amber-400 text-[10px] font-bold" title="Primary Key">
                              PK
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white font-mono">
                  {preview.rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-teal-50/40 transition-colors">
                      <td className="py-2 px-3 text-center text-gray-400 text-[11px] bg-gray-50/60 border-r border-gray-100">
                        {idx + 1}
                      </td>
                      {preview.columns.map((col) => {
                        const val = row[col.name];
                        return (
                          <td
                            key={col.name}
                            className="py-2 px-3 border-r border-gray-100 last:border-r-0 text-gray-800 whitespace-nowrap max-w-xs truncate"
                            title={String(val ?? '')}
                          >
                            {val === null || val === undefined ? (
                              <span className="text-gray-300 italic">null</span>
                            ) : typeof val === 'object' ? (
                              JSON.stringify(val)
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
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-emerald-700">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span>Schema inferred and data validated safely.</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-gray-600 hover:text-gray-800 text-xs font-semibold"
            >
              Close
            </button>
            <button
              onClick={() => {
                onClose();
                onProceedToImport(resourcePath);
              }}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#009F98] to-[#007D78] text-white text-xs font-bold hover:shadow-lg transition-all flex items-center gap-2"
            >
              <DownloadCloud className="w-4 h-4" /> Configure Ingestion
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

