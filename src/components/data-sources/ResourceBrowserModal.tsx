import React, { useState, useEffect } from 'react';
import {
  X,
  Search,
  Table,
  FileText,
  Eye,
  DownloadCloud,
  Loader2,
  AlertCircle,
  Database,
  Layers,
} from 'lucide-react';
import {
  DataSourceConnection,
  ResourceDiscovery,
  dataSourceService,
} from '../../services/dataSourceService';

interface ResourceBrowserModalProps {
  isOpen: boolean;
  onClose: () => void;
  connection: DataSourceConnection | null;
  workspaceId: string;
  onSelectResourceForPreview: (resource: string) => void;
  onSelectResourceForImport: (resource: string) => void;
}

export const ResourceBrowserModal: React.FC<ResourceBrowserModalProps> = ({
  isOpen,
  onClose,
  connection,
  workspaceId,
  onSelectResourceForPreview,
  onSelectResourceForImport,
}) => {
  const [loading, setLoading] = useState(false);
  const [discovery, setDiscovery] = useState<ResourceDiscovery | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && connection) {
      loadDiscovery();
    } else {
      setDiscovery(null);
      setSearch('');
      setError(null);
    }
  }, [isOpen, connection]);

  const loadDiscovery = async () => {
    if (!connection) return;
    setLoading(true);
    setError(null);
    try {
      const data = await dataSourceService.discoverResources(workspaceId, connection.id);
      setDiscovery(data);
    } catch (err: any) {
      setError(err.message || 'Failed to discover resources from external source');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !connection) return null;

  // Flatten resources from schemas dict
  const allResources: Array<{ path: string; name: string; schema?: string; type: string; extra?: any }> = [];
  if (discovery?.schemas) {
    Object.entries(discovery.schemas).forEach(([schemaName, items]) => {
      if (Array.isArray(items)) {
        items.forEach((item: any) => {
          const resName = item.name || item.path || item;
          const fullPath = schemaName !== 'sheets' && schemaName !== 'files' && schemaName !== 'endpoints' && schemaName
            ? `${schemaName}.${resName}`
            : resName;
          allResources.push({
            path: fullPath,
            name: resName,
            schema: schemaName,
            type: item.type || 'TABLE',
            extra: item,
          });
        });
      }
    });
  }

  const filteredResources = allResources.filter((r) =>
    r.path.toLowerCase().includes(search.toLowerCase()) ||
    r.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-[#102C46] to-[#0D3550] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-xl">
              <Database className="w-5 h-5 text-[#39C3B8]" />
            </div>
            <div>
              <h2 className="text-base font-bold">Discover Resources: {connection.name}</h2>
              <p className="text-xs text-[#BBDCE8]">
                {discovery?.database ? `Database: ${discovery.database} • ` : ''}
                {discovery?.bucket ? `Bucket: ${discovery.bucket} • ` : ''}
                {discovery?.total_tables || 0} objects discovered
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

        {/* Search Bar */}
        <div className="px-6 py-3.5 border-b border-gray-100 bg-gray-50 flex items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tables, collections, files, or sheets..."
              className="w-full pl-9 pr-4 py-2 bg-white rounded-xl border border-gray-200 text-xs focus:outline-none focus:ring-2 focus:ring-[#009F98]/20 focus:border-[#009F98]"
            />
          </div>
          <button
            onClick={loadDiscovery}
            disabled={loading}
            className="px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto flex-1">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-gray-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-[#009F98]" />
              <p className="text-xs font-medium">Inspecting remote catalog and schemas...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-700 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : filteredResources.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <Table className="w-10 h-10 mx-auto mb-2 text-gray-300" />
              <p className="text-sm font-medium text-gray-600">No matching resources found</p>
              <p className="text-xs text-gray-400 mt-1">Check permissions or try adjusting search criteria</p>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-100">
              {filteredResources.map((res) => (
                <div
                  key={res.path}
                  className="px-4 py-3 hover:bg-gray-50/80 transition-colors flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-[#E6F6F5] text-[#009F98] rounded-lg shrink-0">
                      {res.type === 'COLLECTION' ? (
                        <Layers className="w-4 h-4" />
                      ) : res.type === 'PARQUET' || res.type === 'CSV' ? (
                        <FileText className="w-4 h-4" />
                      ) : (
                        <Table className="w-4 h-4" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-800 truncate font-mono">
                        {res.path}
                      </p>
                      <p className="text-[11px] text-gray-500">
                        Type: <span className="font-semibold text-gray-700">{res.type}</span>
                        {res.extra?.row_count ? ` • ${res.extra.row_count.toLocaleString()} rows` : ''}
                        {res.extra?.size_bytes ? ` • ${(res.extra.size_bytes / 1024).toFixed(1)} KB` : ''}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => onSelectResourceForPreview(res.path)}
                      className="px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-100 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      title="Preview sample records"
                    >
                      <Eye className="w-3.5 h-3.5 text-gray-500" /> Preview
                    </button>
                    <button
                      onClick={() => onSelectResourceForImport(res.path)}
                      className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-[#009F98] to-[#007D78] text-white text-xs font-bold hover:shadow-md transition-all flex items-center gap-1.5"
                    >
                      <DownloadCloud className="w-3.5 h-3.5" /> Import
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <span>Showing {filteredResources.length} of {allResources.length} resources</span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-gray-600 hover:text-gray-800 font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

