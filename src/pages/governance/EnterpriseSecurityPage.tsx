import React, { useState, useEffect } from 'react';
import {
  Shield,
  Key,
  FileText,
  AlertTriangle,
  Laptop,
  Database,
  Sliders,
  Plus,
  Copy,
  Trash2,
  Edit2,
  Check,
  Search,
  Filter,
  Download,
  Lock,
  Eye,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Globe,
  Building,
} from 'lucide-react';
import {
  governanceService,
  CustomRole,
  PermissionDefinition,
  EnterpriseAuditLog,
  SecurityEvent,
  UserSession,
  DatasetGovernance,
  WorkspaceSecurityPolicy,
} from '../../services/governanceService';
import { useAuth } from '../../context/AuthContext';
import { StorageService } from '../../services/storageService';

export const EnterpriseSecurityPage: React.FC = () => {
  const { currentWorkspace, user } = useAuth();
  const workspaceId = currentWorkspace?.id;

  const [activeTab, setActiveTab] = useState<
    'roles' | 'audit' | 'security_events' | 'sessions' | 'governance' | 'policies'
  >('roles');

  // Roles & Permissions state
  const [roles, setRoles] = useState<CustomRole[]>([]);
  const [catalog, setCatalog] = useState<PermissionDefinition[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<CustomRole | null>(null);
  const [roleName, setRoleName] = useState('');
  const [roleDesc, setRoleDesc] = useState('');
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);

  // Audit Logs state
  const [auditLogs, setAuditLogs] = useState<EnterpriseAuditLog[]>([]);
  const [totalLogs, setTotalLogs] = useState(0);
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditOutcomeFilter, setAuditOutcomeFilter] = useState('');
  const [auditSearch, setAuditSearch] = useState('');

  // Security Events state
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);

  // Active Sessions state
  const [sessions, setSessions] = useState<UserSession[]>([]);

  // Data Governance state
  const datasets = StorageService.getDatasets();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(
    datasets.length > 0 ? datasets[0].id : ''
  );
  const [governance, setGovernance] = useState<DatasetGovernance | null>(null);
  const [sensitivity, setSensitivity] = useState<'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED'>('INTERNAL');
  const [exportRestricted, setExportRestricted] = useState(false);
  const [newMaskCol, setNewMaskCol] = useState('');
  const [newMaskType, setNewMaskType] = useState<'redact' | 'hash' | 'partial'>('redact');

  // Security Policies state
  const [policy, setPolicy] = useState<WorkspaceSecurityPolicy | null>(null);
  const [policySaved, setPolicySaved] = useState(false);

  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  // Load section data
  const loadTabContent = async () => {
    if (!workspaceId) return;
    setLoading(true);
    try {
      if (activeTab === 'roles') {
        const [rolesData, catalogData] = await Promise.all([
          governanceService.listRoles(workspaceId),
          governanceService.getPermissionsCatalog(),
        ]);
        setRoles(rolesData);
        setCatalog(catalogData.permissions);
        setCategories(catalogData.categories);
      } else if (activeTab === 'audit') {
        const res = await governanceService.listAuditLogs(workspaceId, {
          action: auditActionFilter || undefined,
          outcome: auditOutcomeFilter || undefined,
          pageSize: 50,
        });
        setAuditLogs(res.items);
        setTotalLogs(res.total);
      } else if (activeTab === 'security_events') {
        const evts = await governanceService.listSecurityEvents(workspaceId);
        setSecurityEvents(evts);
      } else if (activeTab === 'sessions') {
        const sess = await governanceService.listSessions();
        setSessions(sess);
      } else if (activeTab === 'governance') {
        if (selectedDatasetId) {
          const gov = await governanceService.getDatasetGovernance(workspaceId, selectedDatasetId);
          setGovernance(gov);
          setSensitivity(gov.sensitivity_level);
          setExportRestricted(gov.export_restricted);
        }
      } else if (activeTab === 'policies') {
        const pol = await governanceService.getSecurityPolicy(workspaceId);
        setPolicy(pol);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTabContent();
  }, [workspaceId, activeTab, selectedDatasetId, auditActionFilter, auditOutcomeFilter]);

  // Show temporary toast
  const triggerToast = (msg: string) => {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(null), 3000);
  };

  // Roles operations
  const handleSaveRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || !roleName.trim()) return;

    try {
      if (editingRole) {
        await governanceService.updateRole(workspaceId, editingRole.id, {
          name: roleName.trim(),
          description: roleDesc,
          permissions: selectedPermissions,
        });
        triggerToast('Role updated successfully.');
      } else {
        await governanceService.createRole(workspaceId, {
          name: roleName.trim(),
          description: roleDesc,
          permissions: selectedPermissions,
        });
        triggerToast('Custom role created.');
      }
      setIsRoleModalOpen(false);
      setEditingRole(null);
      setRoleName('');
      setRoleDesc('');
      setSelectedPermissions([]);
      loadTabContent();
    } catch (err: any) {
      alert(err.message || 'Failed to save role');
    }
  };

  const handleDuplicateRole = async (role: CustomRole) => {
    if (!workspaceId) return;
    try {
      await governanceService.duplicateRole(workspaceId, role.id, `${role.name} (Copy)`);
      triggerToast('Role duplicated successfully.');
      loadTabContent();
    } catch (err: any) {
      alert(err.message || 'Failed to duplicate role');
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    if (!workspaceId) return;
    if (!confirm('Are you sure you want to delete this custom role? Members will fallback to Viewer.')) return;
    try {
      await governanceService.deleteRole(workspaceId, roleId);
      triggerToast('Role deleted.');
      loadTabContent();
    } catch (err: any) {
      alert(err.message || 'Failed to delete role');
    }
  };

  // Data Governance save
  const handleSaveGovernance = async () => {
    if (!workspaceId || !selectedDatasetId || !governance) return;
    try {
      await governanceService.updateDatasetGovernance(workspaceId, selectedDatasetId, {
        sensitivity_level: sensitivity,
        export_restricted: exportRestricted,
        column_masks: governance.column_masks,
      });
      triggerToast('Data governance settings updated.');
    } catch (err: any) {
      alert(err.message || 'Failed to update governance');
    }
  };

  const handleAddColumnMask = () => {
    if (!newMaskCol.trim() || !governance) return;
    const updatedMasks = {
      ...governance.column_masks,
      [newMaskCol.trim()]: { type: newMaskType, clearance_roles: ['owner', 'admin'] },
    };
    setGovernance({ ...governance, column_masks: updatedMasks });
    setNewMaskCol('');
  };

  const handleRemoveColumnMask = (colName: string) => {
    if (!governance) return;
    const copy = { ...governance.column_masks };
    delete copy[colName];
    setGovernance({ ...governance, column_masks: copy });
  };

  // Sessions operations
  const handleRevokeSession = async (sessionId: string) => {
    try {
      await governanceService.revokeSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      triggerToast('Session revoked.');
    } catch (err: any) {
      alert(err.message || 'Failed to revoke session');
    }
  };

  const handleRevokeOtherSessions = async () => {
    if (!confirm('Are you sure you want to sign out of all other active devices?')) return;
    try {
      const count = await governanceService.revokeAllOtherSessions();
      triggerToast(`Signed out of ${count} other sessions.`);
      loadTabContent();
    } catch (err: any) {
      alert(err.message || 'Failed to revoke sessions');
    }
  };

  // Security Policies save
  const handleSavePolicy = async () => {
    if (!workspaceId || !policy) return;
    try {
      await governanceService.updateSecurityPolicy(workspaceId, policy);
      setPolicySaved(true);
      setTimeout(() => setPolicySaved(false), 2500);
    } catch (err: any) {
      alert(err.message || 'Failed to save security policy');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-[#102C46] text-white rounded-2xl shadow-sm">
            <Shield className="w-6 h-6 text-[#009F98]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#102C46]">Enterprise Governance & Security</h1>
            <p className="text-sm text-[#52616C]">
              Access governance, custom RBAC permissions, chained audit trails, and workspace security policies.
            </p>
          </div>
        </div>

        {actionMsg && (
          <div className="px-4 py-2 bg-[#DCFCE7] text-[#16A34A] rounded-xl text-xs font-semibold flex items-center gap-2 animate-in fade-in">
            <Check className="w-4 h-4" /> {actionMsg}
          </div>
        )}
      </div>

      {/* Navigation Tabs Bar */}
      <div className="flex border-b border-[#DCE5EB] space-x-2 bg-white px-2 pt-2 rounded-t-2xl shadow-2xs">
        {[
          { id: 'roles', label: 'Roles & Permissions', icon: Key },
          { id: 'audit', label: 'Audit Log Explorer', icon: FileText },
          { id: 'security_events', label: 'Security Incidents', icon: AlertTriangle },
          { id: 'sessions', label: 'Active Sessions', icon: Laptop },
          { id: 'governance', label: 'Data Governance', icon: Database },
          { id: 'policies', label: 'Security Policies', icon: Sliders },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                isActive
                  ? 'border-[#009F98] text-[#009F98] bg-[#F0F9F9] rounded-t-xl'
                  : 'border-transparent text-[#52616C] hover:text-[#102C46] hover:bg-[#F8FAFC]'
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Content Sections */}
      <div className="bg-white rounded-b-2xl shadow-elevated border border-[#DCE5EB] p-6 min-h-[60vh]">
        {/* TAB A: ROLES & PERMISSIONS */}
        {activeTab === 'roles' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[#102C46]">Workspace Roles</h3>
                <p className="text-xs text-[#52616C]">
                  Configure system roles and define custom roles with granular access permissions.
                </p>
              </div>
              <button
                onClick={() => {
                  setEditingRole(null);
                  setRoleName('');
                  setRoleDesc('');
                  setSelectedPermissions([]);
                  setIsRoleModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Create Custom Role
              </button>
            </div>

            {/* System Roles Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { name: 'Owner', desc: 'Universal workspace authority, billing & configuration.' },
                { name: 'Admin', desc: 'Member management, connections & asset administration.' },
                { name: 'Editor', desc: 'Create, edit & share dashboards, reports & datasets.' },
                { name: 'Viewer', desc: 'Read-only asset inspection and discussion access.' },
              ].map((sys) => (
                <div key={sys.name} className="p-4 rounded-xl border border-[#DCE5EB] bg-[#F8FAFC] space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#102C46] text-xs">{sys.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#102C46] text-white font-bold">
                      SYSTEM
                    </span>
                  </div>
                  <p className="text-[11px] text-[#52616C]">{sys.desc}</p>
                </div>
              ))}
            </div>

            {/* Custom Roles Table */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#52616C]">
                Custom Roles ({roles.length})
              </h4>
              <div className="border border-[#DCE5EB] rounded-xl overflow-hidden divide-y divide-[#EEF3F6]">
                {roles.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[#52616C]">
                    No custom roles defined yet. Create your first tailored role above!
                  </div>
                ) : (
                  roles.map((r) => (
                    <div key={r.id} className="p-4 flex items-center justify-between hover:bg-[#F8FAFC] transition-colors">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-[#102C46]">{r.name}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#EDF7FA] text-[#009F98] font-semibold">
                            {r.assigned_members_count} members assigned
                          </span>
                        </div>
                        <p className="text-[11px] text-[#52616C]">{r.description || 'No description provided.'}</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {r.permissions.map((p) => (
                            <span key={p} className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 font-mono">
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDuplicateRole(r)}
                          className="p-1.5 text-[#52616C] hover:text-[#102C46] hover:bg-gray-100 rounded-lg cursor-pointer"
                          title="Duplicate Role"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingRole(r);
                            setRoleName(r.name);
                            setRoleDesc(r.description || '');
                            setSelectedPermissions(r.permissions);
                            setIsRoleModalOpen(true);
                          }}
                          className="p-1.5 text-[#009F98] hover:bg-[#EDF7FA] rounded-lg cursor-pointer"
                          title="Edit Permissions"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteRole(r.id)}
                          className="p-1.5 text-[#A63838] hover:bg-red-50 rounded-lg cursor-pointer"
                          title="Delete Role"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB B: AUDIT LOG EXPLORER */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[#102C46]">Enterprise Audit Log Explorer</h3>
                <p className="text-xs text-[#52616C]">
                  Cryptographically chained audit trail logging all mutations with zero secret leakage.
                </p>
              </div>

              <a
                href={governanceService.getAuditExportUrl(workspaceId || '')}
                download
                className="flex items-center gap-1.5 px-3 py-2 border border-[#DCE5EB] bg-white rounded-xl text-xs font-semibold text-[#102C46] hover:bg-[#F8FAFC]"
              >
                <Download className="w-3.5 h-3.5 text-[#009F98]" /> Export CSV
              </a>
            </div>

            {/* Filter Bar */}
            <div className="flex flex-wrap items-center gap-3 p-3 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] text-xs">
              <Filter className="w-4 h-4 text-[#009F98]" />
              <select
                value={auditOutcomeFilter}
                onChange={(e) => setAuditOutcomeFilter(e.target.value)}
                className="p-1.5 border border-[#DCE5EB] rounded-lg bg-white"
              >
                <option value="">All Outcomes</option>
                <option value="SUCCESS">Success</option>
                <option value="DENIED">Denied</option>
                <option value="FAILURE">Failure</option>
              </select>

              <input
                type="text"
                placeholder="Filter by action (e.g. dataset, role)..."
                value={auditActionFilter}
                onChange={(e) => setAuditActionFilter(e.target.value)}
                className="p-1.5 border border-[#DCE5EB] rounded-lg bg-white flex-1 min-w-[200px]"
              />

              <button
                onClick={() => {
                  setAuditOutcomeFilter('');
                  setAuditActionFilter('');
                }}
                className="text-[#009F98] text-[11px] font-semibold hover:underline"
              >
                Reset
              </button>
            </div>

            {/* Audit Table */}
            <div className="border border-[#DCE5EB] rounded-xl overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAFC] text-[#52616C] uppercase text-[10px] font-bold border-b border-[#DCE5EB]">
                  <tr>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Resource</th>
                    <th className="py-3 px-4">Outcome</th>
                    <th className="py-3 px-4">Chained Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EEF3F6]">
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-[#52616C]">
                        No audit events recorded matching current filters.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-[#F8FAFC] transition-colors">
                        <td className="py-3 px-4 text-[#8A9BA8] whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })}
                        </td>
                        <td className="py-3 px-4 font-semibold text-[#102C46]">
                          {log.actor_name || log.actor_email || 'System'}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-[11px] text-[#009F98]">{log.action}</span>
                        </td>
                        <td className="py-3 px-4 text-[#52616C]">
                          {log.resource_type}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              log.outcome === 'SUCCESS'
                                ? 'bg-green-100 text-green-700'
                                : log.outcome === 'DENIED'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-amber-100 text-amber-700'
                            }`}
                          >
                            {log.outcome}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[10px] text-gray-500 truncate max-w-[140px]" title={log.chained_hash}>
                          {log.chained_hash.substring(0, 16)}...
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB C: SECURITY INCIDENTS */}
        {activeTab === 'security_events' && (
          <div className="space-y-4">
            <div>
              <h3 className="text-base font-bold text-[#102C46]">Security Incidents & Anomaly Monitoring</h3>
              <p className="text-xs text-[#52616C]">
                Monitors suspicious authentication bursts, repeated permission failures, and anomalous exports.
              </p>
            </div>

            <div className="space-y-3">
              {securityEvents.length === 0 ? (
                <div className="p-12 text-center text-xs text-[#52616C] border border-[#DCE5EB] rounded-2xl">
                  <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
                  No security incidents or anomalies detected. System status healthy.
                </div>
              ) : (
                securityEvents.map((evt) => (
                  <div key={evt.id} className="p-4 rounded-xl border border-[#DCE5EB] bg-white flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            evt.severity === 'CRITICAL'
                              ? 'bg-red-600 text-white'
                              : evt.severity === 'HIGH'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}
                        >
                          {evt.severity}
                        </span>
                        <span className="font-bold text-xs text-[#102C46]">{evt.event_type}</span>
                        <span className="text-[10px] text-[#8A9BA8]">
                          {new Date(evt.created_at).toLocaleString()}
                        </span>
                      </div>
                      <pre className="text-[11px] font-mono bg-gray-50 p-2 rounded text-gray-700">
                        {JSON.stringify(evt.details, null, 2)}
                      </pre>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        value={evt.status}
                        onChange={async (e) => {
                          await governanceService.updateSecurityEventStatus(
                            workspaceId || '',
                            evt.id,
                            e.target.value as any
                          );
                          loadTabContent();
                        }}
                        className="text-xs p-1.5 border border-[#DCE5EB] rounded-lg bg-white"
                      >
                        <option value="OPEN">Open</option>
                        <option value="INVESTIGATING">Investigating</option>
                        <option value="RESOLVED">Resolved</option>
                        <option value="FALSE_POSITIVE">False Positive</option>
                      </select>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB D: ACTIVE SESSIONS */}
        {activeTab === 'sessions' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[#102C46]">Active User Sessions</h3>
                <p className="text-xs text-[#52616C]">
                  View and manage signed-in devices. Revoke unrecognized or inactive sessions.
                </p>
              </div>

              <button
                onClick={handleRevokeOtherSessions}
                className="px-3 py-2 bg-red-50 text-[#A63838] border border-red-200 text-xs font-semibold rounded-xl hover:bg-red-100 transition-colors"
              >
                Sign Out of All Other Sessions
              </button>
            </div>

            <div className="border border-[#DCE5EB] rounded-xl divide-y divide-[#EEF3F6]">
              {sessions.map((sess) => (
                <div key={sess.id} className="p-4 flex items-center justify-between hover:bg-[#F8FAFC]">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-[#EDF7FA] text-[#009F98] rounded-xl">
                      <Laptop className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-[#102C46]">
                          {sess.device_label || 'Web Browser'}
                        </span>
                        {sess.is_current && (
                          <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[10px] font-bold">
                            Current Device
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#52616C]">
                        IP: {sess.ip_address || '127.0.0.1'} • Last active{' '}
                        {new Date(sess.last_activity_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                  </div>

                  {!sess.is_current && (
                    <button
                      onClick={() => handleRevokeSession(sess.id)}
                      className="text-xs text-[#A63838] hover:underline font-semibold"
                    >
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB E: DATA GOVERNANCE */}
        {activeTab === 'governance' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-bold text-[#102C46]">Data Access Governance & Column Masking</h3>
              <p className="text-xs text-[#52616C]">
                Classify sensitivity tiers and configure column-level suppression and cryptographic masking.
              </p>
            </div>

            {/* Select Dataset */}
            <div className="flex items-center gap-4">
              <label className="text-xs font-bold text-[#102C46]">Select Dataset:</label>
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="text-xs p-2 border border-[#DCE5EB] rounded-xl bg-white min-w-[240px]"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            {governance && (
              <div className="space-y-4 p-5 bg-[#F8FAFC] rounded-2xl border border-[#DCE5EB]">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-[#102C46] block mb-1">
                      Sensitivity Classification
                    </label>
                    <select
                      value={sensitivity}
                      onChange={(e) => setSensitivity(e.target.value as any)}
                      className="w-full text-xs p-2 border border-[#DCE5EB] rounded-xl bg-white"
                    >
                      <option value="PUBLIC">Public - Open access</option>
                      <option value="INTERNAL">Internal - Workspace members only</option>
                      <option value="CONFIDENTIAL">Confidential - Export restrictions applied</option>
                      <option value="RESTRICTED">Restricted - Strict column masking & clearance</option>
                    </select>
                  </div>

                  <div className="flex items-center pt-5">
                    <label className="flex items-center gap-2 text-xs text-[#102C46] cursor-pointer font-semibold">
                      <input
                        type="checkbox"
                        checked={exportRestricted}
                        onChange={(e) => setExportRestricted(e.target.checked)}
                        className="rounded text-[#009F98]"
                      />
                      Enforce CSV / Raw Export Restrictions
                    </label>
                  </div>
                </div>

                {/* Column Masking Rules */}
                <div className="pt-3 border-t border-[#DCE5EB] space-y-3">
                  <span className="text-xs font-bold text-[#102C46] block">
                    Restricted Column Masking Rules
                  </span>

                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Column name (e.g. ssn, salary, email)..."
                      value={newMaskCol}
                      onChange={(e) => setNewMaskCol(e.target.value)}
                      className="text-xs p-2 border border-[#DCE5EB] rounded-xl bg-white flex-1"
                    />
                    <select
                      value={newMaskType}
                      onChange={(e) => setNewMaskType(e.target.value as any)}
                      className="text-xs p-2 border border-[#DCE5EB] rounded-xl bg-white"
                    >
                      <option value="redact">Redact (••••••••)</option>
                      <option value="hash">SHA-256 Hash</option>
                      <option value="partial">Partial Mask (***-**-1234)</option>
                    </select>
                    <button
                      onClick={handleAddColumnMask}
                      className="px-4 py-2 bg-[#102C46] text-white text-xs font-bold rounded-xl hover:bg-[#1E3A5F]"
                    >
                      Add Mask
                    </button>
                  </div>

                  {/* Configured column masks list */}
                  <div className="space-y-1.5 mt-2">
                    {Object.entries(governance.column_masks).length === 0 ? (
                      <p className="text-xs text-[#52616C]">No column masks applied to this dataset.</p>
                    ) : (
                      Object.entries(governance.column_masks).map(([col, rule]) => (
                        <div key={col} className="flex items-center justify-between p-2 bg-white rounded-lg border border-[#DCE5EB] text-xs">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-[#102C46]">{col}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-[#EDF7FA] text-[#009F98] uppercase font-bold">
                              {rule.type}
                            </span>
                          </div>
                          <button
                            onClick={() => handleRemoveColumnMask(col)}
                            className="text-[#A63838] hover:bg-red-50 p-1 rounded"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="flex justify-end pt-3">
                  <button
                    onClick={handleSaveGovernance}
                    className="px-5 py-2.5 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-all"
                  >
                    Save Governance Policies
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB F: SECURITY POLICIES */}
        {activeTab === 'policies' && policy && (
          <div className="space-y-6 max-w-2xl">
            <div>
              <h3 className="text-base font-bold text-[#102C46]">Workspace Security Policies</h3>
              <p className="text-xs text-[#52616C]">
                Enforce organizational security boundaries across sharing, exports, and session durations.
              </p>
            </div>

            {policySaved && (
              <div className="p-3 bg-green-50 text-green-700 text-xs rounded-xl flex items-center gap-2">
                <Check className="w-4 h-4" /> Security policies saved and applied across workspace.
              </div>
            )}

            <div className="space-y-4">
              <label className="flex items-center justify-between p-3.5 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] cursor-pointer">
                <div>
                  <span className="text-xs font-bold text-[#102C46] block">Enable Public Share Links</span>
                  <span className="text-[11px] text-[#52616C]">
                    Allow team members to generate public and password-protected external dashboard links.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={policy.allow_public_share_links}
                  onChange={(e) => setPolicy({ ...policy, allow_public_share_links: e.target.checked })}
                  className="rounded text-[#009F98] w-4 h-4"
                />
              </label>

              <div className="p-3.5 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] space-y-2">
                <span className="text-xs font-bold text-[#102C46] block">Maximum Share Link Lifetime (Days)</span>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={policy.max_share_link_days}
                  onChange={(e) => setPolicy({ ...policy, max_share_link_days: Number(e.target.value) })}
                  className="w-full text-xs p-2 border border-[#DCE5EB] rounded-lg bg-white"
                />
              </div>

              <label className="flex items-center justify-between p-3.5 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] cursor-pointer">
                <div>
                  <span className="text-xs font-bold text-[#102C46] block">Restrict Dataset Raw Exports</span>
                  <span className="text-[11px] text-[#52616C]">
                    Disallow raw CSV and Excel exports across all workspace datasets.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={policy.restrict_dataset_exports}
                  onChange={(e) => setPolicy({ ...policy, restrict_dataset_exports: e.target.checked })}
                  className="rounded text-[#009F98] w-4 h-4"
                />
              </label>

              <div className="p-3.5 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] space-y-2">
                <span className="text-xs font-bold text-[#102C46] block">Audit Log Retention Policy (Days)</span>
                <select
                  value={policy.audit_retention_days}
                  onChange={(e) => setPolicy({ ...policy, audit_retention_days: Number(e.target.value) })}
                  className="w-full text-xs p-2 border border-[#DCE5EB] rounded-lg bg-white"
                >
                  <option value={30}>30 Days</option>
                  <option value={90}>90 Days (Recommended)</option>
                  <option value={365}>1 Year</option>
                  <option value={2555}>7 Years (Regulatory Compliance)</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  onClick={handleSavePolicy}
                  className="px-6 py-2.5 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-all shadow-sm"
                >
                  Save Security Policies
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CREATE / EDIT CUSTOM ROLE MODAL */}
      {isRoleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in">
          <div className="w-full max-w-2xl bg-white rounded-3xl shadow-elevated border border-[#DCE5EB] p-6 space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-2 border-b border-[#DCE5EB]">
              <h3 className="text-base font-bold text-[#102C46]">
                {editingRole ? 'Edit Custom Role' : 'Create Custom Role'}
              </h3>
              <button onClick={() => setIsRoleModalOpen(false)} className="text-[#52616C] hover:text-[#102C46]">
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveRole} className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div>
                <label className="text-xs font-bold text-[#102C46] block mb-1">Role Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Data Steward, Financial Auditor..."
                  value={roleName}
                  onChange={(e) => setRoleName(e.target.value)}
                  className="w-full text-xs p-2.5 border border-[#DCE5EB] rounded-xl focus:border-[#009F98] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102C46] block mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Describe the responsibilities and scope of this role..."
                  value={roleDesc}
                  onChange={(e) => setRoleDesc(e.target.value)}
                  className="w-full text-xs p-2.5 border border-[#DCE5EB] rounded-xl focus:border-[#009F98] focus:outline-none"
                />
              </div>

              {/* Permissions Selector Grouped by Category */}
              <div className="space-y-3 pt-2">
                <label className="text-xs font-bold text-[#102C46] block">
                  Permissions Matrix ({selectedPermissions.length} selected)
                </label>
                {categories.map((cat) => {
                  const catPerms = catalog.filter((p) => p.category === cat);
                  return (
                    <div key={cat} className="p-3 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] space-y-2">
                      <span className="text-xs font-bold text-[#102C46] block">{cat}</span>
                      <div className="grid grid-cols-2 gap-2">
                        {catPerms.map((perm) => {
                          const isChecked = selectedPermissions.includes(perm.code);
                          return (
                            <label key={perm.code} className="flex items-start gap-2 text-xs text-[#2D3E4E] cursor-pointer">
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedPermissions([...selectedPermissions, perm.code]);
                                  } else {
                                    setSelectedPermissions(selectedPermissions.filter((p) => p !== perm.code));
                                  }
                                }}
                                className="mt-0.5 rounded text-[#009F98]"
                              />
                              <div>
                                <span className="font-semibold block">{perm.name}</span>
                                <span className="text-[10px] text-[#52616C] block">{perm.description}</span>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-[#DCE5EB]">
                <button
                  type="button"
                  onClick={() => setIsRoleModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-[#52616C] hover:bg-gray-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781]"
                >
                  {editingRole ? 'Save Changes' : 'Create Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

