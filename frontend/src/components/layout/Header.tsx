import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, Plus, Sun, Moon } from 'lucide-react';
import { Button } from '../common/Button';
import { useTheme } from '../../context/ThemeContext';

interface HeaderProps {
  onToggleMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleMobileMenu }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return { title: 'Dashboard', sub: 'Overview of your projects and activity' };
      case '/create':
        return { title: 'New Face Swap', sub: 'Upload a video and choose a target face' };
      case '/projects':
        return { title: 'My Projects', sub: 'Your saved face swap projects' };
      case '/settings':
        return { title: 'Settings', sub: 'Configure your processing preferences' };
      default:
        return { title: 'FaceSwap AI', sub: '' };
    }
  };

  const current = getPageTitle();

  return (
    <header
      className="sticky top-0 z-30 h-20 backdrop-blur-xl border-b px-4 sm:px-8 flex items-center justify-between transition-colors duration-200"
      style={{
        backgroundColor: 'var(--bg-header)',
        borderColor: 'var(--border)',
      }}
    >
      {/* Left: Hamburger + Title */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleMobileMenu}
          aria-label="Toggle navigation menu"
          className="lg:hidden p-2 rounded-xl transition-colors cursor-pointer"
          style={{ color: 'var(--text-secondary)' }}
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h1
            className="text-lg sm:text-xl font-cinematic font-bold tracking-wide"
            style={{ color: 'var(--text-primary)' }}
          >
            {current.title}
          </h1>
          {current.sub && (
            <p className="text-xs hidden sm:block" style={{ color: 'var(--text-faint)' }}>
              {current.sub}
            </p>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          className="w-9 h-9 rounded-xl flex items-center justify-center transition-colors cursor-pointer"
          style={{
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            backgroundColor: 'var(--bg-card)',
          }}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* New Face Swap CTA */}
        {location.pathname !== '/create' && (
          <Button
            size="sm"
            variant="primary"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => navigate('/create')}
            className="shadow-sm"
          >
            <span className="hidden sm:inline">New Face Swap</span>
            <span className="sm:hidden">New</span>
          </Button>
        )}
      </div>
    </header>
  );
};
