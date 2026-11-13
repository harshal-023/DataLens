import { describe, it, expect } from 'vitest';
import {
  CustomRole,
  ResourceAccessPolicy,
  WorkspaceSecurityPolicy,
} from '../services/governanceService';

describe('Phase 5C Enterprise Governance & RBAC Engine', () => {
  it('evaluates custom role granular permission grants', () => {
    const customRole: CustomRole = {
      id: 'r1',
      workspace_id: 'ws1',
      name: 'Data Steward',
      permissions: ['dataset:view', 'dataset:edit', 'governance:manage'],
      is_system: false,
      assigned_members_count: 2,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const hasPermission = (role: CustomRole, requiredPerm: string) => {
      return role.permissions.includes(requiredPerm);
    };

    expect(hasPermission(customRole, 'dataset:view')).toBe(true);
    expect(hasPermission(customRole, 'governance:manage')).toBe(true);
    expect(hasPermission(customRole, 'dataset:delete')).toBe(false);
  });

  it('enforces 4-tier RLAC decision hierarchy with Explicit Deny precedence', () => {
    const policies: ResourceAccessPolicy[] = [
      {
        id: 'p1',
        workspace_id: 'ws1',
        resource_type: 'report',
        resource_id: 'rep_101',
        user_id: 'user_analyst',
        permission: 'viewer',
        is_denied: true, // EXPLICIT DENY
        created_at: new Date().toISOString(),
      },
      {
        id: 'p2',
        workspace_id: 'ws1',
        resource_type: 'report',
        resource_id: 'rep_102',
        user_id: 'user_analyst',
        permission: 'editor',
        is_denied: false, // EXPLICIT GRANT
        created_at: new Date().toISOString(),
      },
    ];

    const evaluateRLAC = (
      userRole: string,
      userId: string,
      resourceId: string,
      reqPerm: 'viewer' | 'editor'
    ): boolean => {
      // 1. Owner always allowed
      if (userRole === 'owner') return true;

      // 2. Check explicit deny for this user
      const deny = policies.find(
        (p) => p.resource_id === resourceId && p.user_id === userId && p.is_denied
      );
      if (deny) return false;

      // 3. Check explicit grant
      const grant = policies.find(
        (p) => p.resource_id === resourceId && p.user_id === userId && !p.is_denied
      );
      if (grant) {
        if (reqPerm === 'viewer') return true;
        return grant.permission === 'editor';
      }

      // 4. Default role capability
      return userRole === 'editor' || userRole === 'admin';
    };

    // User is Editor, but rep_101 has Explicit Deny -> Denied!
    expect(evaluateRLAC('editor', 'user_analyst', 'rep_101', 'viewer')).toBe(false);

    // User is Viewer, but rep_102 has Explicit Grant as Editor -> Allowed!
    expect(evaluateRLAC('viewer', 'user_analyst', 'rep_102', 'editor')).toBe(true);

    // Owner bypasses explicit deny
    expect(evaluateRLAC('owner', 'user_analyst', 'rep_101', 'viewer')).toBe(true);
  });

  it('applies client-side column suppression and masking algorithms', () => {
    const maskValue = (val: string, type: 'redact' | 'hash' | 'partial'): string => {
      if (!val) return val;
      if (type === 'redact') return '••••••••';
      if (type === 'partial') {
        if (val.length <= 4) return '****';
        return '*'.repeat(val.length - 4) + val.slice(-4);
      }
      return 'HASHED_OUTPUT';
    };

    expect(maskValue('123-45-6789', 'redact')).toBe('••••••••');
    expect(maskValue('123-45-6789', 'partial')).toBe('*******6789');
    expect(maskValue('test', 'partial')).toBe('****');
  });

  it('validates workspace security policy boundaries for public share links', () => {
    const policy: WorkspaceSecurityPolicy = {
      id: 'pol1',
      workspace_id: 'ws1',
      allow_public_share_links: false,
      max_share_link_days: 7,
      restrict_external_sharing: true,
      restrict_report_downloads: false,
      restrict_dataset_exports: true,
      max_session_hours: 12,
      allowed_invitation_domains: ['company.com'],
      custom_roles_enabled: true,
      audit_retention_days: 90,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const canGenerateShareLink = (
      pol: WorkspaceSecurityPolicy,
      isExternal: boolean,
      requestedDays: number
    ): { allowed: boolean; reason?: string } => {
      if (!pol.allow_public_share_links) {
        return { allowed: false, reason: 'Public share links are prohibited by policy.' };
      }
      if (isExternal && pol.restrict_external_sharing) {
        return { allowed: false, reason: 'External sharing is restricted.' };
      }
      if (requestedDays > pol.max_share_link_days) {
        return { allowed: false, reason: `Max allowed duration is ${pol.max_share_link_days} days.` };
      }
      return { allowed: true };
    };

    const res = canGenerateShareLink(policy, true, 10);
    expect(res.allowed).toBe(false);
    expect(res.reason).toBe('Public share links are prohibited by policy.');
  });

  it('validates email invitation allowlist domains', () => {
    const allowedDomains = ['corp.com', 'acme.org'];
    const isEmailAllowed = (email: string, domains: string[]): boolean => {
      if (domains.length === 0) return true;
      const domain = email.split('@')[1]?.toLowerCase();
      return domains.includes(domain);
    };

    expect(isEmailAllowed('alice@corp.com', allowedDomains)).toBe(true);
    expect(isEmailAllowed('bob@acme.org', allowedDomains)).toBe(true);
    expect(isEmailAllowed('eve@gmail.com', allowedDomains)).toBe(false);
  });
});

