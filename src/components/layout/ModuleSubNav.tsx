import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Database,
  Cable,
  Workflow,
  LayoutDashboard,
  Layers,
  Sparkles,
  Compass,
  MessageSquare,
  FlaskConical,
  FileText,
  FilePlus,
  Settings as SettingsIcon,
  Users,
  Activity,
  Shield,
  RefreshCw,
} from 'lucide-react';

interface SubNavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
}

interface ModuleConfig {
  title: string;
  badge?: string;
  description: string;
  items: SubNavItem[];
}

export const ModuleSubNav: React.FC = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  let activeModule: ModuleConfig | null = null;

  // 1. Data Management Module
  if (
    currentPath.startsWith('/data') ||
    currentPath.startsWith('/data-sources') ||
    currentPath.startsWith('/data-preparation')
  ) {
    activeModule = {
      title: 'Data Management',
      description: 'Ingest, profile, clean, and manage datasets and external data sources',
      items: [
        { name: 'Datasets & Library', path: '/data', icon: Database, exact: true },
        { name: 'External Connections', path: '/data-sources', icon: Cable },
        { name: 'Data Prep & Cleaning', path: '/data-preparation', icon: Workflow },
      ],
    };
  }
  // 2. Analytics & Dashboards Module
  else if (
    currentPath === '/dashboard' ||
    currentPath.startsWith('/dashboards') ||
    currentPath.startsWith('/advanced-analytics')
  ) {
    activeModule = {
      title: 'Analytics & Dashboards',
      description: 'Interactive visualization, KPI tracking, and multi-dimensional analytics',
      items: [
        { name: 'Overview', path: '/dashboard', icon: LayoutDashboard, exact: true },
        { name: 'Dashboards', path: '/dashboards', icon: Layers },
        { name: 'Advanced ML & Forecasting', path: '/advanced-analytics', icon: Sparkles },
      ],
    };
  }
  // 3. AI Data Analyst Module
  else if (
    currentPath.startsWith('/business-analyst') ||
    currentPath.startsWith('/ask') ||
    currentPath.startsWith('/prompt-lab')
  ) {
    activeModule = {
      title: 'AI Data Analyst',
      badge: 'Unified Intelligence',
      description: 'Autonomous risk discovery, natural language analytics, and evidence synthesis',
      items: [
        { name: 'Autonomous Insights & Risks', path: '/business-analyst', icon: Compass },
        { name: 'Ask Your Data', path: '/ask', icon: MessageSquare },
        { name: 'Prompt Lab & Benchmarks', path: '/prompt-lab', icon: FlaskConical },
      ],
    };
  }
  // 4. Reports Module
  else if (currentPath.startsWith('/reports')) {
    activeModule = {
      title: 'Reports',
      description: 'Assemble executive summaries and export multi-format business reports',
      items: [
        { name: 'Report Library', path: '/reports', icon: FileText, exact: true },
        { name: 'Create Report', path: '/reports/new', icon: FilePlus },
      ],
    };
  }
  // 5. Workspace & Settings Module
  else if (
    currentPath.startsWith('/settings') ||
    currentPath.startsWith('/workspaces') ||
    currentPath.startsWith('/activity') ||
    currentPath.startsWith('/governance') ||
    currentPath.startsWith('/automation')
  ) {
    activeModule = {
      title: 'Workspace & Settings',
      description: 'Manage members, security governance, automation schedules, and platform settings',
      items: [
        { name: 'Settings', path: '/settings', icon: SettingsIcon, exact: true },
        { name: 'Team Members', path: '/workspaces/members', icon: Users },
        { name: 'Activity Stream', path: '/activity', icon: Activity },
        { name: 'Governance & Security', path: '/governance', icon: Shield },
        { name: 'Automation & Jobs', path: '/automation', icon: RefreshCw },
      ],
    };
  }

  if (!activeModule) return null;

  return (
    <div className="mb-6 bg-white rounded-2xl border border-[#DCE5EB] p-2 sm:p-2.5 shadow-2xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-2 py-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-[#102C46] tracking-tight uppercase">
            {activeModule.title}
          </span>
          {activeModule.badge && (
            <span className="text-[10px] font-bold text-[#007D78] bg-[#EDF7FA] border border-[#BBDCE8] px-2 py-0.5 rounded-full">
              {activeModule.badge}
            </span>
          )}
        </div>

        {/* Sub-Navigation Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
          {activeModule.items.map((item) => {
            const Icon = item.icon;
            const isMatch = item.exact
              ? currentPath === item.path
              : currentPath === item.path || currentPath.startsWith(item.path + '/');

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                  isMatch
                    ? 'bg-[#102C46] text-white shadow-2xs font-bold'
                    : 'text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6]'
                }`}
              >
                <Icon
                  className={`w-3.5 h-3.5 ${
                    isMatch ? 'text-[#39C3B8]' : 'text-[#52616C]'
                  }`}
                />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>
      </div>
    </div>
  );
};
