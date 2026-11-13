import React, { useState, useEffect } from 'react';
import {
  Activity,
  Filter,
  RefreshCw,
  Database,
  LayoutDashboard,
  FileText,
  UserPlus,
  Share2,
  MessageSquare,
  Radio,
  Calendar,
} from 'lucide-react';
import { collaborationService, ActivityItem } from '../../services/collaborationService';
import { useAuth } from '../../context/AuthContext';

export const WorkspaceActivityPage: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id;

  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);

  // Filters
  const [resourceType, setResourceType] = useState<string>('');
  const [eventType, setEventType] = useState<string>('');

  const fetchActivities = async () => {
    if (!workspaceId) return;
    setLoading(true);
    try {
      const res = await collaborationService.getWorkspaceActivity(workspaceId, {
        resourceType: resourceType || undefined,
        eventType: eventType || undefined,
        pageSize: 100,
      });
      setActivities(res.items);
      setTotalCount(res.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, [workspaceId, resourceType, eventType]);

  const getEventIcon = (type: string) => {
    if (type.includes('dashboard')) return <LayoutDashboard className="w-4 h-4 text-[#009F98]" />;
    if (type.includes('report')) return <FileText className="w-4 h-4 text-[#3B82F6]" />;
    if (type.includes('dataset') || type.includes('connection'))
      return <Database className="w-4 h-4 text-[#102C46]" />;
    if (type.includes('invitation') || type.includes('member'))
      return <UserPlus className="w-4 h-4 text-[#8B5CF6]" />;
    if (type.includes('comment') || type.includes('discussion'))
      return <MessageSquare className="w-4 h-4 text-[#F59E0B]" />;
    return <Activity className="w-4 h-4 text-[#52616C]" />;
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#102C46]">Workspace Activity & Audit Feed</h1>
          <p className="text-sm text-[#52616C] mt-1">
            Real-time chronological timeline of team actions, resource shares, and data events in{' '}
            <span className="font-semibold text-[#102C46]">
              {currentWorkspace?.name || 'Workspace'}
            </span>
            .
          </p>
        </div>

        <button
          onClick={fetchActivities}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 border border-[#DCE5EB] bg-white rounded-xl text-xs font-semibold text-[#52616C] hover:text-[#102C46] hover:bg-[#F8FAFC] cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-2xl shadow-elevated border border-[#DCE5EB] flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-2 text-[#52616C] font-semibold">
          <Filter className="w-4 h-4 text-[#009F98]" /> Filters:
        </div>

        <div className="flex items-center gap-2">
          <label className="text-[#52616C]">Resource:</label>
          <select
            value={resourceType}
            onChange={(e) => setResourceType(e.target.value)}
            className="p-1.5 border border-[#DCE5EB] rounded-lg focus:outline-none focus:border-[#009F98] bg-white"
          >
            <option value="">All Resources</option>
            <option value="dashboard">Dashboards</option>
            <option value="report">Reports</option>
            <option value="dataset">Datasets</option>
            <option value="invitation">Invitations</option>
            <option value="user">Members</option>
            <option value="connection">Connections</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-[#52616C]">Action Type:</label>
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="p-1.5 border border-[#DCE5EB] rounded-lg focus:outline-none focus:border-[#009F98] bg-white"
          >
            <option value="">All Actions</option>
            <option value="dashboard_shared">Dashboard Shared</option>
            <option value="report_shared">Report Shared</option>
            <option value="comment_added">Comment Added</option>
            <option value="discussion_resolved">Discussion Resolved</option>
            <option value="invitation_sent">Invitation Sent</option>
            <option value="member_joined">Member Joined</option>
            <option value="member_role_changed">Member Role Changed</option>
          </select>
        </div>

        {(resourceType || eventType) && (
          <button
            onClick={() => {
              setResourceType('');
              setEventType('');
            }}
            className="text-[11px] text-[#009F98] hover:underline font-medium"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Activities Timeline */}
      <div className="bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] p-6">
        {activities.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#52616C]">
            No activity logged yet matching these filters.
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#EEF3F6]">
            {activities.map((act) => (
              <div key={act.id} className="relative flex items-start gap-3 group">
                {/* Timeline node icon */}
                <div className="absolute -left-6 mt-0.5 p-1 rounded-full bg-white border border-[#DCE5EB] shadow-2xs group-hover:border-[#009F98] transition-colors">
                  {getEventIcon(act.event_type)}
                </div>

                {/* Event Details */}
                <div className="flex-1 bg-[#F8FAFC] p-3 rounded-xl border border-[#EEF3F6] hover:border-[#DCE5EB] transition-colors">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-[#102C46]">
                      {act.actor_name || 'System User'}
                    </span>
                    <span className="text-[10px] text-[#8A9BA8]">
                      {new Date(act.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>

                  <p className="text-xs text-[#2D3E4E]">{act.summary}</p>

                  {/* Sanitized Metadata details if any */}
                  {act.metadata_snapshot &&
                    Object.keys(act.metadata_snapshot).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {Object.entries(act.metadata_snapshot).map(([k, v]) => (
                          <span
                            key={k}
                            className="text-[10px] bg-white border border-[#DCE5EB] text-[#52616C] px-2 py-0.5 rounded-md"
                          >
                            <span className="font-semibold">{k}:</span> {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

