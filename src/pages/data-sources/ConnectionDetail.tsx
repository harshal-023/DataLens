import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  Database,
  Globe,
  Table,
  Layers,
  Archive,
  Zap,
  FolderOpen,
  RefreshCw,
  Sliders,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  DownloadCloud,
  Calendar,
  ExternalLink,
  ShieldCheck,
  StopCircle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  DataSourceConnection,
  DataSourceImport,
  RefreshConfig,
  dataSourceService,
} from '../../services/dataSourceService';
import { ResourceBrowserModal } from '../../components/data-sources/ResourceBrowserModal';
import { DataPreviewModal } from '../../components/data-sources/DataPreviewModal';
import { ImportConfigModal } from '../../components/data-sources/ImportConfigModal';
import { ImportMonitorModal } from '../../components/data-sources/ImportMonitorModal';

export const ConnectionDetail: React.FC = () => {
  const { connectionId } = useParams<{ connectionId: string }>();
  const { currentWorkspace } = useAuth();
  const navigate = useNavigate();
  const workspaceId = currentWorkspace?.id || '';

  const [connection, setConnection] = useState<DataSourceConnection | null>(null);
  const [imports, setImports] = useState<DataSourceImport[]>([]);
  const [refreshConfigs, setRefreshConfigs] = useState<RefreshConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'history' | 'schedules' | 'schema'>('history');
  const [testing, setTesting] = useState(false);

  // Modals state
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);
  const [previewResource, setPreviewResource] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [importResource, setImportResource] = useState<string | null>(null);
  const [isImportConfigOpen, setIsImportConfigOpen] = useState(false);
  const [activeImport, setActiveImport] = useState<DataSourceImport | null>(null);
  const [isMonitorOpen, setIsMonitorOpen] = useState(false);

  useEffect(() => {
    if (workspaceId && connectionId) {
      loadDetails();
    }
  }, [workspaceId, connectionId]);

  const loadDetails = async () => {
    if (!workspaceId || !connectionId) return;
    setLoading(true);
    try {
      const [conn, impList, schedList] = await Promise.all([
        dataSourceService.getConnection(workspaceId, connectionId),
        dataSourceService.listImports(workspaceId, connectionId),
        dataSourceService.getRefreshConfigs(workspaceId, connectionId),
      ]);
      setConnection(conn);
      setImports(impList);
      setRefreshConfigs(schedList);
    } catch (err) {
      console.error('Failed to load connection detail:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!connectionId) return;
    setTesting(true);
    try {
      const res = await dataSourceService.testSavedConnection(workspaceId, connectionId);
      setConnection((prev) =>
        prev
          ? {
              ...prev,
              status: res.status === 'success' ? 'ready' : 'error',
              last_tested_at: new Date().toISOString(),
            }
          : null
      );
    } finally {
      setTesting(false);
    }
  };

  const handleTriggerSync = async () => {
    if (!connection) return;
    try {
      const imp = await dataSourceService.triggerRefresh(workspaceId, connection.id);
      setActiveImport(imp);
      setIsMonitorOpen(true);
      loadDetails();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    }
  };

  const handleDeleteConnection = async () => {
    if (!connection || !window.confirm('Are you sure you want to delete this connection?')) return;
    try {
      await dataSourceService.deleteConnection(workspaceId, connection.id);
      navigate('/data-sources');
    } catch (err) {
      console.error('Failed to delete connection:', err);
    }
  };

  const getConnectorIcon = (type: string) => {
    switch (type) {
      case 'postgres':
      case 'mysql':
        return <Database className="w-6 h-6 text-[#009F98]" />;
      case 'rest_api':
        return <Globe className="w-6 h-6 text-[#009F98]" />;
      case 'google_sheets':
        return <Table className="w-6 h-6 text-[#009F98]" />;
      case 'mongodb':
        return <Layers className="w-6 h-6 text-[#009F98]" />;
      case 's3':
        return <Archive className="w-6 h-6 text-[#009F98]" />;
      default:
        return <Database className="w-6 h-6 text-[#009F98]" />;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <RefreshCw className="w-8 h-8 animate-spin text-[#009F98]" />
      </div>
    );
  }

  if (!connection) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 gap-4">
        <AlertCircle className="w-12 h-12 text-rose-500" />
        <p className="text-gray-700 font-bold">Connection Not Found</p>
        <button
          onClick={() => navigate('/data-sources')}
          className="px-4 py-2 bg-[#102C46] text-white rounded-xl text-xs font-semibold"
        >
          Return to Data Sources
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50/60 pb-16">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-[#102C46] to-[#0D3550] text-white border-b border-[#1D4664]/50 px-8 py-6">
        <div className="max-w-7xl mx-auto space-y-4">
          <button
            onClick={() => navigate('/data-sources')}
            className="flex items-center gap-1.5 text-xs text-[#BBDCE8] hover:text-white transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Back to Data Sources
          </button>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3.5 bg-white/10 rounded-2xl backdrop-blur-md">
                {getConnectorIcon(connection.source_type)}
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-xl font-black text-white">{connection.name}</h1>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      connection.status === 'ready'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : connection.status === 'error'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : 'bg-white/10 text-white/80'
                    }`}
                  >
                    {connection.status === 'ready' && <CheckCircle2 className="w-3 h-3" />}
                    {connection.status === 'error' && <AlertCircle className="w-3 h-3" />}
                    {connection.status}
                  </span>
                </div>
                <p className="text-xs text-[#BBDCE8] mt-1 capitalize">
                  {connection.source_type.replace('_', ' ')} • Created on{' '}
                  {new Date(connection.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleTestConnection}
                disabled={testing}
                className="px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors border border-white/10"
              >
                <Zap className={`w-3.5 h-3.5 text-amber-400 ${testing ? 'animate-spin' : ''}`} />
                {testing ? 'Testing...' : 'Test Connection'}
              </button>

              <button
                onClick={() => setIsBrowserOpen(true)}
                className="px-3.5 py-2 rounded-xl bg-[#009F98] hover:bg-[#007D78] text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow-md"
              >
                <FolderOpen className="w-3.5 h-3.5" /> Browse Objects
              </button>

              <button
                onClick={handleTriggerSync}
                className="p-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs transition-colors border border-white/10"
                title="Trigger Manual Sync"
              >
                <RefreshCw className="w-4 h-4" />
              </button>

              <button
                onClick={handleDeleteConnection}
                className="p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs transition-colors border border-rose-500/20"
                title="Delete Connection"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-8 py-8 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-gray-200">
          <button
            onClick={() => setActiveTab('history')}
            className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'history'
                ? 'border-[#009F98] text-[#009F98]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <Clock className="w-3.5 h-3.5" /> Ingestion History ({imports.length})
          </button>

          <button
            onClick={() => setActiveTab('schedules')}
            className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'schedules'
                ? 'border-[#009F98] text-[#009F98]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" /> Refresh Schedules ({refreshConfigs.length})
          </button>
        </div>

        {/* Tab 1: Ingestion History */}
        {activeTab === 'history' && (
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
            {imports.length === 0 ? (
              <div className="py-16 text-center text-gray-400">
                <DownloadCloud className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p className="text-sm font-semibold text-gray-700">No Ingestions Executed Yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Browse remote tables to start streaming records into Parquet datasets.
                </p>
              </div>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase tracking-wider font-semibold text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Resource</th>
                    <th className="py-3 px-4">Mode</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Rows</th>
                    <th className="py-3 px-4">Bytes</th>
                    <th className="py-3 px-4">Watermark</th>
                    <th className="py-3 px-4">Completed</th>
                    <th className="py-3 px-4 text-right">Dataset</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 font-mono">
                  {imports.map((imp) => (
                    <tr key={imp.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="py-3 px-4 font-bold text-gray-800 truncate max-w-xs">
                        {imp.source_resource}
                      </td>
                      <td className="py-3 px-4 capitalize font-sans text-gray-600">
                        {imp.import_mode}
                      </td>
                      <td className="py-3 px-4 font-sans">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            imp.status === 'completed'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : imp.status === 'failed'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : imp.status === 'cancelled'
                              ? 'bg-gray-100 text-gray-600 border border-gray-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200 animate-pulse'
                          }`}
                        >
                          {imp.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-700">
                        {imp.rows_imported.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-gray-500">
                        {formatBytes(imp.bytes_imported)}
                      </td>
                      <td className="py-3 px-4 text-gray-500 truncate max-w-[120px]">
                        {imp.watermark_value || '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-400 font-sans text-[11px]">
                        {imp.completed_at
                          ? new Date(imp.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : 'In progress'}
                      </td>
                      <td className="py-3 px-4 text-right font-sans">
                        {imp.dataset_id && (
                          <button
                            onClick={() => navigate(`/data/${imp.dataset_id}`)}
                            className="text-[#009F98] hover:underline font-bold text-xs inline-flex items-center gap-1"
                          >
                            View <ExternalLink className="w-3 h-3" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tab 2: Refresh Schedules */}
        {activeTab === 'schedules' && (
          <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-gray-900">Configured Sync Schedules</h3>
                <p className="text-xs text-gray-500">Automated background syncs managed by the system scheduler.</p>
              </div>
            </div>

            {refreshConfigs.length === 0 ? (
              <div className="py-12 text-center text-gray-400 border border-dashed border-gray-200 rounded-xl">
                <Calendar className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-xs font-semibold text-gray-700">No automated schedules active</p>
                <p className="text-[11px] text-gray-400 mt-1">
                  Enable automatic hourly, daily, or weekly syncs when configuring an import.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100 border border-gray-200 rounded-xl overflow-hidden">
                {refreshConfigs.map((cfg) => (
                  <div key={cfg.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                    <div>
                      <span className="text-xs font-bold text-gray-800 font-mono">
                        {cfg.target_resource}
                      </span>
                      <p className="text-[11px] text-gray-500">
                        Frequency: <span className="font-semibold capitalize text-gray-700">{cfg.frequency}</span> • Mode:{' '}
                        <span className="font-semibold capitalize text-gray-700">{cfg.refresh_mode}</span>
                      </p>
                    </div>

                    <div className="text-right">
                      <span className="text-[11px] text-gray-400 block">Next Run:</span>
                      <span className="text-xs font-mono font-semibold text-gray-700">
                        {cfg.next_run_at ? new Date(cfg.next_run_at).toLocaleString() : 'N/A'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      <ResourceBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        connection={connection}
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
        connection={connection}
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
        connection={connection}
        resourcePath={importResource || ''}
        workspaceId={workspaceId}
        onImportStarted={(imp) => {
          setActiveImport(imp);
          setIsMonitorOpen(true);
          loadDetails();
        }}
      />

      <ImportMonitorModal
        isOpen={isMonitorOpen}
        onClose={() => {
          setIsMonitorOpen(false);
          loadDetails();
        }}
        importRecord={activeImport}
        workspaceId={workspaceId}
      />
    </div>
  );
};

