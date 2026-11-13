// Phase 5C Enterprise Governance, Advanced RBAC, and Security Audit API Service Client

import { apiClient, API_BASE_URL } from './apiClient';

export interface PermissionDefinition {
  code: string;
  category: string;
  name: string;
  description: string;
}

export interface PermissionsCatalog {
  permissions: PermissionDefinition[];
  categories: string[];
}

export interface CustomRole {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  permissions: string[];
  is_system: boolean;
  assigned_members_count: number;
  created_at: string;
  updated_at: string;
}

export interface ResourceAccessPolicy {
  id: string;
  workspace_id: string;
  resource_type: string;
  resource_id: string;
  user_id?: string | null;
  user_name?: string | null;
  user_email?: string | null;
  role_id?: string | null;
  role_name?: string | null;
  permission: 'viewer' | 'editor' | 'admin';
  is_denied: boolean;
  created_at: string;
}

export interface ColumnMaskRule {
  type: 'redact' | 'hash' | 'partial';
  clearance_roles?: string[];
}

export interface DatasetGovernance {
  id: string;
  workspace_id: string;
  dataset_id: string;
  dataset_name?: string | null;
  sensitivity_level: 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED';
  export_restricted: boolean;
  column_masks: Record<string, ColumnMaskRule>;
  approved_by?: string | null;
  approved_by_name?: string | null;
  approved_at?: string | null;
  updated_at: string;
}

export interface EnterpriseAuditLog {
  id: string;
  workspace_id?: string | null;
  actor_id?: string | null;
  actor_email?: string | null;
  actor_name?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  timestamp: string;
  ip_address?: string | null;
  user_agent?: string | null;
  correlation_id?: string | null;
  outcome: 'SUCCESS' | 'FAILURE' | 'DENIED';
  metadata_snapshot: Record<string, any>;
  previous_hash?: string | null;
  chained_hash: string;
  is_chain_valid?: boolean;
}

export interface AuditLogListResponse {
  items: EnterpriseAuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface SecurityEvent {
  id: string;
  workspace_id?: string | null;
  event_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  details: Record<string, any>;
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'FALSE_POSITIVE';
  resolved_by?: string | null;
  resolved_by_name?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

export interface UserSession {
  id: string;
  user_id: string;
  ip_address?: string | null;
  user_agent?: string | null;
  device_label?: string | null;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  is_current: boolean;
  is_revoked: boolean;
}

export interface WorkspaceSecurityPolicy {
  id: string;
  workspace_id: string;
  allow_public_share_links: boolean;
  max_share_link_days: number;
  restrict_external_sharing: boolean;
  restrict_report_downloads: boolean;
  restrict_dataset_exports: boolean;
  max_session_hours: number;
  allowed_invitation_domains: string[];
  custom_roles_enabled: boolean;
  audit_retention_days: number;
  created_at: string;
  updated_at: string;
}

export const governanceService = {
  // ---------------------------------------------------------------------------
  // Permissions & Custom Roles
  // ---------------------------------------------------------------------------
  async getPermissionsCatalog(): Promise<PermissionsCatalog> {
    const res = await apiClient<{ success: boolean; data: PermissionsCatalog }>(
      '/api/v1/permissions/catalog'
    );
    return res.data;
  },

  async listRoles(workspaceId: string): Promise<CustomRole[]> {
    const res = await apiClient<{ success: boolean; data: CustomRole[] }>(
      `/api/v1/roles?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async createRole(
    workspaceId: string,
    params: { name: string; description?: string; permissions: string[] }
  ): Promise<CustomRole> {
    const res = await apiClient<{ success: boolean; data: CustomRole }>(
      `/api/v1/roles?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
    return res.data;
  },

  async updateRole(
    workspaceId: string,
    roleId: string,
    params: { name?: string; description?: string; permissions?: string[] }
  ): Promise<CustomRole> {
    const res = await apiClient<{ success: boolean; data: CustomRole }>(
      `/api/v1/roles/${roleId}?workspace_id=${workspaceId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(params),
      }
    );
    return res.data;
  },

  async duplicateRole(
    workspaceId: string,
    roleId: string,
    newName: string
  ): Promise<CustomRole> {
    const res = await apiClient<{ success: boolean; data: CustomRole }>(
      `/api/v1/roles/${roleId}/duplicate?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({ new_name: newName }),
      }
    );
    return res.data;
  },

  async deleteRole(workspaceId: string, roleId: string): Promise<void> {
    await apiClient(`/api/v1/roles/${roleId}?workspace_id=${workspaceId}`, {
      method: 'DELETE',
    });
  },

  async assignCustomRole(
    workspaceId: string,
    targetUserId: string,
    customRoleId: string | null
  ): Promise<void> {
    const query = customRoleId ? `&custom_role_id=${customRoleId}` : '';
    await apiClient(
      `/api/v1/roles/assign?workspace_id=${workspaceId}&target_user_id=${targetUserId}${query}`,
      {
        method: 'POST',
      }
    );
  },

  // ---------------------------------------------------------------------------
  // Resource Access Policies (RLAC)
  // ---------------------------------------------------------------------------
  async listResourcePolicies(
    workspaceId: string,
    resourceType: string,
    resourceId: string
  ): Promise<ResourceAccessPolicy[]> {
    const res = await apiClient<{ success: boolean; data: ResourceAccessPolicy[] }>(
      `/api/v1/permissions/resources?workspace_id=${workspaceId}&resource_type=${resourceType}&resource_id=${resourceId}`
    );
    return res.data;
  },

  async createResourcePolicy(
    workspaceId: string,
    params: {
      resource_type: string;
      resource_id: string;
      user_id?: string;
      role_id?: string;
      permission: 'viewer' | 'editor' | 'admin';
      is_denied: boolean;
    }
  ): Promise<ResourceAccessPolicy> {
    const res = await apiClient<{ success: boolean; data: ResourceAccessPolicy }>(
      `/api/v1/permissions/resources?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
    return res.data;
  },

  async deleteResourcePolicy(workspaceId: string, policyId: string): Promise<void> {
    await apiClient(
      `/api/v1/permissions/resources/${policyId}?workspace_id=${workspaceId}`,
      {
        method: 'DELETE',
      }
    );
  },

  // ---------------------------------------------------------------------------
  // Data Governance & Column Masking
  // ---------------------------------------------------------------------------
  async getDatasetGovernance(
    workspaceId: string,
    datasetId: string
  ): Promise<DatasetGovernance> {
    const res = await apiClient<{ success: boolean; data: DatasetGovernance }>(
      `/api/v1/governance/datasets/${datasetId}?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async updateDatasetGovernance(
    workspaceId: string,
    datasetId: string,
    params: {
      sensitivity_level: 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED';
      export_restricted: boolean;
      column_masks: Record<string, ColumnMaskRule>;
    }
  ): Promise<DatasetGovernance> {
    const res = await apiClient<{ success: boolean; data: DatasetGovernance }>(
      `/api/v1/governance/datasets/${datasetId}?workspace_id=${workspaceId}`,
      {
        method: 'PUT',
        body: JSON.stringify(params),
      }
    );
    return res.data;
  },

  // ---------------------------------------------------------------------------
  // Enterprise Audit Logs
  // ---------------------------------------------------------------------------
  async listAuditLogs(
    workspaceId: string,
    params?: {
      actorId?: string;
      action?: string;
      resourceType?: string;
      outcome?: string;
      page?: number;
      pageSize?: number;
    }
  ): Promise<AuditLogListResponse> {
    const query = new URLSearchParams();
    query.append('workspace_id', workspaceId);
    if (params?.actorId) query.append('actor_id', params.actorId);
    if (params?.action) query.append('action', params.action);
    if (params?.resourceType) query.append('resource_type', params.resourceType);
    if (params?.outcome) query.append('outcome', params.outcome);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.pageSize) query.append('page_size', params.pageSize.toString());

    const res = await apiClient<{ success: boolean; data: AuditLogListResponse }>(
      `/api/v1/audit-logs?${query.toString()}`
    );
    return res.data;
  },

  getAuditExportUrl(workspaceId: string): string {
    return `${API_BASE_URL}/api/v1/audit-logs/export?workspace_id=${workspaceId}`;
  },

  // ---------------------------------------------------------------------------
  // Security Incident Events
  // ---------------------------------------------------------------------------
  async listSecurityEvents(
    workspaceId: string,
    params?: { status?: string; severity?: string }
  ): Promise<SecurityEvent[]> {
    const query = new URLSearchParams();
    query.append('workspace_id', workspaceId);
    if (params?.status) query.append('status', params.status);
    if (params?.severity) query.append('severity', params.severity);

    const res = await apiClient<{ success: boolean; data: SecurityEvent[] }>(
      `/api/v1/security-events?${query.toString()}`
    );
    return res.data;
  },

  async updateSecurityEventStatus(
    workspaceId: string,
    eventId: string,
    status: 'INVESTIGATING' | 'RESOLVED' | 'FALSE_POSITIVE',
    notes?: string
  ): Promise<SecurityEvent> {
    const res = await apiClient<{ success: boolean; data: SecurityEvent }>(
      `/api/v1/security-events/${eventId}?workspace_id=${workspaceId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status, notes }),
      }
    );
    return res.data;
  },

  // ---------------------------------------------------------------------------
  // Active User Sessions
  // ---------------------------------------------------------------------------
  async listSessions(): Promise<UserSession[]> {
    const res = await apiClient<{ success: boolean; data: UserSession[] }>(
      '/api/v1/sessions'
    );
    return res.data;
  },

  async revokeSession(sessionId: string): Promise<void> {
    await apiClient(`/api/v1/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  },

  async revokeAllOtherSessions(): Promise<number> {
    const res = await apiClient<{
      success: boolean;
      data: { revoked_count: number };
    }>('/api/v1/sessions/revoke-others', {
      method: 'POST',
    });
    return res.data.revoked_count;
  },

  // ---------------------------------------------------------------------------
  // Workspace Security Policies
  // ---------------------------------------------------------------------------
  async getSecurityPolicy(workspaceId: string): Promise<WorkspaceSecurityPolicy> {
    const res = await apiClient<{ success: boolean; data: WorkspaceSecurityPolicy }>(
      `/api/v1/workspace-security?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async updateSecurityPolicy(
    workspaceId: string,
    params: Partial<WorkspaceSecurityPolicy>
  ): Promise<WorkspaceSecurityPolicy> {
    const res = await apiClient<{ success: boolean; data: WorkspaceSecurityPolicy }>(
      `/api/v1/workspace-security?workspace_id=${workspaceId}`,
      {
        method: 'PUT',
        body: JSON.stringify(params),
      }
    );
    return res.data;
  },
};
