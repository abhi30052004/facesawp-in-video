import React from 'react';
import { cn } from '../../utils/cn';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'gold' | 'burgundy' | 'emerald' | 'amber' | 'slate' | 'demo';
  size?: 'sm' | 'md';
  className?: string;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'slate',
  size = 'sm',
  className,
  icon,
}) => {
  const baseStyles = 'inline-flex items-center gap-1.5 font-medium rounded-full tracking-wide uppercase';

  const variants = {
    gold: 'bg-[#D6AD65]/15 text-[#B8822A] dark:text-[#F3DC9B] border border-[#D6AD65]/30',
    burgundy: 'bg-[#8E3048]/15 text-[#8E3048] dark:text-[#FFA8BD] border border-[#8E3048]/30',
    emerald: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30',
    amber: 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30',
    slate: 'bg-black/5 dark:bg-[#22222C] text-[#52525B] dark:text-[#A1A1AA] border border-black/10 dark:border-[#2F2F3D]',
    demo: 'bg-[#D6AD65]/15 text-[#8A5F1A] dark:text-[#F5E6C8] border border-[#D6AD65]/40 font-semibold',
  };

  const sizes = {
    sm: 'text-[10px] px-2.5 py-0.5',
    md: 'text-xs px-3 py-1',
  };

  return (
    <span className={cn(baseStyles, variants[variant], sizes[size], className)}>
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
