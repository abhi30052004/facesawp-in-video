import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, Plus, ShieldCheck, Activity } from 'lucide-react';
import { Button } from '../common/Button';
import { useSettings } from '../../context/SettingsContext';

interface HeaderProps {
  onToggleMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleMobileMenu }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { settings } = useSettings();

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return { title: 'Studio Production Hub', tag: 'Directorial Dashboard' };
      case '/create':
        return { title: 'New Face Swap Studio', tag: 'Neural Pipeline Wizard' };
      case '/projects':
        return { title: 'Film Roster & Archive', tag: 'Project History' };
      case '/settings':
        return { title: 'Studio Settings & API', tag: 'Engine Preferences' };
      default:
        return { title: 'BollySwap Studio', tag: 'Cinematic AI' };
    }
  };

  const current = getPageTitle();

  return (
    <header className="sticky top-0 z-30 h-20 bg-[#09090B]/90 backdrop-blur-xl border-b border-[#20202B] px-4 sm:px-8 flex items-center justify-between">
      {/* Left Title / Hamburger */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleMobileMenu}
          aria-label="Toggle navigation menu"
          className="lg:hidden p-2 rounded-xl text-[#A1A1AA] hover:text-white hover:bg-[#1A1A22] transition-colors cursor-pointer"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg sm:text-xl font-cinematic font-bold text-white tracking-wide">
              {current.title}
            </h1>
            <span className="hidden md:inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#1A1A24] border border-[#2B2B38] text-[#D6AD65]">
              <ShieldCheck className="w-3 h-3 text-[#D6AD65]" />
              {current.tag}
            </span>
          </div>
          <p className="text-xs text-[#8E8E9E] hidden sm:block">
            High-fidelity Bollywood neural re-targeting & temporal frame harmonization
          </p>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* API Backend status badge */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#14141B] border border-[#262635] text-xs">
          <Activity
            className={`w-3.5 h-3.5 ${
              settings.apiConfig.useLiveBackend ? 'text-emerald-400 animate-pulse' : 'text-[#D6AD65]'
            }`}
          />
          <span className="text-[#A1A1AA] text-[11px]">
            {settings.apiConfig.useLiveBackend ? 'FastAPI Connected' : 'Frontend Demo Mode'}
          </span>
        </div>

        {/* New Face Swap CTA (hidden if already on create page) */}
        {location.pathname !== '/create' && (
          <Button
            size="sm"
            variant="primary"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => navigate('/create')}
            className="shadow-sm"
          >
            <span className="hidden sm:inline">New Face Swap</span>
            <span className="sm:hidden">New Swap</span>
          </Button>
        )}

        {/* Profile Pill */}
        <div
          onClick={() => navigate('/settings')}
          className="flex items-center gap-2.5 p-1.5 pr-3 rounded-xl bg-[#16161E] border border-[#272736] hover:border-[#D6AD65]/40 transition-colors cursor-pointer"
        >
          <img
            src={settings.profile.avatarUrl}
            alt={settings.profile.name}
            className="w-8 h-8 rounded-lg object-cover border border-[#D6AD65]/40"
          />
          <div className="hidden xl:flex flex-col text-left">
            <span className="text-xs font-semibold text-white leading-tight">
              {settings.profile.name}
            </span>
            <span className="text-[10px] text-[#D6AD65] font-mono leading-tight">
              {settings.profile.role.split('&')[0]}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
