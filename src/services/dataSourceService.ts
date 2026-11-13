/**
 * Data Source Connector Service
 * Manages external data sources, live testing, resource discovery, previews,
 * imports, and scheduled refreshes across all 6 connector types.
 */

import { apiClient } from './apiClient';

export type DataSourceType = 'postgres' | 'mysql' | 'rest_api' | 'google_sheets' | 'mongodb' | 's3';

export interface ConnectorMetadata {
  type: DataSourceType;
  name: string;
  category: string;
  icon: string;
  description: string;
  default_port?: number;
  supports_watermark: boolean;
  supports_ssl: boolean;
}

export interface DataSourceConnection {
  id: string;
  workspace_id: string;
  name: string;
  source_type: DataSourceType;
  config: Record<string, any>;
  status: 'configured' | 'ready' | 'error' | 'syncing';
  last_tested_at?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectionTestResult {
  status: 'success' | 'failed';
  latency_ms: number;
  message: string;
  server_version?: string | null;
}

export interface ColumnMetadata {
  name: string;
  type: string;
  nullable: boolean;
  is_primary_key: boolean;
  default?: string | null;
}

export interface ResourceDiscovery {
  database?: string | null;
  bucket?: string | null;
  schemas: Record<string, any>;
  available_databases?: string[] | null;
  total_tables: number;
}

export interface ResourcePreview {
  resource: string;
  columns: ColumnMetadata[];
  rows: Record<string, any>[];
  total_rows: number;
}

export interface DataSourceImport {
  id: string;
  connection_id: string;
  workspace_id: string;
  dataset_id?: string | null;
  dataset_version_id?: string | null;
  source_resource: string;
  import_mode: 'full' | 'incremental';
  watermark_column?: string | null;
  watermark_value?: string | null;
  status: 'in_progress' | 'completed' | 'failed' | 'cancelled';
  rows_imported: number;
  bytes_imported: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface RefreshConfig {
  id: string;
  connection_id: string;
  dataset_id?: string | null;
  frequency: 'hourly' | 'daily' | 'weekly' | 'custom_cron';
  cron_expression?: string | null;
  refresh_mode: 'full' | 'incremental';
  target_resource: string;
  watermark_column?: string | null;
  timezone: string;
  is_active: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
  created_at: string;
  updated_at: string;
}

export const dataSourceService = {
  // Connector Metadata
  async listConnectors(): Promise<ConnectorMetadata[]> {
    return apiClient<ConnectorMetadata[]>('/api/v1/connections/connectors', {
      method: 'GET',
    });
  },

  // Test on-the-fly
  async testConnection(payload: {
    source_type: string;
    config: Record<string, any>;
    credentials: Record<string, any>;
  }): Promise<ConnectionTestResult> {
    return apiClient<ConnectionTestResult>('/api/v1/connections/test', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Connection CRUD
  async listConnections(workspaceId: string): Promise<DataSourceConnection[]> {
    return apiClient<DataSourceConnection[]>('/api/v1/connections', {
      method: 'GET',
      workspaceId,
    });
  },

  async getConnection(workspaceId: string, connectionId: string): Promise<DataSourceConnection> {
    return apiClient<DataSourceConnection>(`/api/v1/connections/${connectionId}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async createConnection(
    workspaceId: string,
    payload: {
      name: string;
      source_type: string;
      config: Record<string, any>;
      credentials: Record<string, any>;
      is_active?: boolean;
    }
  ): Promise<DataSourceConnection> {
    return apiClient<DataSourceConnection>('/api/v1/connections', {
      method: 'POST',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  async updateConnection(
    workspaceId: string,
    connectionId: string,
    payload: {
      name?: string;
      config?: Record<string, any>;
      credentials?: Record<string, any>;
      is_active?: boolean;
    }
  ): Promise<DataSourceConnection> {
    return apiClient<DataSourceConnection>(`/api/v1/connections/${connectionId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  async deleteConnection(workspaceId: string, connectionId: string): Promise<void> {
    return apiClient<void>(`/api/v1/connections/${connectionId}`, {
      method: 'DELETE',
      workspaceId,
    });
  },

  async testSavedConnection(workspaceId: string, connectionId: string): Promise<ConnectionTestResult> {
    return apiClient<ConnectionTestResult>(`/api/v1/connections/${connectionId}/test`, {
      method: 'POST',
      workspaceId,
    });
  },

  // Discovery & Exploration
  async discoverResources(workspaceId: string, connectionId: string): Promise<ResourceDiscovery> {
    return apiClient<ResourceDiscovery>(`/api/v1/connections/${connectionId}/discover`, {
      method: 'GET',
      workspaceId,
    });
  },

  async getResourceSchema(
    workspaceId: string,
    connectionId: string,
    resourcePath: string
  ): Promise<{ resource: string; columns: ColumnMetadata[] }> {
    return apiClient<{ resource: string; columns: ColumnMetadata[] }>(
      `/api/v1/connections/${connectionId}/schema?resource_path=${encodeURIComponent(resourcePath)}`,
      {
        method: 'GET',
        workspaceId,
      }
    );
  },

  async previewResource(
    workspaceId: string,
    connectionId: string,
    payload: { resource_path: string; limit?: number }
  ): Promise<ResourcePreview> {
    return apiClient<ResourcePreview>(`/api/v1/connections/${connectionId}/preview`, {
      method: 'POST',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  // Ingestion & Imports
  async triggerImport(
    workspaceId: string,
    connectionId: string,
    payload: {
      resource_path: string;
      import_mode?: 'full' | 'incremental';
      target_dataset_name?: string;
      target_dataset_id?: string;
      watermark_column?: string;
    }
  ): Promise<DataSourceImport> {
    return apiClient<DataSourceImport>(`/api/v1/connections/${connectionId}/imports`, {
      method: 'POST',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  async listImports(workspaceId: string, connectionId: string): Promise<DataSourceImport[]> {
    return apiClient<DataSourceImport[]>(`/api/v1/connections/${connectionId}/imports`, {
      method: 'GET',
      workspaceId,
    });
  },

  async getImportDetails(workspaceId: string, connectionId: string, importId: string): Promise<DataSourceImport> {
    return apiClient<DataSourceImport>(`/api/v1/connections/${connectionId}/imports/${importId}`, {
      method: 'GET',
      workspaceId,
    });
  },

  async cancelImport(workspaceId: string, connectionId: string, importId: string): Promise<DataSourceImport> {
    return apiClient<DataSourceImport>(`/api/v1/connections/${connectionId}/imports/${importId}/cancel`, {
      method: 'POST',
      workspaceId,
    });
  },

  // Refresh & Scheduling
  async triggerRefresh(workspaceId: string, connectionId: string): Promise<DataSourceImport> {
    return apiClient<DataSourceImport>(`/api/v1/connections/${connectionId}/refresh`, {
      method: 'POST',
      workspaceId,
    });
  },

  async getRefreshConfigs(workspaceId: string, connectionId: string): Promise<RefreshConfig[]> {
    return apiClient<RefreshConfig[]>(`/api/v1/connections/${connectionId}/refresh-config`, {
      method: 'GET',
      workspaceId,
    });
  },

  async createRefreshConfig(
    workspaceId: string,
    connectionId: string,
    payload: {
      frequency: 'hourly' | 'daily' | 'weekly' | 'custom_cron';
      refresh_mode: 'full' | 'incremental';
      target_resource: string;
      dataset_id?: string;
      watermark_column?: string;
      cron_expression?: string;
      timezone?: string;
      is_active?: boolean;
    }
  ): Promise<RefreshConfig> {
    return apiClient<RefreshConfig>(`/api/v1/connections/${connectionId}/refresh-config`, {
      method: 'POST',
      body: JSON.stringify(payload),
      workspaceId,
    });
  },

  // Google OAuth Helpers
  async getGoogleAuthUrl(clientId: string, redirectUri: string): Promise<{ auth_url: string; state: string }> {
    return apiClient<{ auth_url: string; state: string }>(
      `/api/v1/connections/oauth/google/auth-url?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirectUri)}`,
      { method: 'GET' }
    );
  },

  async handleGoogleCallback(
    code: string,
    clientId: string,
    clientSecret: string,
    redirectUri: string,
    state?: string
  ): Promise<any> {
    return apiClient<any>(
      `/api/v1/connections/oauth/google/callback?client_id=${encodeURIComponent(clientId)}&client_secret=${encodeURIComponent(clientSecret)}&redirect_uri=${encodeURIComponent(redirectUri)}`,
      {
        method: 'POST',
        body: JSON.stringify({ code, state }),
      }
    );
  },
};

