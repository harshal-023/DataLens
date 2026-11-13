import React, { useState, useEffect } from 'react';
import {
  X,
  Share2,
  Users,
  Link as LinkIcon,
  Copy,
  Check,
  Trash2,
  Lock,
  Download,
} from 'lucide-react';
import {
  collaborationService,
  MemberShare,
  ShareAccessTokenInfo,
  WorkspaceMember,
} from '../../services/collaborationService';
import { useAuth } from '../../context/AuthContext';

interface ReportShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportId: string;
  reportTitle: string;
}

export const ReportShareModal: React.FC<ReportShareModalProps> = ({
  isOpen,
  onClose,
  reportId,
  reportTitle,
}) => {
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id;

  const [activeTab, setActiveTab] = useState<'members' | 'links'>('members');
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [shares, setShares] = useState<MemberShare[]>([]);
  const [links, setLinks] = useState<ShareAccessTokenInfo[]>([]);

  // Member Share form
  const [selectedUserId, setSelectedUserId] = useState('');
  const [memberRole, setMemberRole] = useState<'viewer' | 'editor'>('viewer');

  // Share Link form
  const [expiresInDays, setExpiresInDays] = useState<number | undefined>(7);
  const [linkPassword, setLinkPassword] = useState('');

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !workspaceId) return;

    const loadData = async () => {
      try {
        const [wsMembers, currentShares, currentLinks] = await Promise.all([
          collaborationService.listMembers(workspaceId),
          collaborationService.listReportShares(workspaceId, reportId),
          collaborationService.listReportShareLinks(workspaceId, reportId),
        ]);
        setMembers(wsMembers);
        setShares(currentShares);
        setLinks(currentLinks);
        if (wsMembers.length > 0) {
          setSelectedUserId(wsMembers[0].user_id);
        }
      } catch {
        // ignore
      }
    };

    loadData();
  }, [isOpen, workspaceId, reportId]);

  const handleShareWithMember = async () => {
    if (!workspaceId || !selectedUserId) return;
    try {
      await collaborationService.shareReportWithMember(
        workspaceId,
        reportId,
        selectedUserId,
        memberRole
      );
      const updated = await collaborationService.listReportShares(workspaceId, reportId);
      setShares(updated);
      setActionSuccess('Report shared successfully with member.');
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (e: any) {
      alert(e.message || 'Failed to share report');
    }
  };

  const handleRevokeShare = async (shareId: string) => {
    if (!workspaceId) return;
    try {
      await collaborationService.revokeReportShare(workspaceId, reportId, shareId);
      setShares((prev) => prev.filter((s) => s.id !== shareId));
    } catch (e: any) {
      alert(e.message || 'Failed to revoke share');
    }
  };

  const handleCreateLink = async () => {
    if (!workspaceId) return;
    try {
      await collaborationService.createReportShareLink(workspaceId, reportId, {
        allow_download: true,
        expires_in_days: expiresInDays,
        password: linkPassword || undefined,
      });
      const updated = await collaborationService.listReportShareLinks(workspaceId, reportId);
      setLinks(updated);
      setLinkPassword('');
      setActionSuccess('Controlled download link generated.');
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (e: any) {
      alert(e.message || 'Failed to create report link');
    }
  };

  const handleRevokeLink = async (tokenId: string) => {
    if (!workspaceId) return;
    try {
      await collaborationService.revokeReportShareLink(workspaceId, reportId, tokenId);
      setLinks((prev) => prev.filter((l) => l.id !== tokenId));
    } catch (e: any) {
      alert(e.message || 'Failed to revoke link');
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#DCE5EB] bg-[#F8FAFC]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-[#EDF7FA] text-[#009F98] rounded-xl">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#102C46]">Share Report</h2>
              <p className="text-xs text-[#52616C] truncate max-w-sm">{reportTitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Bar */}
        <div className="flex border-b border-[#DCE5EB] px-6 bg-white">
          <button
            onClick={() => setActiveTab('members')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'members'
                ? 'border-[#009F98] text-[#009F98]'
                : 'border-transparent text-[#52616C] hover:text-[#102C46]'
            }`}
          >
            <Users className="w-4 h-4" /> Team Members ({shares.length})
          </button>
          <button
            onClick={() => setActiveTab('links')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'links'
                ? 'border-[#009F98] text-[#009F98]'
                : 'border-transparent text-[#52616C] hover:text-[#102C46]'
            }`}
          >
            <LinkIcon className="w-4 h-4" /> Download Links ({links.length})
          </button>
        </div>

        {/* Action success alert */}
        {actionSuccess && (
          <div className="mx-6 mt-3 p-2 bg-[#DCFCE7] text-[#16A34A] rounded-lg text-xs font-semibold flex items-center gap-2">
            <Check className="w-4 h-4" /> {actionSuccess}
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 space-y-5 max-h-[65vh] overflow-y-auto">
          {activeTab === 'members' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="flex-1 text-xs p-2 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                >
                  {members.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.full_name} ({m.email})
                    </option>
                  ))}
                </select>

                <select
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value as any)}
                  className="text-xs p-2 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98]"
                >
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                </select>

                <button
                  onClick={handleShareWithMember}
                  className="px-4 py-2 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-colors shrink-0"
                >
                  Share
                </button>
              </div>

              <div className="border border-[#DCE5EB] rounded-xl divide-y divide-[#EEF3F6]">
                {shares.length === 0 ? (
                  <div className="p-4 text-center text-xs text-[#52616C]">
                    No specific member shares. Team members access reports per workspace permissions.
                  </div>
                ) : (
                  shares.map((share) => (
                    <div
                      key={share.id}
                      className="p-3 flex items-center justify-between text-xs hover:bg-[#F8FAFC]"
                    >
                      <div>
                        <span className="font-bold text-[#102C46]">
                          {share.shared_with_name}
                        </span>
                        <span className="text-[11px] text-[#52616C] block">
                          {share.shared_with_email}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="px-2 py-0.5 rounded-md bg-[#EDF7FA] text-[#009F98] text-[10px] font-bold uppercase">
                          {share.permission}
                        </span>
                        <button
                          onClick={() => handleRevokeShare(share.id)}
                          className="p-1 text-[#A63838] hover:bg-red-50 rounded"
                          title="Revoke access"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'links' && (
            <div className="space-y-4">
              <div className="p-4 bg-[#F8FAFC] rounded-xl border border-[#DCE5EB] space-y-3">
                <span className="text-xs font-bold text-[#102C46] block">
                  Generate Secure Download Link
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-[#52616C] block mb-1">
                      Expires in
                    </label>
                    <select
                      value={expiresInDays || ''}
                      onChange={(e) =>
                        setExpiresInDays(e.target.value ? Number(e.target.value) : undefined)
                      }
                      className="w-full text-xs p-2 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] bg-white"
                    >
                      <option value="1">1 Day</option>
                      <option value="7">7 Days</option>
                      <option value="30">30 Days</option>
                      <option value="">Never Expires</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-[#52616C] block mb-1">
                      Password Protection (Optional)
                    </label>
                    <input
                      type="password"
                      placeholder="Optional password"
                      value={linkPassword}
                      onChange={(e) => setLinkPassword(e.target.value)}
                      className="w-full text-xs p-2 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] bg-white"
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    onClick={handleCreateLink}
                    className="px-4 py-2 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-colors"
                  >
                    Generate Download Link
                  </button>
                </div>
              </div>

              <div className="border border-[#DCE5EB] rounded-xl divide-y divide-[#EEF3F6]">
                {links.length === 0 ? (
                  <div className="p-4 text-center text-xs text-[#52616C]">
                    No active download links.
                  </div>
                ) : (
                  links.map((link) => (
                    <div key={link.id} className="p-3 space-y-2 hover:bg-[#F8FAFC]">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-[#102C46]">Download Link</span>
                          {link.has_password && (
                            <span className="flex items-center gap-1 text-[10px] text-[#B45309] bg-[#FEF3C7] px-1.5 py-0.5 rounded">
                              <Lock className="w-3 h-3" /> Password Protected
                            </span>
                          )}
                          <span className="text-[10px] text-[#52616C]">
                            {link.access_count} downloads
                          </span>
                        </div>
                        <button
                          onClick={() => handleRevokeLink(link.id)}
                          className="text-xs text-[#A63838] hover:underline"
                        >
                          Revoke
                        </button>
                      </div>

                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          readOnly
                          value={link.share_url}
                          className="flex-1 text-xs p-2 bg-[#F1F5F9] border border-[#CBD5E1] rounded-lg text-[#334155]"
                        />
                        <button
                          onClick={() => handleCopy(link.share_url, link.id)}
                          className="px-3 py-2 bg-[#102C46] text-white rounded-lg text-xs font-medium hover:bg-[#1E3A5F] flex items-center gap-1"
                        >
                          {copiedId === link.id ? (
                            <>
                              <Check className="w-3.5 h-3.5" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" /> Copy
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

