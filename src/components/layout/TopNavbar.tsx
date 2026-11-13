import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Bell,
  ChevronDown,
  Menu,
  Settings,
  LogOut,
  Database,
  FileText,
  FlaskConical,
  MessageSquare,
  Sparkles,
  X,
  Check,
  Building,
} from 'lucide-react';
import { StorageService } from '../../services/storageService';
import { useAuth } from '../../context/AuthContext';
import { NotificationCenter } from './NotificationCenter';

export interface TopNavbarProps {
  onOpenMobileMenu: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({ onOpenMobileMenu }) => {
  const navigate = useNavigate();
  const auth = useAuth();
  const fallbackUser = StorageService.getUser();
  const displayName = auth.user?.full_name || fallbackUser.name || 'Harshal Sharma';
  const displayEmail = auth.user?.email || fallbackUser.email || 'harshal@datalens.ai';
  const currentWorkspaceName = auth.currentWorkspace?.name || 'Pro Workspace';

  const [notifications, setNotifications] = useState(StorageService.getNotifications());
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const searchRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const datasets = StorageService.getDatasets();
  const reports = StorageService.getReports();
  const experiments = StorageService.getExperiments();

  // Compute initials
  const initials = displayName
    ? displayName
        .split(' ')
        .map((n: string) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'HS';

  // Keyboard shortcut listener for ⌘ K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
        setTimeout(() => searchInputRef.current?.focus(), 50);
      } else if (e.key === 'Escape') {
        setIsSearchOpen(false);
        setShowNotifications(false);
        setShowUserMenu(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Click outside listener for search popover
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredDatasets = searchQuery
    ? datasets.filter((d) => d.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : datasets.slice(0, 3);

  const filteredReports = searchQuery
    ? reports.filter((r) => r.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : reports.slice(0, 3);

  const filteredExperiments = searchQuery
    ? experiments.filter((e) => e.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : experiments.slice(0, 2);

  const hasResults =
    filteredDatasets.length > 0 || filteredReports.length > 0 || filteredExperiments.length > 0;

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-[#DCE5EB] px-4 sm:px-8 flex items-center justify-between select-none">
      {/* Left: Mobile hamburger & Global Search Bar matching reference */}
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 rounded-lg text-[#52616C] hover:bg-[#EEF3F6] hover:text-[#102C46] cursor-pointer"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Omnisearch Container with Keyboard Shortcut */}
        <div ref={searchRef} className="relative w-full max-w-lg">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#52616C]" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsSearchOpen(true);
              }}
              onFocus={() => setIsSearchOpen(true)}
              placeholder="Search datasets, reports, insights, or prompts..."
              className="w-full pl-10 pr-12 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] text-[#102C46] placeholder:text-[#52616C] focus:outline-none focus:ring-2 focus:ring-[#009F98] focus:bg-white transition-all shadow-2xs"
            />
            {searchQuery ? (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#52616C] hover:text-[#102C46]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            ) : (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-[#52616C] bg-white px-1.5 py-0.5 rounded border border-[#DCE5EB] pointer-events-none">
                ⌘ K
              </span>
            )}
          </div>

          {/* Interactive Global Search Dropdown */}
          {isSearchOpen && (
            <div className="absolute left-0 top-full mt-2 w-full bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] p-3 z-50 animate-in fade-in-50 duration-150">
              <div className="flex items-center justify-between pb-2 border-b border-[#DCE5EB] text-[11px] text-[#52616C]">
                <span>{searchQuery ? `Results for "${searchQuery}"` : 'Quick Suggestions'}</span>
                <span>ESC to close</span>
              </div>

              {!hasResults ? (
                <div className="py-6 text-center text-xs text-[#52616C]">
                  No matching assets found for "{searchQuery}".
                </div>
              ) : (
                <div className="divide-y divide-[#EEF3F6] max-h-72 overflow-y-auto mt-1">
                  {/* Datasets */}
                  {filteredDatasets.length > 0 && (
                    <div className="py-2">
                      <span className="text-[10px] font-bold text-[#52616C] uppercase tracking-wider block mb-1">
                        Datasets
                      </span>
                      {filteredDatasets.map((d) => (
                        <div
                          key={d.id}
                          onClick={() => {
                            navigate(`/data/${d.id}`);
                            setIsSearchOpen(false);
                          }}
                          className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-[#EDF7FA] cursor-pointer text-xs text-[#102C46] transition-colors"
                        >
                          <Database className="w-3.5 h-3.5 text-[#009F98]" />
                          <span className="font-semibold">{d.name}</span>
                          <span className="text-[10px] text-[#52616C]">({d.rowCount.toLocaleString()} rows)</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Reports */}
                  {filteredReports.length > 0 && (
                    <div className="py-2">
                      <span className="text-[10px] font-bold text-[#52616C] uppercase tracking-wider block mb-1">
                        Reports
                      </span>
                      {filteredReports.map((r) => (
                        <div
                          key={r.id}
                          onClick={() => {
                            navigate(`/reports/${r.id}/preview`);
                            setIsSearchOpen(false);
                          }}
                          className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-[#EDF7FA] cursor-pointer text-xs text-[#102C46] transition-colors"
                        >
                          <FileText className="w-3.5 h-3.5 text-[#009F98]" />
                          <span className="font-semibold">{r.title}</span>
                          <span className="text-[10px] text-[#52616C]">({r.type})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Prompt Experiments */}
                  {filteredExperiments.length > 0 && (
                    <div className="py-2">
                      <span className="text-[10px] font-bold text-[#52616C] uppercase tracking-wider block mb-1">
                        Prompt Lab Experiments
                      </span>
                      {filteredExperiments.map((e) => (
                        <div
                          key={e.id}
                          onClick={() => {
                            navigate(`/prompt-lab/experiments/${e.id}`);
                            setIsSearchOpen(false);
                          }}
                          className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-[#EDF7FA] cursor-pointer text-xs text-[#102C46] transition-colors"
                        >
                          <FlaskConical className="w-3.5 h-3.5 text-[#009F98]" />
                          <span className="font-semibold">{e.title}</span>
                          <span className="text-[10px] text-[#52616C]">• {e.datasetName}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Notifications & Profile Pill */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <NotificationCenter />

        {/* User Profile Pill matching reference image */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2.5 py-1 px-2 rounded-full hover:bg-[#EEF3F6] transition-colors cursor-pointer"
          >
            {/* Signature Peacock Teal Circular Avatar with white initials */}
            <div className="w-8 h-8 rounded-full bg-[#009F98] text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-2xs">
              {initials}
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="text-xs font-bold text-[#102C46] leading-none">
                {displayName}
              </span>
              <span className="text-[10px] text-[#52616C] font-medium mt-0.5 leading-none">
                {currentWorkspaceName}
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-[#52616C]" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-elevated border border-[#DCE5EB] p-2 z-50 animate-in fade-in-50">
              <div className="px-3 py-2 border-b border-[#DCE5EB]">
                <p className="text-xs font-semibold text-[#102C46]">{displayName}</p>
                <p className="text-[11px] text-[#52616C] truncate">{displayEmail}</p>
              </div>

              {/* Workspaces Switcher */}
              {auth.workspaces.length > 0 && (
                <div className="p-2 border-b border-[#DCE5EB]">
                  <p className="text-[10px] font-bold text-[#52616C] uppercase tracking-wider mb-1.5 px-1">
                    Workspaces
                  </p>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {auth.workspaces.map((ws) => (
                      <button
                        key={ws.id}
                        onClick={() => {
                          auth.setCurrentWorkspace(ws);
                          setShowUserMenu(false);
                        }}
                        className={`w-full text-left px-2 py-1.5 rounded-lg text-xs flex items-center justify-between transition-colors ${
                          auth.currentWorkspace?.id === ws.id
                            ? 'bg-[#EDF7FA] text-[#007D78] font-bold'
                            : 'text-[#102C46] hover:bg-[#F5F8FA]'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <Building className="w-3.5 h-3.5 text-[#009F98] shrink-0" />
                          <span className="truncate">{ws.name}</span>
                        </div>
                        {auth.currentWorkspace?.id === ws.id && (
                          <Check className="w-3 h-3 text-[#009F98] shrink-0" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="p-1 space-y-0.5">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    navigate('/settings');
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-[#102C46] rounded-lg hover:bg-[#EDF7FA] flex items-center gap-2 cursor-pointer"
                >
                  <Settings className="w-3.5 h-3.5 text-[#52616C]" />
                  <span>Workspace Settings</span>
                </button>
                <button
                  onClick={async () => {
                    setShowUserMenu(false);
                    await auth.logout();
                    navigate('/login');
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-[#A63838] rounded-lg hover:bg-[#FCE9E9] flex items-center gap-2 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
