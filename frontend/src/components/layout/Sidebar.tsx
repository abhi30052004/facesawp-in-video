import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Clapperboard,
  Film,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Zap,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useProjects } from '../../context/ProjectContext';

interface SidebarProps {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, setMobileOpen }) => {
  const [collapsed, setCollapsed] = useState(false);
  const { stats } = useProjects();

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
          className="fixed inset-0 bg-[#09090B]/80 backdrop-blur-sm z-40 lg:hidden"
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
          'fixed top-0 bottom-0 left-0 z-40 flex flex-col bg-[#111116] border-r border-[#242430] transition-transform duration-300 lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Brand Header */}
        <div className="h-20 flex items-center justify-between px-5 border-b border-[#22222E]">
          <NavLink
            to="/"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-3 overflow-hidden group"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D6AD65] via-[#8E3048] to-[#591C2B] p-0.5 shrink-0 shadow-[0_0_15px_rgba(214,173,101,0.25)] group-hover:shadow-[0_0_20px_rgba(214,173,101,0.4)] transition-shadow">
              <div className="w-full h-full bg-[#0E0E12] rounded-[10px] flex items-center justify-center">
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
                  <span className="font-cinematic font-bold text-base tracking-wider text-white flex items-center gap-1.5">
                    BollySwap <span className="text-[#D6AD65] text-xs font-sans px-1.5 py-0.5 rounded bg-[#D6AD65]/15 border border-[#D6AD65]/30">AI</span>
                  </span>
                  <span className="text-[10px] text-[#8E8E9E] tracking-widest uppercase font-mono">
                    Cinematic Studio
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </NavLink>

          {/* Desktop Collapse Button */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-[#8E8E9E] hover:text-white hover:bg-[#1E1E28] transition-colors cursor-pointer"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-sm font-medium transition-all group relative',
                    isActive
                      ? 'bg-gradient-to-r from-[#D6AD65]/15 via-[#8E3048]/10 to-transparent text-[#F4DE9C] border-l-4 border-[#D6AD65] shadow-sm'
                      : 'text-[#9D9DAE] hover:text-[#EDEDED] hover:bg-[#191922]'
                  )
                }
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

        {/* Quota & Studio Status Card */}
        <div className="p-3 border-t border-[#22222E]">
          {!collapsed ? (
            <div className="bg-[#181820] border border-[#2A2A38] rounded-xl p-3.5 relative overflow-hidden">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[#D6AD65] flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 fill-[#D6AD65]" />
                  Render Credits
                </span>
                <span className="text-xs font-mono font-medium text-white">
                  {stats.creditsRemaining}/{stats.creditsTotal}
                </span>
              </div>
              <div className="w-full bg-[#242432] h-1.5 rounded-full overflow-hidden mb-2.5">
                <div
                  className="bg-gradient-to-r from-[#D6AD65] to-[#8E3048] h-full rounded-full transition-all duration-500"
                  style={{ width: `${(stats.creditsRemaining / stats.creditsTotal) * 100}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] text-[#8E8E9E]">
                <span>{stats.currentTier}</span>
                <span className="text-[#D6AD65] hover:underline cursor-pointer">Tier Details</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center py-2 text-[#D6AD65]">
              <Sparkles className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-mono">{stats.creditsRemaining}</span>
            </div>
          )}
        </div>
      </motion.aside>
    </>
  );
};

