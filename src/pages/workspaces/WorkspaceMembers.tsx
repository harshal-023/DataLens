import React, { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  Mail,
  Shield,
  Trash2,
  RefreshCw,
  Copy,
  Check,
  Clock,
  AlertCircle,
  MoreVertical,
} from 'lucide-react';
import {
  collaborationService,
  WorkspaceMember,
  WorkspaceInvitation,
} from '../../services/collaborationService';
import { useAuth } from '../../context/AuthContext';

export const WorkspaceMembers: React.FC = () => {
  const { currentWorkspace, user } = useAuth();
  const workspaceId = currentWorkspace?.id;

  const [activeTab, setActiveTab] = useState<'members' | 'invitations'>('members');
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [loading, setLoading] = useState(false);

  // Invite modal
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'editor' | 'viewer'>('editor');
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadData = async () => {
    if (!workspaceId) return;
    setLoading(true);
    try {
      const [membersData, invitationsData] = await Promise.all([
        collaborationService.listMembers(workspaceId),
        collaborationService.listInvitations(workspaceId),
      ]);
      setMembers(membersData);
      setInvitations(invitationsData);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [workspaceId]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || !inviteEmail.trim()) return;

    setInviting(true);
    setInviteError(null);
    try {
      const newInv = await collaborationService.inviteMember(
        workspaceId,
        inviteEmail.trim(),
        inviteRole
      );
      setInviteSuccess(`Invitation sent to ${newInv.email}!`);
      setInviteEmail('');
      setInvitations((prev) => [newInv, ...prev]);
      setTimeout(() => {
        setInviteSuccess(null);
        setIsInviteOpen(false);
      }, 2000);
    } catch (err: any) {
      setInviteError(err.message || 'Failed to send invitation');
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (memberUserId: string, newRole: string) => {
    if (!workspaceId) return;
    try {
      const updated = await collaborationService.updateMemberRole(
        workspaceId,
        memberUserId,
        newRole
      );
      setMembers((prev) =>
        prev.map((m) => (m.user_id === memberUserId ? { ...m, role: updated.role } : m))
      );
    } catch (err: any) {
      alert(err.message || 'Failed to update member role');
    }
  };

  const handleRemoveMember = async (memberUserId: string, memberName: string) => {
    if (!workspaceId) return;
    if (!confirm(`Are you sure you want to remove ${memberName} from this workspace?`)) return;

    try {
      await collaborationService.removeMember(workspaceId, memberUserId);
      setMembers((prev) => prev.filter((m) => m.user_id !== memberUserId));
    } catch (err: any) {
      alert(err.message || 'Failed to remove member');
    }
  };

  const handleResendInvitation = async (invitationId: string) => {
    if (!workspaceId) return;
    try {
      const updated = await collaborationService.resendInvitation(workspaceId, invitationId);
      setInvitations((prev) =>
        prev.map((i) => (i.id === invitationId ? updated : i))
      );
      alert('Invitation resent successfully!');
    } catch (err: any) {
      alert(err.message || 'Failed to resend invitation');
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    if (!workspaceId) return;
    if (!confirm('Are you sure you want to revoke this invitation?')) return;

    try {
      await collaborationService.revokeInvitation(workspaceId, invitationId);
      setInvitations((prev) =>
        prev.map((i) => (i.id === invitationId ? { ...i, status: 'revoked' } : i))
      );
    } catch (err: any) {
      alert(err.message || 'Failed to revoke invitation');
    }
  };

  const handleCopyLink = (url: string | undefined, id: string) => {
    if (!url) return;
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const isOwnerOrAdmin =
    members.find((m) => m.user_id === user?.id)?.role === 'owner' ||
    members.find((m) => m.user_id === user?.id)?.role === 'admin';

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#102C46]">Workspace Team & Members</h1>
          <p className="text-sm text-[#52616C] mt-1">
            Manage teammates, modify permissions, and invite collaborators to{' '}
            <span className="font-semibold text-[#102C46]">
              {currentWorkspace?.name || 'Workspace'}
            </span>
            .
          </p>
        </div>

        {isOwnerOrAdmin && (
          <button
            onClick={() => setIsInviteOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-all shadow-sm cursor-pointer"
          >
            <UserPlus className="w-4 h-4" /> Invite Member
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#DCE5EB] space-x-6">
        <button
          onClick={() => setActiveTab('members')}
          className={`flex items-center gap-2 pb-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
            activeTab === 'members'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-[#52616C] hover:text-[#102C46]'
          }`}
        >
          <Users className="w-4 h-4" /> Active Members ({members.length})
        </button>
        <button
          onClick={() => setActiveTab('invitations')}
          className={`flex items-center gap-2 pb-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
            activeTab === 'invitations'
              ? 'border-[#009F98] text-[#009F98]'
              : 'border-transparent text-[#52616C] hover:text-[#102C46]'
          }`}
        >
          <Mail className="w-4 h-4" /> Pending Invitations (
          {invitations.filter((i) => i.status === 'pending').length})
        </button>
      </div>

      {/* Active Members Table */}
      {activeTab === 'members' && (
        <div className="bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAFC] text-[#52616C] uppercase text-[10px] font-bold tracking-wider border-b border-[#DCE5EB]">
                <tr>
                  <th className="py-3.5 px-6">Member</th>
                  <th className="py-3.5 px-6">Email</th>
                  <th className="py-3.5 px-6">Role</th>
                  <th className="py-3.5 px-6">Joined Date</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EEF3F6]">
                {members.map((member) => {
                  const isCurrent = member.user_id === user?.id;
                  const isMemberOwner = member.role === 'owner';

                  return (
                    <tr key={member.user_id} className="hover:bg-[#F8FAFC] transition-colors">
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-[#009F98] text-white flex items-center justify-center font-bold text-xs shrink-0">
                            {member.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <span className="font-bold text-[#102C46] flex items-center gap-1.5">
                              {member.full_name}
                              {isCurrent && (
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#EDF7FA] text-[#009F98] font-normal">
                                  You
                                </span>
                              )}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-[#52616C]">{member.email}</td>
                      <td className="py-4 px-6">
                        {isOwnerOrAdmin && !isMemberOwner ? (
                          <select
                            value={member.role}
                            onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                            className="text-xs p-1.5 border border-[#DCE5EB] rounded-lg focus:outline-none focus:border-[#009F98] bg-white font-medium"
                          >
                            <option value="admin">Admin</option>
                            <option value="editor">Editor</option>
                            <option value="viewer">Viewer</option>
                          </select>
                        ) : (
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              isMemberOwner
                                ? 'bg-[#102C46] text-white'
                                : 'bg-[#EDF7FA] text-[#009F98]'
                            }`}
                          >
                            {member.role}
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-[#8A9BA8]">
                        {new Date(member.joined_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-4 px-6 text-right">
                        {isOwnerOrAdmin && !isMemberOwner && !isCurrent && (
                          <button
                            onClick={() => handleRemoveMember(member.user_id, member.full_name)}
                            className="p-1.5 text-[#A63838] hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                            title="Remove from workspace"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pending Invitations Table */}
      {activeTab === 'invitations' && (
        <div className="bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAFC] text-[#52616C] uppercase text-[10px] font-bold tracking-wider border-b border-[#DCE5EB]">
                <tr>
                  <th className="py-3.5 px-6">Invited Email</th>
                  <th className="py-3.5 px-6">Target Role</th>
                  <th className="py-3.5 px-6">Status</th>
                  <th className="py-3.5 px-6">Expires At</th>
                  <th className="py-3.5 px-6">Resends</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EEF3F6]">
                {invitations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[#52616C]">
                      No invitations found for this workspace.
                    </td>
                  </tr>
                ) : (
                  invitations.map((inv) => (
                    <tr key={inv.id} className="hover:bg-[#F8FAFC] transition-colors">
                      <td className="py-4 px-6 font-semibold text-[#102C46]">{inv.email}</td>
                      <td className="py-4 px-6">
                        <span className="px-2 py-0.5 rounded-full bg-[#EDF7FA] text-[#009F98] text-[10px] font-bold uppercase">
                          {inv.role}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            inv.status === 'accepted'
                              ? 'bg-green-100 text-green-700'
                              : inv.status === 'revoked'
                              ? 'bg-gray-100 text-gray-600'
                              : inv.status === 'expired'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-[#8A9BA8]">
                        {new Date(inv.expires_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-4 px-6 text-[#52616C]">{inv.resend_count}</td>
                      <td className="py-4 px-6 text-right">
                        {inv.status === 'pending' && isOwnerOrAdmin && (
                          <div className="flex items-center justify-end gap-2">
                            {inv.invitation_url && (
                              <button
                                onClick={() => handleCopyLink(inv.invitation_url, inv.id)}
                                className="p-1.5 text-[#52616C] hover:text-[#102C46] hover:bg-gray-100 rounded-lg cursor-pointer"
                                title="Copy invitation link"
                              >
                                {copiedId === inv.id ? (
                                  <Check className="w-4 h-4 text-green-600" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </button>
                            )}
                            <button
                              onClick={() => handleResendInvitation(inv.id)}
                              className="p-1.5 text-[#009F98] hover:bg-[#EDF7FA] rounded-lg cursor-pointer"
                              title="Resend invitation email"
                            >
                              <RefreshCw className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleRevokeInvitation(inv.id)}
                              className="p-1.5 text-[#A63838] hover:bg-red-50 rounded-lg cursor-pointer"
                              title="Revoke invitation"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Invite Member Modal */}
      {isInviteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#DCE5EB]">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-[#EDF7FA] text-[#009F98] rounded-xl">
                  <UserPlus className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold text-[#102C46]">Invite Workspace Member</h3>
              </div>
              <button
                onClick={() => setIsInviteOpen(false)}
                className="text-[#52616C] hover:text-[#102C46]"
              >
                ✕
              </button>
            </div>

            {inviteSuccess && (
              <div className="p-2.5 bg-green-50 text-green-700 text-xs rounded-xl flex items-center gap-2">
                <Check className="w-4 h-4" /> {inviteSuccess}
              </div>
            )}

            {inviteError && (
              <div className="p-2.5 bg-red-50 text-red-700 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> {inviteError}
              </div>
            )}

            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-[#102C46] block mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="collaborator@example.com"
                  className="w-full text-xs p-2.5 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#102C46] block mb-1">
                  Workspace Role
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as any)}
                  className="w-full text-xs p-2.5 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                >
                  <option value="viewer">Viewer - Can view datasets, dashboards & reports</option>
                  <option value="editor">Editor - Can create dashboards, transformations & reports</option>
                  <option value="admin">Admin - Can manage members, connections & settings</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsInviteOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-[#52616C] hover:bg-[#EEF3F6] rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="px-5 py-2 text-xs font-bold bg-[#009F98] text-white rounded-xl hover:bg-[#008781] disabled:opacity-50 transition-all cursor-pointer"
                >
                  {inviting ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

