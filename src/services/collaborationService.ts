// Phase 5B Team Collaboration, Sharing, Comments, and Notifications Service Client

import { apiClient, API_BASE_URL, getAccessToken } from './apiClient';

export interface WorkspaceMember {
  user_id: string;
  full_name: string;
  email: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  joined_at: string;
}

export interface WorkspaceInvitation {
  id: string;
  workspace_id: string;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  status: 'pending' | 'accepted' | 'declined' | 'expired' | 'revoked';
  expires_at: string;
  resend_count: number;
  created_at: string;
  inviter_id?: string;
  inviter_name?: string;
  invitation_url?: string;
}

export interface InvitationPublicDetail {
  id: string;
  workspace_id: string;
  workspace_name: string;
  inviter_name: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
  is_valid: boolean;
}

export interface MemberShare {
  id: string;
  workspace_id: string;
  resource_type: 'dashboard' | 'report';
  resource_id: string;
  shared_with_user_id: string;
  shared_with_name: string;
  shared_with_email: string;
  shared_by_user_id?: string;
  permission: 'viewer' | 'editor';
  created_at: string;
}

export interface ShareAccessTokenInfo {
  id: string;
  workspace_id: string;
  resource_type: 'dashboard' | 'report';
  resource_id: string;
  permission: 'viewer' | 'editor';
  allow_download: boolean;
  has_password: boolean;
  expires_at?: string | null;
  is_revoked: boolean;
  access_count: number;
  last_accessed_at?: string | null;
  share_url: string;
  created_at: string;
}

export interface CommentItem {
  id: string;
  workspace_id: string;
  resource_type: 'dashboard' | 'report';
  resource_id: string;
  parent_id?: string | null;
  author_id: string;
  author_name: string;
  author_email: string;
  content: string;
  mentions: string[];
  is_resolved: boolean;
  resolved_by_id?: string | null;
  resolved_by_name?: string | null;
  resolved_at?: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  replies: CommentItem[];
}

export interface NotificationItem {
  id: string;
  workspace_id: string;
  recipient_id: string;
  actor_id?: string | null;
  actor_name?: string | null;
  event_type: string;
  resource_type?: string | null;
  resource_id?: string | null;
  title: string;
  message: string;
  data: Record<string, any>;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationPreferences {
  user_id: string;
  workspace_id: string;
  email_notifications: boolean;
  in_app_notifications: boolean;
  mention_notifications: boolean;
  share_notifications: boolean;
}

export interface ActivityItem {
  id: string;
  workspace_id: string;
  actor_id?: string | null;
  actor_name?: string | null;
  event_type: string;
  resource_type: string;
  resource_id?: string | null;
  summary: string;
  metadata_snapshot: Record<string, any>;
  created_at: string;
}

export interface ActivityListResponse {
  items: ActivityItem[];
  total: number;
}

export const collaborationService = {
  // ---------------------------------------------------------------------------
  // Workspace Members & Invitations
  // ---------------------------------------------------------------------------
  async listMembers(workspaceId: string): Promise<WorkspaceMember[]> {
    const res = await apiClient<{ success: boolean; data: WorkspaceMember[] }>(
      `/api/v1/workspaces/${workspaceId}/members`
    );
    return res.data;
  },

  async updateMemberRole(
    workspaceId: string,
    userId: string,
    role: string
  ): Promise<WorkspaceMember> {
    const res = await apiClient<{ success: boolean; data: WorkspaceMember }>(
      `/api/v1/workspaces/${workspaceId}/members/${userId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }
    );
    return res.data;
  },

  async removeMember(workspaceId: string, userId: string): Promise<void> {
    await apiClient(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
      method: 'DELETE',
    });
  },

  async listInvitations(workspaceId: string, status?: string): Promise<WorkspaceInvitation[]> {
    const url = status
      ? `/api/v1/workspaces/${workspaceId}/invitations?status=${status}`
      : `/api/v1/workspaces/${workspaceId}/invitations`;
    const res = await apiClient<{ success: boolean; data: WorkspaceInvitation[] }>(url);
    return res.data;
  },

  async inviteMember(
    workspaceId: string,
    email: string,
    role: string
  ): Promise<WorkspaceInvitation> {
    const res = await apiClient<{ success: boolean; data: WorkspaceInvitation }>(
      `/api/v1/workspaces/${workspaceId}/invitations`,
      {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      }
    );
    return res.data;
  },

  async resendInvitation(
    workspaceId: string,
    invitationId: string
  ): Promise<WorkspaceInvitation> {
    const res = await apiClient<{ success: boolean; data: WorkspaceInvitation }>(
      `/api/v1/workspaces/${workspaceId}/invitations/${invitationId}/resend`,
      {
        method: 'POST',
      }
    );
    return res.data;
  },

  async revokeInvitation(workspaceId: string, invitationId: string): Promise<void> {
    await apiClient(`/api/v1/workspaces/${workspaceId}/invitations/${invitationId}`, {
      method: 'DELETE',
    });
  },

  async getInvitationByToken(token: string): Promise<InvitationPublicDetail> {
    const res = await apiClient<{ success: boolean; data: InvitationPublicDetail }>(
      `/api/v1/invitations/${token}`,
      { skipAuth: true }
    );
    return res.data;
  },

  async acceptInvitation(token: string): Promise<{ workspace_id: string; workspace_name: string }> {
    const res = await apiClient<{
      success: boolean;
      data: { workspace_id: string; workspace_name: string };
    }>(`/api/v1/invitations/${token}/accept`, {
      method: 'POST',
    });
    return res.data;
  },

  async declineInvitation(token: string): Promise<void> {
    await apiClient(`/api/v1/invitations/${token}/decline`, {
      method: 'POST',
      skipAuth: true,
    });
  },

  // ---------------------------------------------------------------------------
  // Resource Sharing (Member-level)
  // ---------------------------------------------------------------------------
  async listDashboardShares(workspaceId: string, dashboardId: string): Promise<MemberShare[]> {
    const res = await apiClient<{ success: boolean; data: MemberShare[] }>(
      `/api/v1/dashboards/${dashboardId}/shares?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async shareDashboardWithMember(
    workspaceId: string,
    dashboardId: string,
    targetUserId: string,
    permission: 'viewer' | 'editor' = 'viewer'
  ): Promise<MemberShare> {
    const res = await apiClient<{ success: boolean; data: MemberShare }>(
      `/api/v1/dashboards/${dashboardId}/shares?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({ target_user_id: targetUserId, permission }),
      }
    );
    return res.data;
  },

  async revokeDashboardShare(
    workspaceId: string,
    dashboardId: string,
    shareId: string
  ): Promise<void> {
    await apiClient(
      `/api/v1/dashboards/${dashboardId}/shares/${shareId}?workspace_id=${workspaceId}`,
      {
        method: 'DELETE',
      }
    );
  },

  async listReportShares(workspaceId: string, reportId: string): Promise<MemberShare[]> {
    const res = await apiClient<{ success: boolean; data: MemberShare[] }>(
      `/api/v1/reports/${reportId}/shares?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async shareReportWithMember(
    workspaceId: string,
    reportId: string,
    targetUserId: string,
    permission: 'viewer' | 'editor' = 'viewer'
  ): Promise<MemberShare> {
    const res = await apiClient<{ success: boolean; data: MemberShare }>(
      `/api/v1/reports/${reportId}/shares?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({ target_user_id: targetUserId, permission }),
      }
    );
    return res.data;
  },

  async revokeReportShare(
    workspaceId: string,
    reportId: string,
    shareId: string
  ): Promise<void> {
    await apiClient(
      `/api/v1/reports/${reportId}/shares/${shareId}?workspace_id=${workspaceId}`,
      {
        method: 'DELETE',
      }
    );
  },

  // ---------------------------------------------------------------------------
  // Controlled Share Links
  // ---------------------------------------------------------------------------
  async listDashboardShareLinks(
    workspaceId: string,
    dashboardId: string
  ): Promise<ShareAccessTokenInfo[]> {
    const res = await apiClient<{ success: boolean; data: ShareAccessTokenInfo[] }>(
      `/api/v1/dashboards/${dashboardId}/links?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async createDashboardShareLink(
    workspaceId: string,
    dashboardId: string,
    params: {
      permission?: 'viewer' | 'editor';
      allow_download?: boolean;
      expires_in_days?: number;
      password?: string;
    }
  ): Promise<ShareAccessTokenInfo> {
    const res = await apiClient<{ success: boolean; data: ShareAccessTokenInfo }>(
      `/api/v1/dashboards/${dashboardId}/links?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({
          permission: params.permission || 'viewer',
          allow_download: params.allow_download ?? true,
          expires_in_days: params.expires_in_days,
          password: params.password,
        }),
      }
    );
    return res.data;
  },

  async revokeDashboardShareLink(
    workspaceId: string,
    dashboardId: string,
    tokenId: string
  ): Promise<void> {
    await apiClient(
      `/api/v1/dashboards/${dashboardId}/links/${tokenId}?workspace_id=${workspaceId}`,
      {
        method: 'DELETE',
      }
    );
  },

  async listReportShareLinks(
    workspaceId: string,
    reportId: string
  ): Promise<ShareAccessTokenInfo[]> {
    const res = await apiClient<{ success: boolean; data: ShareAccessTokenInfo[] }>(
      `/api/v1/reports/${reportId}/links?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async createReportShareLink(
    workspaceId: string,
    reportId: string,
    params: {
      allow_download?: boolean;
      expires_in_days?: number;
      password?: string;
    }
  ): Promise<ShareAccessTokenInfo> {
    const res = await apiClient<{ success: boolean; data: ShareAccessTokenInfo }>(
      `/api/v1/reports/${reportId}/links?workspace_id=${workspaceId}`,
      {
        method: 'POST',
        body: JSON.stringify({
          permission: 'viewer',
          allow_download: params.allow_download ?? true,
          expires_in_days: params.expires_in_days,
          password: params.password,
        }),
      }
    );
    return res.data;
  },

  async revokeReportShareLink(
    workspaceId: string,
    reportId: string,
    tokenId: string
  ): Promise<void> {
    await apiClient(
      `/api/v1/reports/${reportId}/links/${tokenId}?workspace_id=${workspaceId}`,
      {
        method: 'DELETE',
      }
    );
  },

  async duplicateDashboard(
    dashboardId: string,
    targetWorkspaceId: string,
    newTitle?: string
  ): Promise<{ id: string; name: string; workspace_id: string }> {
    const res = await apiClient<{
      success: boolean;
      data: { id: string; name: string; workspace_id: string };
    }>(`/api/v1/dashboards/${dashboardId}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({
        target_workspace_id: targetWorkspaceId,
        new_title: newTitle,
      }),
    });
    return res.data;
  },

  async resolvePublicDashboard(token: string, password?: string): Promise<any> {
    const res = await apiClient<{ success: boolean; data: any }>(
      `/api/v1/shared/dashboards/${token}`,
      {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ password }),
      }
    );
    return res.data;
  },

  // ---------------------------------------------------------------------------
  // Comments & Discussions
  // ---------------------------------------------------------------------------
  async listComments(
    workspaceId: string,
    resourceType: 'dashboard' | 'report',
    resourceId: string
  ): Promise<CommentItem[]> {
    const res = await apiClient<{ success: boolean; data: CommentItem[] }>(
      `/api/v1/comments?workspace_id=${workspaceId}&resource_type=${resourceType}&resource_id=${resourceId}`
    );
    return res.data;
  },

  async createComment(params: {
    workspaceId: string;
    resourceType: 'dashboard' | 'report';
    resourceId: string;
    content: string;
    parentId?: string;
  }): Promise<CommentItem> {
    const res = await apiClient<{ success: boolean; data: CommentItem }>(`/api/v1/comments`, {
      method: 'POST',
      body: JSON.stringify({
        workspace_id: params.workspaceId,
        resource_type: params.resourceType,
        resource_id: params.resourceId,
        content: params.content,
        parent_id: params.parentId,
      }),
    });
    return res.data;
  },

  async updateComment(commentId: string, content: string): Promise<CommentItem> {
    const res = await apiClient<{ success: boolean; data: CommentItem }>(
      `/api/v1/comments/${commentId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ content }),
      }
    );
    return res.data;
  },

  async deleteComment(commentId: string): Promise<void> {
    await apiClient(`/api/v1/comments/${commentId}`, {
      method: 'DELETE',
    });
  },

  async resolveDiscussion(commentId: string): Promise<CommentItem> {
    const res = await apiClient<{ success: boolean; data: CommentItem }>(
      `/api/v1/comments/${commentId}/resolve`,
      {
        method: 'POST',
      }
    );
    return res.data;
  },

  async reopenDiscussion(commentId: string): Promise<CommentItem> {
    const res = await apiClient<{ success: boolean; data: CommentItem }>(
      `/api/v1/comments/${commentId}/reopen`,
      {
        method: 'POST',
      }
    );
    return res.data;
  },

  // ---------------------------------------------------------------------------
  // Notifications
  // ---------------------------------------------------------------------------
  async listNotifications(
    workspaceId: string,
    unreadOnly = false,
    limit = 50,
    offset = 0
  ): Promise<NotificationItem[]> {
    const res = await apiClient<{ success: boolean; data: NotificationItem[] }>(
      `/api/v1/notifications?workspace_id=${workspaceId}&unread_only=${unreadOnly}&limit=${limit}&offset=${offset}`
    );
    return res.data;
  },

  async getUnreadCount(workspaceId: string): Promise<number> {
    const res = await apiClient<{ success: boolean; data: { unread_count: number } }>(
      `/api/v1/notifications/unread-count?workspace_id=${workspaceId}`
    );
    return res.data.unread_count;
  },

  async markNotificationRead(notificationId: string): Promise<void> {
    await apiClient(`/api/v1/notifications/${notificationId}/read`, {
      method: 'PATCH',
    });
  },

  async markAllNotificationsRead(workspaceId: string): Promise<void> {
    await apiClient(`/api/v1/notifications/mark-all-read?workspace_id=${workspaceId}`, {
      method: 'POST',
    });
  },

  async dismissNotification(notificationId: string): Promise<void> {
    await apiClient(`/api/v1/notifications/${notificationId}`, {
      method: 'DELETE',
    });
  },

  async getNotificationPreferences(workspaceId: string): Promise<NotificationPreferences> {
    const res = await apiClient<{ success: boolean; data: NotificationPreferences }>(
      `/api/v1/notifications/preferences?workspace_id=${workspaceId}`
    );
    return res.data;
  },

  async updateNotificationPreferences(
    workspaceId: string,
    prefs: Partial<NotificationPreferences>
  ): Promise<NotificationPreferences> {
    const res = await apiClient<{ success: boolean; data: NotificationPreferences }>(
      `/api/v1/notifications/preferences?workspace_id=${workspaceId}`,
      {
        method: 'PUT',
        body: JSON.stringify(prefs),
      }
    );
    return res.data;
  },

  createNotificationSource(onMessage: (notification: any) => void): () => void {
    const token = getAccessToken();
    const url = `${API_BASE_URL}/api/v1/notifications/stream${
      token ? `?access_token=${token}` : ''
    }`;

    // EventSource doesn't support custom Authorization headers directly in standard browser API,
    // so we support SSE connection or fallback to polling interval
    let es: EventSource | null = null;
    let pollInterval: any = null;

    try {
      es = new EventSource(url, { withCredentials: true });
      es.addEventListener('notification', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          onMessage(data);
        } catch {
          // ignore parse errors
        }
      });
      es.onerror = () => {
        // SSE error, degrade gracefully
      };
    } catch {
      // Fallback
    }

    return () => {
      if (es) {
        es.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  },

  // ---------------------------------------------------------------------------
  // Workspace Activity
  // ---------------------------------------------------------------------------
  async getWorkspaceActivity(
    workspaceId: string,
    params?: {
      actorId?: string;
      resourceType?: string;
      eventType?: string;
      page?: number;
      pageSize?: number;
    }
  ): Promise<ActivityListResponse> {
    const query = new URLSearchParams();
    if (params?.actorId) query.append('actor_id', params.actorId);
    if (params?.resourceType) query.append('resource_type', params.resourceType);
    if (params?.eventType) query.append('event_type', params.eventType);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.pageSize) query.append('page_size', params.pageSize.toString());

    const queryString = query.toString();
    const url = `/api/v1/workspaces/${workspaceId}/activity${
      queryString ? `?${queryString}` : ''
    }`;

    const res = await apiClient<{ success: boolean; data: ActivityListResponse }>(url);
    return res.data;
  },
};

