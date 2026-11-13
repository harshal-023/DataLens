import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  Globe,
  Table,
  Layers,
  Archive,
  Plus,
  RefreshCw,
  Search,
  ExternalLink,
  Zap,
  MoreVertical,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  Sliders,
  FolderOpen,
  ArrowRight,
  ShieldCheck,
  Activity,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  ConnectorMetadata,
  DataSourceConnection,
  DataSourceImport,
  dataSourceService,
} from '../../services/dataSourceService';
import { ConnectorModal } from '../../components/data-sources/ConnectorModal';
import { ResourceBrowserModal } from '../../components/data-sources/ResourceBrowserModal';
import { DataPreviewModal } from '../../components/data-sources/DataPreviewModal';
import { ImportConfigModal } from '../../components/data-sources/ImportConfigModal';
import { ImportMonitorModal } from '../../components/data-sources/ImportMonitorModal';

export const DataSourcesOverview: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const navigate = useNavigate();

  const [connectors, setConnectors] = useState<ConnectorMetadata[]>([]);
  const [connections, setConnections] = useState<DataSourceConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  // Modals state
  const [selectedConnector, setSelectedConnector] = useState<ConnectorMetadata | null>(null);
  const [editingConnection, setEditingConnection] = useState<DataSourceConnection | null>(null);
  const [isConnectorModalOpen, setIsConnectorModalOpen] = useState(false);

  const [activeConnection, setActiveConnection] = useState<DataSourceConnection | null>(null);
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);

  const [previewResource, setPreviewResource] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const [importResource, setImportResource] = useState<string | null>(null);
  const [isImportConfigOpen, setIsImportConfigOpen] = useState(false);

  const [activeImport, setActiveImport] = useState<DataSourceImport | null>(null);
  const [isMonitorOpen, setIsMonitorOpen] = useState(false);

  // Testing indicator per connection id
  const [testingId, setTestingId] = useState<string | null>(null);

  const workspaceId = currentWorkspace?.id || '';

  useEffect(() => {
    loadData();
  }, [workspaceId]);

  const loadData = async () => {
    if (!workspaceId) return;
    setLoading(true);
    try {
      const [allConnectors, allConns] = await Promise.all([
        dataSourceService.listConnectors(),
        dataSourceService.listConnections(workspaceId),
      ]);
      setConnectors(allConnectors);
      setConnections(allConns);
    } catch (err) {
      console.error('Failed to load data sources:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (conn: DataSourceConnection) => {
    setTestingId(conn.id);
    try {
      const res = await dataSourceService.testSavedConnection(workspaceId, conn.id);
      // Update local state status
      setConnections((prev) =>
        prev.map((c) =>
          c.id === conn.id
            ? { ...c, status: res.status === 'success' ? 'ready' : 'error', last_tested_at: new Date().toISOString() }
            : c
        )
      );
    } catch {
      setConnections((prev) =>
        prev.map((c) => (c.id === conn.id ? { ...c, status: 'error' } : c))
      );
    } finally {
      setTestingId(null);
    }
  };

  const handleDeleteConnection = async (connId: string) => {
    if (!window.confirm('Are you sure you want to delete this connection?')) return;
    try {
      await dataSourceService.deleteConnection(workspaceId, connId);
      setConnections((prev) => prev.filter((c) => c.id !== connId));
    } catch (err) {
      console.error('Failed to delete connection:', err);
    }
  };

  const handleManualRefresh = async (conn: DataSourceConnection) => {
    try {
      const imp = await dataSourceService.triggerRefresh(workspaceId, conn.id);
      setActiveImport(imp);
      setIsMonitorOpen(true);
    } catch (err: any) {
      alert(`Refresh failed: ${err.message}`);
    }
  };

  const getConnectorIcon = (type: string, className = 'w-6 h-6 text-[#009F98]') => {
    switch (type) {
      case 'postgres':
      case 'mysql':
        return <Database className={className} />;
      case 'rest_api':
        return <Globe className={className} />;
      case 'google_sheets':
        return <Table className={className} />;
      case 'mongodb':
        return <Layers className={className} />;
      case 's3':
        return <Archive className={className} />;
      default:
        return <Database className={className} />;
    }
  };

  const filteredConnections = connections.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.source_type.toLowerCase().includes(search.toLowerCase());
    const matchesType = filterType === 'all' || c.source_type === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="min-h-screen bg-gray-50/60 pb-16">
      {/* Top Header Banner */}
      <div className="bg-gradient-to-r from-[#102C46] via-[#0D3550] to-[#0A485A] text-white border-b border-[#1D4664]/50 px-8 py-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#009F98]/30 text-[#8BE5DE] border border-[#009F98]/50 uppercase tracking-wider">
                  Enterprise Connectors
                </span>
                <span className="text-xs text-[#BBDCE8]">Unified Ingestion</span>
              </div>
              <h1 className="text-2xl font-black tracking-tight text-white">External Data Sources</h1>
              <p className="text-sm text-[#BBDCE8] mt-1">
                Connect external relational databases, document stores, object storage, and APIs directly into immutable Parquet datasets.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={loadData}
                disabled={loading}
                className="px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white border border-white/15 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Metric KPI Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <span className="text-[11px] font-semibold text-[#BBDCE8] uppercase tracking-wider">
                Configured Sources
              </span>
              <p className="text-2xl font-black text-white mt-1">{connections.length}</p>
            </div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <span className="text-[11px] font-semibold text-[#BBDCE8] uppercase tracking-wider">
                Supported Connectors
              </span>
              <p className="text-2xl font-black text-[#39C3B8] mt-1">{connectors.length || 6}</p>
            </div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <span className="text-[11px] font-semibold text-[#BBDCE8] uppercase tracking-wider">
                Active & Healthy
              </span>
              <p className="text-2xl font-black text-emerald-400 mt-1">
                {connections.filter((c) => c.status === 'ready').length}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <span className="text-[11px] font-semibold text-[#BBDCE8] uppercase tracking-wider">
                Encryption Vault
              </span>
              <p className="text-2xl font-black text-[#8BE5DE] mt-1 flex items-center gap-1.5">
                <ShieldCheck className="w-5 h-5 text-[#39C3B8]" /> AES-256
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-8 space-y-10">
        {/* Section 1: Connector Gallery */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-gray-900">Available External Connectors</h2>
              <p className="text-xs text-gray-500">
                Choose a data provider to configure streaming ingestion pipelines.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connectors.map((c) => (
              <div
                key={c.type}
                className="group p-5 bg-white rounded-2xl border border-gray-200 hover:border-[#009F98]/50 hover:shadow-lg transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="p-3 bg-[#E6F6F5] rounded-xl text-[#009F98] group-hover:scale-105 transition-transform">
                      {getConnectorIcon(c.type)}
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-100 text-gray-600 uppercase tracking-wider">
                      {c.category}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-gray-900 mb-1">{c.name}</h3>
                  <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
                    {c.description}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-semibold">
                    {c.supports_ssl && (
                      <span className="flex items-center gap-0.5 text-emerald-600">
                        <ShieldCheck className="w-3 h-3" /> SSL
                      </span>
                    )}
                    {c.supports_watermark && (
                      <span className="flex items-center gap-0.5 text-[#009F98]">
                        • Watermarks
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setSelectedConnector(c);
                      setEditingConnection(null);
                      setIsConnectorModalOpen(true);
                    }}
                    className="px-3.5 py-1.5 rounded-xl bg-[#102C46] hover:bg-[#009F98] text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Connect
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 2: Connected Sources Table */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-gray-900">Configured Data Sources</h2>
              <p className="text-xs text-gray-500">
                Active connections configured in this workspace.
              </p>
            </div>

            {/* Filter and search */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter connections..."
                  className="pl-8 pr-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs focus:ring-2 focus:ring-[#009F98]/20 focus:border-[#009F98]"
                />
              </div>

              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700"
              >
                <option value="all">All Types</option>
                <option value="postgres">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="rest_api">REST API</option>
                <option value="google_sheets">Google Sheets</option>
                <option value="mongodb">MongoDB</option>
                <option value="s3">S3 Storage</option>
              </select>
            </div>
          </div>

          {filteredConnections.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-gray-200">
              <Database className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-gray-800">No Data Sources Connected Yet</h3>
              <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                Select one of the connectors above to connect PostgreSQL, MySQL, REST APIs, Google Sheets, MongoDB, or S3.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase tracking-wider font-semibold text-[11px]">
                    <tr>
                      <th className="py-3 px-4">Source Name</th>
                      <th className="py-3 px-4">Provider</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Last Tested</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredConnections.map((conn) => (
                      <tr key={conn.id} className="hover:bg-gray-50/70 transition-colors">
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-[#E6F6F5] rounded-xl text-[#009F98] shrink-0">
                              {getConnectorIcon(conn.source_type, 'w-4 h-4 text-[#009F98]')}
                            </div>
                            <div>
                              <button
                                onClick={() => navigate(`/data-sources/${conn.id}`)}
                                className="text-xs font-bold text-gray-900 hover:text-[#009F98] text-left transition-colors flex items-center gap-1.5"
                              >
                                {conn.name}
                                <ExternalLink className="w-3 h-3 text-gray-400" />
                              </button>
                              <span className="text-[10px] text-gray-400 font-mono">
                                ID: {conn.id.slice(0, 8)}...
                              </span>
                            </div>
                          </div>
                        </td>

                        <td className="py-3.5 px-4 font-semibold text-gray-700 capitalize">
                          {conn.source_type.replace('_', ' ')}
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              conn.status === 'ready'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : conn.status === 'error'
                                ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                : 'bg-gray-100 text-gray-700 border border-gray-200'
                            }`}
                          >
                            {conn.status === 'ready' && <CheckCircle2 className="w-3 h-3" />}
                            {conn.status === 'error' && <AlertCircle className="w-3 h-3" />}
                            {conn.status}
                          </span>
                        </td>

                        <td className="py-3.5 px-4 text-gray-500">
                          {conn.last_tested_at ? (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-gray-400" />
                              {new Date(conn.last_tested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          ) : (
                            <span className="text-gray-400">Never</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            {/* Test Connection Button */}
                            <button
                              onClick={() => handleTestConnection(conn)}
                              disabled={testingId === conn.id}
                              className="px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-100 text-xs font-semibold flex items-center gap-1 transition-colors"
                              title="Ping connection"
                            >
                              <Zap className={`w-3 h-3 text-amber-500 ${testingId === conn.id ? 'animate-spin' : ''}`} />
                              {testingId === conn.id ? 'Pinging...' : 'Test'}
                            </button>

                            {/* Browse Resources */}
                            <button
                              onClick={() => {
                                setActiveConnection(conn);
                                setIsBrowserOpen(true);
                              }}
                              className="px-2.5 py-1.5 rounded-lg bg-[#E6F6F5] text-[#009F98] hover:bg-[#009F98] hover:text-white text-xs font-bold transition-all flex items-center gap-1"
                              title="Browse tables and objects"
                            >
                              <FolderOpen className="w-3 h-3" /> Browse
                            </button>

                            {/* Quick Sync / Refresh */}
                            <button
                              onClick={() => handleManualRefresh(conn)}
                              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors"
                              title="Trigger immediate sync"
                            >
                              <RefreshCw className="w-3.5 h-3.5" />
                            </button>

                            {/* Settings / Edit */}
                            <button
                              onClick={() => {
                                const foundMeta = connectors.find((m) => m.type === conn.source_type);
                                setSelectedConnector(foundMeta || null);
                                setEditingConnection(conn);
                                setIsConnectorModalOpen(true);
                              }}
                              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors"
                              title="Edit connection settings"
                            >
                              <Sliders className="w-3.5 h-3.5" />
                            </button>

                            {/* Delete */}
                            <button
                              onClick={() => handleDeleteConnection(conn.id)}
                              className="p-1.5 rounded-lg text-rose-500 hover:text-rose-700 hover:bg-rose-50 transition-colors"
                              title="Delete connection"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
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

      {/* Modals */}
      <ConnectorModal
        isOpen={isConnectorModalOpen}
        onClose={() => setIsConnectorModalOpen(false)}
        connector={selectedConnector}
        existingConnection={editingConnection}
        workspaceId={workspaceId}
        onSuccess={() => loadData()}
      />

      <ResourceBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        connection={activeConnection}
        workspaceId={workspaceId}
        onSelectResourceForPreview={(resource) => {
          setPreviewResource(resource);
          setIsPreviewOpen(true);
        }}
        onSelectResourceForImport={(resource) => {
          setImportResource(resource);
          setIsImportConfigOpen(true);
        }}
      />

      <DataPreviewModal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        connection={activeConnection}
        resourcePath={previewResource || ''}
        workspaceId={workspaceId}
        onProceedToImport={(resource) => {
          setImportResource(resource);
          setIsImportConfigOpen(true);
        }}
      />

      <ImportConfigModal
        isOpen={isImportConfigOpen}
        onClose={() => setIsImportConfigOpen(false)}
        connection={activeConnection}
        resourcePath={importResource || ''}
        workspaceId={workspaceId}
        onImportStarted={(imp) => {
          setActiveImport(imp);
          setIsMonitorOpen(true);
        }}
      />

      <ImportMonitorModal
        isOpen={isMonitorOpen}
        onClose={() => setIsMonitorOpen(false)}
        importRecord={activeImport}
        workspaceId={workspaceId}
      />
    </div>
  );
};

