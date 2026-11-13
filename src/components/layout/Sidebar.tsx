import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  MessageSquare,
  FlaskConical,
  FileText,
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
  Crown,
  Sparkles,
  Layers,
  Workflow,
  Cable,
  Users,
  Activity,
  Shield,
  RefreshCw,
  Compass,
} from 'lucide-react';
import { DataLensLogo } from '../common/DataLensLogo';
import { SidebarBottomWave } from '../common/SidebarBottomWave';

export interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen = false,
  onMobileClose,
}) => {
  const location = useLocation();

  const primaryNavItems = [
    {
      name: 'Data Management',
      path: '/data',
      icon: Database,
      subpaths: ['/data', '/data-sources', '/data-preparation'],
    },
    {
      name: 'Analytics & Dashboards',
      path: '/dashboards',
      icon: LayoutDashboard,
      subpaths: ['/dashboards', '/dashboard', '/advanced-analytics'],
    },
    {
      name: 'AI Data Analyst',
      path: '/business-analyst',
      icon: Sparkles,
      badge: 'AI',
      subpaths: ['/business-analyst', '/ask', '/prompt-lab'],
    },
    {
      name: 'Reports',
      path: '/reports',
      icon: FileText,
      subpaths: ['/reports'],
    },
    {
      name: 'Workspace & Settings',
      path: '/settings',
      icon: SettingsIcon,
      subpaths: ['/settings', '/workspaces', '/activity', '/governance', '/automation'],
    },
  ];

  const sidebarContent = (
    <div className="h-full flex flex-col justify-between bg-gradient-to-b from-[#102C46] via-[#0D3550] to-[#073D50] border-r border-[#1D4664]/50 select-none relative overflow-hidden text-white">
      {/* Signature Flowing Peacock Wave in bottom background */}
      <SidebarBottomWave />

      {/* Top Brand Section */}
      <div className="relative z-10 shrink-0">
        <div
          className={`flex items-center justify-between px-5 h-20 border-b border-[#1D4664]/40 ${
            isCollapsed ? 'justify-center px-2' : ''
          }`}
        >
          {!isCollapsed ? (
            <DataLensLogo size="md" theme="dark" />
          ) : (
            <div className="flex items-end gap-1 py-1" title="DataLens">
              <div className="w-1.5 h-3.5 bg-gradient-to-t from-[#007D78] to-[#009F98] rounded-full" />
              <div className="w-1.5 h-5 bg-gradient-to-t from-[#009F98] to-[#39C3B8] rounded-full" />
              <div className="w-1.5 h-7 bg-gradient-to-t from-[#39C3B8] to-[#8BE5DE] rounded-full" />
            </div>
          )}

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-[#BBDCE8] hover:text-white hover:bg-[#1D4664]/60 transition-colors cursor-pointer shrink-0 ml-1"
            title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Middle Navigation Section (Vertically Centered in Sidebar) */}
      <div className="relative z-10 flex-1 flex flex-col justify-center px-3.5 py-4 my-auto">
        <nav className="space-y-2">
          {primaryNavItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.path ||
              item.subpaths.some(
                (sp) => location.pathname === sp || location.pathname.startsWith(sp + '/')
              );

            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={onMobileClose}
                className={`flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-150 cursor-pointer relative ${
                  isActive
                    ? 'bg-[#009F98] text-white font-bold shadow-[0_4px_16px_rgba(0,159,152,0.38)]'
                    : 'text-[#DDF0F5] hover:text-white hover:bg-[#1D4664]/40'
                } ${isCollapsed ? 'justify-center px-2' : ''}`}
                title={isCollapsed ? item.name : undefined}
              >
                <Icon
                  className={`w-5 h-5 shrink-0 transition-colors ${
                    isActive ? 'text-white' : 'text-[#BBDCE8]'
                  }`}
                />

                {!isCollapsed && (
                  <>
                    <span className="truncate tracking-wide">{item.name}</span>
                    {item.badge && (
                      <span className="ml-auto text-[9px] uppercase font-extrabold px-1.5 py-0.5 rounded bg-[#39C3B8]/20 text-[#8BE5DE] border border-[#39C3B8]/40">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Workspace Card matching reference image */}
      {!isCollapsed && (
        <div className="p-4 relative z-10 shrink-0">
          <div className="bg-[#0A2036]/80 backdrop-blur-md rounded-2xl border border-[#39C3B8]/30 p-3.5 shadow-elevated space-y-2">
            <div className="flex items-center gap-2">
              <Crown className="w-4 h-4 text-[#39C3B8]" />
              <span className="text-xs font-bold text-white tracking-wide">Pro Workspace</span>
            </div>

            <p className="text-[11px] text-[#BBDCE8]">
              12 / 50 Reports Used
            </p>

            <div className="w-full bg-[#102C46] h-1.5 rounded-full overflow-hidden border border-[#1D4664]/60">
              <div
                className="bg-gradient-to-r from-[#009F98] to-[#39C3B8] h-full rounded-full transition-all duration-500"
                style={{ width: '24%' }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Sticky Sidebar */}
      <aside
        className={`hidden lg:block shrink-0 transition-all duration-200 z-30 h-screen sticky top-0 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-[#0A2036]/70 backdrop-blur-xs transition-opacity"
            onClick={onMobileClose}
          />
          <div className="fixed inset-y-0 left-0 w-64 shadow-elevated z-50">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
