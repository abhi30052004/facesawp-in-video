import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { StudioStatusFooter } from './StudioStatusFooter';
import { DemoBanner } from '../common/DemoBanner';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#09090B] text-[#EDEDED] flex flex-col font-sans relative selection:bg-[#D6AD65]/30 selection:text-[#FFF5DC]">
      {/* Disclaimer / Demo Banner */}
      <DemoBanner />

      <div className="flex flex-1 relative">
        {/* Sidebar */}
        <Sidebar mobileOpen={mobileMenuOpen} setMobileOpen={setMobileMenuOpen} />

        {/* Content Wrapper */}
        <div className="flex-1 flex flex-col min-w-0 lg:pl-[260px] transition-all duration-300">
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

