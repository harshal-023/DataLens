import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { PageUpperWave } from '../common/PageUpperWave';

export const AppLayout: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#F5F8FA] text-[#102C46] flex flex-col lg:flex-row font-sans relative">
      {/* Sidebar (Desktop persistent + Mobile drawer) */}
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        isMobileOpen={isMobileOpen}
        onMobileClose={() => setIsMobileOpen(false)}
      />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden relative">
        {/* Top Navbar */}
        <TopNavbar onOpenMobileMenu={() => setIsMobileOpen(true)} />

        {/* Page Content Viewport with Signature Upper Wave in background */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto relative">
          {/* Signature Upper Flowing Peacock Wave */}
          <PageUpperWave />

          {/* Page Outlet content rendered cleanly above the background wave */}
          <div className="relative z-10">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
