import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Check, Trash2, ExternalLink, Filter } from 'lucide-react';
import { collaborationService, NotificationItem } from '../../services/collaborationService';
import { useAuth } from '../../context/AuthContext';

export const NotificationCenter: React.FC = () => {
  const navigate = useNavigate();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.id;

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    if (!workspaceId) return;
    try {
      const [list, count] = await Promise.all([
        collaborationService.listNotifications(workspaceId, unreadOnly, 30),
        collaborationService.getUnreadCount(workspaceId),
      ]);
      setNotifications(list);
      setUnreadCount(count);
    } catch {
      // Gracefully silent fallback
    }
  };

  useEffect(() => {
    fetchNotifications();

    // Subscribe to real-time events via SSE
    const unsubscribe = collaborationService.createNotificationSource((newNotif) => {
      setNotifications((prev) => [newNotif, ...prev]);
      setUnreadCount((c) => c + 1);
    });

    // Also poll every 30 seconds as fallback
    const interval = setInterval(fetchNotifications, 30000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [workspaceId, unreadOnly]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await collaborationService.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async () => {
    if (!workspaceId) return;
    try {
      await collaborationService.markAllNotificationsRead(workspaceId);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  };

  const handleDismiss = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await collaborationService.dismissNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  };

  const handleNotificationClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await collaborationService.markNotificationRead(notif.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch {
        // ignore
      }
    }
    setIsOpen(false);

    if (notif.data?.action_url) {
      if (notif.data.action_url.startsWith('http')) {
        const path = new URL(notif.data.action_url).pathname;
        navigate(path);
      } else {
        navigate(notif.data.action_url);
      }
    } else if (notif.resource_type === 'dashboard' && notif.resource_id) {
      navigate(`/dashboards/${notif.resource_id}`);
    } else if (notif.resource_type === 'report' && notif.resource_id) {
      navigate(`/reports/${notif.resource_id}`);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-full text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6] relative transition-colors cursor-pointer"
        title="Notifications"
        aria-label="View notifications"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-4 h-4 px-1 rounded-full bg-[#009F98] text-white text-[9px] font-bold ring-2 ring-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-84 bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] p-3 z-50 animate-in fade-in-50">
          <div className="flex items-center justify-between pb-2 border-b border-[#DCE5EB]">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#102C46]">Notifications</span>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-[#EDF7FA] text-[#009F98] text-[10px] font-bold">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setUnreadOnly(!unreadOnly)}
                className={`text-[10px] px-2 py-0.5 rounded transition-colors ${
                  unreadOnly
                    ? 'bg-[#009F98] text-white font-semibold'
                    : 'text-[#52616C] hover:bg-[#EEF3F6]'
                }`}
              >
                {unreadOnly ? 'Showing Unread' : 'All'}
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-[10px] text-[#009F98] hover:text-[#007F79] font-medium"
                >
                  Mark all read
                </button>
              )}
            </div>
          </div>

          <div className="divide-y divide-[#EEF3F6] max-h-72 overflow-y-auto mt-1">
            {notifications.length === 0 ? (
              <div className="py-6 text-center text-xs text-[#52616C]">
                No notifications right now.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleNotificationClick(n)}
                  className={`p-2.5 rounded-xl transition-colors cursor-pointer group flex items-start justify-between gap-2 ${
                    n.is_read ? 'hover:bg-[#F5F8FA]' : 'bg-[#F0F9F9] hover:bg-[#E5F5F5]'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      {!n.is_read && (
                        <span className="w-1.5 h-1.5 rounded-full bg-[#009F98] shrink-0" />
                      )}
                      <p className="text-xs font-semibold text-[#102C46] truncate">{n.title}</p>
                    </div>
                    <p className="text-[11px] text-[#52616C] mt-0.5 line-clamp-2">{n.message}</p>
                    <span className="text-[9px] text-[#8A9BA8] block mt-1">
                      {new Date(n.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {!n.is_read && (
                      <button
                        onClick={(e) => handleMarkAsRead(n.id, e)}
                        className="p-1 hover:bg-white rounded text-[#009F98]"
                        title="Mark as read"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={(e) => handleDismiss(n.id, e)}
                      className="p-1 hover:bg-white rounded text-[#A63838]"
                      title="Dismiss"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

