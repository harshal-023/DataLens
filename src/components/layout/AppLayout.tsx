import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { ModuleSubNav } from './ModuleSubNav';
import { PageUpperWave } from '../common/PageUpperWave';

export const AppLayout: React.FC = () => {
  // Global sidebar collapse state persisted across sessions and pages
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem('datalens_sidebar_collapsed');
      return stored === 'true';
    } catch {
      return false;
    }
  });

  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);
  const location = useLocation();

  // Persist sidebar preference on change
  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('datalens_sidebar_collapsed', String(next));
      } catch {
        // storage disabled fallback
      }
      return next;
    });
  };

  // Check if current route uses dedicated independent scrolling (Analytics & Dashboards, Ask AI)
  const isDashboardRoute =
    location.pathname === '/dashboard' ||
    location.pathname.startsWith('/dashboards');

  const isAskAiRoute = location.pathname.startsWith('/ask');

  const isIndependentScrollRoute = isDashboardRoute || isAskAiRoute;

  // Auto-close mobile drawer on route navigation
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  return (
    <div className="h-screen w-screen bg-[#F5F8FA] text-[#102C46] flex flex-col lg:flex-row font-sans overflow-hidden select-none">
      {/* Sidebar (Desktop persistent with global collapse + Mobile drawer) */}
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={handleToggleCollapse}
        isMobileOpen={isMobileOpen}
        onMobileClose={() => setIsMobileOpen(false)}
      />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative select-auto">
        {/* Fixed Top Navbar */}
        <TopNavbar onOpenMobileMenu={() => setIsMobileOpen(true)} />

        {/* Viewport Content Container */}
        <div
          className={`flex-1 min-h-0 relative ${
            isIndependentScrollRoute
              ? 'overflow-hidden flex flex-col'
              : 'overflow-y-auto'
          }`}
        >
          {/* Signature Upper Flowing Peacock Wave */}
          <PageUpperWave />

          {/* Page Outlet content rendered cleanly above the background wave */}
          <main
            className={`relative z-10 w-full ${
              isIndependentScrollRoute
                ? 'h-full flex flex-col min-h-0 p-3 sm:p-4 lg:p-6 max-w-[1700px] mx-auto'
                : 'p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto'
            }`}
          >
            {/* Show ModuleSubNav on standard overview pages, but allow dedicated full-canvas dashboards */}
            {!isDashboardRoute && <ModuleSubNav />}
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};

