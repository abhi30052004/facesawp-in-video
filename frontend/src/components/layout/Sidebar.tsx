import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Clapperboard,
  Film,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../../utils/cn';

interface SidebarProps {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  collapsed: boolean;
  setCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
}

export const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen,
  setMobileOpen,
  collapsed,
  setCollapsed,
}) => {
  const navItems = [
    {
      name: 'Dashboard',
      path: '/',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      name: 'Create Project',
      path: '/create',
      icon: Clapperboard,
      badge: 'New',
    },
    {
      name: 'My Projects',
      path: '/projects',
      icon: Film,
      badge: null,
    },
    {
      name: 'Settings',
      path: '/settings',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main Sidebar */}
      <motion.aside
        animate={{
          width: collapsed ? 80 : 260,
        }}
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        className={cn(
          'fixed top-0 bottom-0 left-0 z-40 flex flex-col border-r transition-transform duration-300 lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        style={{
          backgroundColor: 'var(--bg-sidebar)',
          borderColor: 'var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        {/* Brand Header */}
        <div
          className={cn(
            'h-20 flex items-center border-b transition-all duration-200',
            collapsed ? 'justify-center px-0' : 'justify-between px-5'
          )}
          style={{ borderColor: 'var(--border)' }}
        >
          <NavLink
            to="/"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-3 group"
          >
            {/* Clapperboard Logo */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D6AD65] via-[#8E3048] to-[#591C2B] p-0.5 shrink-0 shadow-sm transition-shadow">
              <div
                className="w-full h-full rounded-[10px] flex items-center justify-center"
                style={{ backgroundColor: 'var(--bg-card)' }}
              >
                <Clapperboard className="w-5 h-5 text-[#D6AD65] group-hover:scale-110 transition-transform" />
              </div>
            </div>

            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.15 }}
                  className="flex flex-col whitespace-nowrap"
                >
                  <span
                    className="font-cinematic font-bold text-base tracking-wider flex items-center gap-1.5"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    FaceSwap <span className="text-[#D6AD65] text-xs font-sans px-1.5 py-0.5 rounded bg-[#D6AD65]/15 border border-[#D6AD65]/30">AI</span>
                  </span>
                  <span
                    className="text-[10px] tracking-widest uppercase font-mono"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Video Studio
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </NavLink>

          {/* Top Collapse Button (only visible when expanded on desktop) */}
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              aria-label="Collapse sidebar"
              className="hidden lg:flex items-center justify-center w-8 h-8 rounded-lg transition-colors cursor-pointer hover:opacity-80"
              style={{ color: 'var(--text-muted)' }}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Navigation Links */}
        <div className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                title={collapsed ? item.name : undefined}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'flex items-center rounded-xl text-sm font-medium transition-all group relative',
                    collapsed ? 'justify-center w-11 h-11 mx-auto' : 'gap-3.5 px-3.5 py-3',
                    isActive
                      ? 'bg-gradient-to-r from-[#D6AD65]/20 via-[#8E3048]/15 to-transparent text-[#D6AD65] border-l-4 border-[#D6AD65] shadow-sm font-semibold'
                      : 'hover:opacity-100 opacity-80 hover:bg-black/5 dark:hover:bg-white/5'
                  )
                }
                style={({ isActive }) => ({
                  color: isActive ? 'var(--gold)' : 'var(--text-secondary)',
                })}
              >
                <Icon className="w-5 h-5 shrink-0 transition-transform group-hover:scale-110" />
                {!collapsed && (
                  <span className="truncate flex-1">{item.name}</span>
                )}
                {!collapsed && item.badge && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#8E3048] text-white">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Bottom Collapse/Expand Footer Button */}
        <div className="p-3 border-t hidden lg:block" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn(
              'w-full flex items-center rounded-xl transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/5',
              collapsed ? 'justify-center w-11 h-11 mx-auto' : 'gap-3 px-3.5 py-2.5'
            )}
            style={{ color: 'var(--text-muted)' }}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            {!collapsed && <span className="text-xs font-medium">Collapse</span>}
          </button>
        </div>
      </motion.aside>
    </>
  );
};
