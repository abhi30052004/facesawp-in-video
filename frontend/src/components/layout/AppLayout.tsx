import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { StudioStatusFooter } from './StudioStatusFooter';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen text-[var(--text-primary)] flex flex-col font-sans relative" style={{ backgroundColor: 'var(--bg-page)' }}>
      <div className="flex flex-1 relative">
        {/* Sidebar */}
        <Sidebar
          mobileOpen={mobileMenuOpen}
          setMobileOpen={setMobileMenuOpen}
          collapsed={collapsed}
          setCollapsed={setCollapsed}
        />

        {/* Content Wrapper */}
        <div
          className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${
            collapsed ? 'lg:pl-[80px]' : 'lg:pl-[260px]'
          }`}
        >
          {/* Header */}
          <Header onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)} />

          {/* Page Body with Studio Backlight */}
          <main className="flex-1 p-4 sm:p-6 lg:p-8 relative">
            <div className="ambient-cinema-lights" />
            <div className="relative z-10 max-w-7xl mx-auto">
              <Outlet />
            </div>
          </main>

          {/* Footer */}
          <StudioStatusFooter />
        </div>
      </div>
    </div>
  );
};
