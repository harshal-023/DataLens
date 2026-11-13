import React, { useState, useEffect } from 'react';
import {
  X,
  Database,
  Globe,
  Table,
  Layers,
  Archive,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import {
  ConnectorMetadata,
  DataSourceConnection,
  dataSourceService,
  ConnectionTestResult,
} from '../../services/dataSourceService';

interface ConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  connector: ConnectorMetadata | null;
  existingConnection?: DataSourceConnection | null;
  workspaceId: string;
  onSuccess: (conn: DataSourceConnection) => void;
}

export const ConnectorModal: React.FC<ConnectorModalProps> = ({
  isOpen,
  onClose,
  connector,
  existingConnection,
  workspaceId,
  onSuccess,
}) => {
  const [name, setName] = useState('');
  const [config, setConfig] = useState<Record<string, any>>({});
  const [credentials, setCredentials] = useState<Record<string, any>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (existingConnection) {
      setName(existingConnection.name);
      setConfig(existingConnection.config || {});
      setCredentials({});
    } else if (connector) {
      setName(`${connector.name} Connection`);
      if (connector.type === 'postgres') {
        setConfig({ host: 'localhost', port: 5432, database: 'postgres', ssl: false });
      } else if (connector.type === 'mysql') {
        setConfig({ host: 'localhost', port: 3306, database: '', charset: 'utf8mb4', ssl: false });
      } else if (connector.type === 'rest_api') {
        setConfig({
          base_url: 'https://api.example.com/v1',
          auth_type: 'none',
          pagination_type: 'none',
          page_size: 100,
        });
      } else if (connector.type === 'google_sheets') {
        setConfig({ spreadsheet_id: '' });
      } else if (connector.type === 'mongodb') {
        setConfig({ host: 'localhost', port: 27017, database: 'analytics', auth_source: 'admin' });
      } else if (connector.type === 's3') {
        setConfig({ bucket: '', region_name: 'us-east-1', prefix: '' });
      }
      setCredentials({});
    }
    setTestResult(null);
    setError(null);
  }, [connector, existingConnection, isOpen]);

  if (!isOpen || !connector) return null;

  const handleConfigChange = (key: string, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleCredChange = (key: string, value: any) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const res = await dataSourceService.testConnection({
        source_type: connector.type,
        config,
        credentials,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        status: 'failed',
        latency_ms: 0,
        message: err.message || 'Connection test failed',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Connection name is required');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      let saved: DataSourceConnection;
      if (existingConnection) {
        saved = await dataSourceService.updateConnection(workspaceId, existingConnection.id, {
          name: name.trim(),
          config,
          credentials: Object.keys(credentials).length > 0 ? credentials : undefined,
        });
      } else {
        saved = await dataSourceService.createConnection(workspaceId, {
          name: name.trim(),
          source_type: connector.type,
          config,
          credentials,
          is_active: true,
        });
      }
      onSuccess(saved);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save connection');
    } finally {
      setSaving(false);
    }
  };

  const getConnectorIcon = () => {
    switch (connector.type) {
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
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-[#102C46] to-[#0D3550] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-white/10 rounded-xl backdrop-blur-md">
              {getConnectorIcon()}
            </div>
            <div>
              <h2 className="text-lg font-bold">
                {existingConnection ? 'Configure' : 'Connect'} {connector.name}
              </h2>
              <p className="text-xs text-[#BBDCE8]">{connector.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-[#BBDCE8] hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 overflow-y-auto space-y-5 flex-1">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2.5 text-rose-700 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Connection Name */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wider">
              Connection Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Analytics DB"
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98] text-sm text-gray-800"
            />
          </div>

          {/* Relational: PostgreSQL & MySQL */}
          {(connector.type === 'postgres' || connector.type === 'mysql') && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Host / Endpoint *</label>
                  <input
                    type="text"
                    required
                    value={config.host || ''}
                    onChange={(e) => handleConfigChange('host', e.target.value)}
                    placeholder="localhost or db.company.com"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Port *</label>
                  <input
                    type="number"
                    required
                    value={config.port || (connector.type === 'postgres' ? 5432 : 3306)}
                    onChange={(e) => handleConfigChange('port', parseInt(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Database Name *</label>
                <input
                  type="text"
                  required
                  value={config.database || ''}
                  onChange={(e) => handleConfigChange('database', e.target.value)}
                  placeholder="e.g. analytics_production"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Username *</label>
                  <input
                    type="text"
                    required
                    value={credentials.username || ''}
                    onChange={(e) => handleCredChange('username', e.target.value)}
                    placeholder="read_user"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Password {existingConnection ? '(leave blank to keep stored)' : '*'}
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required={!existingConnection}
                      value={credentials.password || ''}
                      onChange={(e) => handleCredChange('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3.5 py-2.5 pr-10 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="ssl_toggle"
                  checked={Boolean(config.ssl)}
                  onChange={(e) => handleConfigChange('ssl', e.target.checked)}
                  className="w-4 h-4 text-[#009F98] rounded border-gray-300 focus:ring-[#009F98]"
                />
                <label htmlFor="ssl_toggle" className="text-xs font-medium text-gray-700 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#009F98]" /> Require SSL Encryption
                </label>
              </div>
            </div>
          )}

          {/* REST API */}
          {connector.type === 'rest_api' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Base API URL *</label>
                <input
                  type="url"
                  required
                  value={config.base_url || ''}
                  onChange={(e) => handleConfigChange('base_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-[#009F98]/30 focus:border-[#009F98]"
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  Protected by SSRF security filtering against private loopback/internal hosts.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Authentication Type</label>
                  <select
                    value={config.auth_type || 'none'}
                    onChange={(e) => handleConfigChange('auth_type', e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm bg-white"
                  >
                    <option value="none">No Auth</option>
                    <option value="bearer">Bearer Token</option>
                    <option value="api_key">API Key (Header)</option>
                    <option value="basic">Basic Auth</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Pagination Strategy</label>
                  <select
                    value={config.pagination_type || 'none'}
                    onChange={(e) => handleConfigChange('pagination_type', e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm bg-white"
                  >
                    <option value="none">No Pagination (Single page)</option>
                    <option value="offset_limit">Offset & Limit</option>
                    <option value="page">Page & Page Size</option>
                    <option value="cursor">Cursor-based</option>
                  </select>
                </div>
              </div>

              {config.auth_type === 'bearer' && (
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Bearer Token *</label>
                  <input
                    type="password"
                    value={credentials.token || ''}
                    onChange={(e) => handleCredChange('token', e.target.value)}
                    placeholder="eyJhbGciOi..."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                  />
                </div>
              )}

              {config.auth_type === 'api_key' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1.5">Header Name</label>
                    <input
                      type="text"
                      value={config.api_key_header || 'X-API-Key'}
                      onChange={(e) => handleConfigChange('api_key_header', e.target.value)}
                      placeholder="X-API-Key"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1.5">API Key Value *</label>
                    <input
                      type="password"
                      value={credentials.api_key || ''}
                      onChange={(e) => handleCredChange('api_key', e.target.value)}
                      placeholder="api_live_..."
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Data Extraction Path (optional)</label>
                <input
                  type="text"
                  value={config.data_path || ''}
                  onChange={(e) => handleConfigChange('data_path', e.target.value)}
                  placeholder="e.g. data or items or response.results"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                />
              </div>
            </div>
          )}

          {/* Google Sheets */}
          {connector.type === 'google_sheets' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Google Spreadsheet ID *</label>
                <input
                  type="text"
                  required
                  value={config.spreadsheet_id || ''}
                  onChange={(e) => handleConfigChange('spreadsheet_id', e.target.value)}
                  placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-mono"
                />
                <p className="text-[11px] text-gray-500 mt-1">Found in the Google Sheet URL after /d/ and before /edit</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Client ID</label>
                  <input
                    type="text"
                    value={credentials.client_id || ''}
                    onChange={(e) => handleCredChange('client_id', e.target.value)}
                    placeholder="apps.googleusercontent.com"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Client Secret</label>
                  <input
                    type="password"
                    value={credentials.client_secret || ''}
                    onChange={(e) => handleCredChange('client_secret', e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">OAuth Refresh Token *</label>
                <input
                  type="password"
                  value={credentials.refresh_token || ''}
                  onChange={(e) => handleCredChange('refresh_token', e.target.value)}
                  placeholder="1//04..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-mono"
                />
              </div>
            </div>
          )}

          {/* MongoDB */}
          {connector.type === 'mongodb' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Connection URI (optional)</label>
                <input
                  type="text"
                  value={credentials.uri || ''}
                  onChange={(e) => handleCredChange('uri', e.target.value)}
                  placeholder="mongodb+srv://user:pass@cluster0.mongodb.net/analytics"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-mono"
                />
              </div>

              {!credentials.uri && (
                <>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Host *</label>
                      <input
                        type="text"
                        value={config.host || ''}
                        onChange={(e) => handleConfigChange('host', e.target.value)}
                        placeholder="localhost"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Port *</label>
                      <input
                        type="number"
                        value={config.port || 27017}
                        onChange={(e) => handleConfigChange('port', parseInt(e.target.value))}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Database Name *</label>
                      <input
                        type="text"
                        value={config.database || ''}
                        onChange={(e) => handleConfigChange('database', e.target.value)}
                        placeholder="analytics"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Auth Source</label>
                      <input
                        type="text"
                        value={config.auth_source || 'admin'}
                        onChange={(e) => handleConfigChange('auth_source', e.target.value)}
                        placeholder="admin"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Username</label>
                      <input
                        type="text"
                        value={credentials.username || ''}
                        onChange={(e) => handleCredChange('username', e.target.value)}
                        placeholder="mongo_user"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Password</label>
                      <input
                        type="password"
                        value={credentials.password || ''}
                        onChange={(e) => handleCredChange('password', e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                      />
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* S3 Storage */}
          {connector.type === 's3' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">S3 Bucket *</label>
                  <input
                    type="text"
                    required
                    value={config.bucket || ''}
                    onChange={(e) => handleConfigChange('bucket', e.target.value)}
                    placeholder="my-analytics-data"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Region *</label>
                  <input
                    type="text"
                    required
                    value={config.region_name || 'us-east-1'}
                    onChange={(e) => handleConfigChange('region_name', e.target.value)}
                    placeholder="us-east-1"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Custom S3 Endpoint (MinIO / R2 / Wasabi)</label>
                <input
                  type="url"
                  value={config.endpoint_url || ''}
                  onChange={(e) => handleConfigChange('endpoint_url', e.target.value)}
                  placeholder="https://minio.internal.com:9000 (leave blank for AWS)"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Access Key ID *</label>
                  <input
                    type="text"
                    required
                    value={credentials.access_key_id || ''}
                    onChange={(e) => handleCredChange('access_key_id', e.target.value)}
                    placeholder="AKIA..."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Secret Access Key *</label>
                  <input
                    type="password"
                    required
                    value={credentials.secret_access_key || ''}
                    onChange={(e) => handleCredChange('secret_access_key', e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Folder Prefix (optional)</label>
                <input
                  type="text"
                  value={config.prefix || ''}
                  onChange={(e) => handleConfigChange('prefix', e.target.value)}
                  placeholder="raw/data/"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm"
                />
              </div>
            </div>
          )}

          {/* Test Status Feedback Banner */}
          {testResult && (
            <div
              className={`p-3.5 rounded-xl border flex items-center justify-between text-xs animate-fade-in ${
                testResult.status === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
            >
              <div className="flex items-center gap-2">
                {testResult.status === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                )}
                <span>{testResult.message}</span>
              </div>
              {testResult.status === 'success' && (
                <span className="font-mono font-bold text-emerald-700 shrink-0">
                  ⚡ {testResult.latency_ms} ms
                </span>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
            <button
              type="button"
              disabled={testing || saving}
              onClick={handleTestConnection}
              className="px-4 py-2.5 rounded-xl border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-amber-500" />}
              {testing ? 'Testing...' : 'Test Connection'}
            </button>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-xl text-gray-600 hover:text-gray-800 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || testing}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#009F98] to-[#007D78] text-white text-xs font-bold hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {existingConnection ? 'Update Connection' : 'Save Connection'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

