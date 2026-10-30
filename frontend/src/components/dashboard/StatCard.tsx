import React from 'react';
import { Card } from '../common/Card';
import { cn } from '../../utils/cn';

interface StatCardProps {
  label: string;
  value: string | number;
  subtext: string;
  icon: React.ReactNode;
  trend?: string;
  color?: 'gold' | 'burgundy' | 'slate' | 'emerald';
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  trend,
  color = 'gold',
}) => {
  const iconColors = {
    gold: 'bg-[#D6AD65]/15 text-[#D6AD65] border-[#D6AD65]/30',
    burgundy: 'bg-[#8E3048]/20 text-[#FFA8BD] border-[#8E3048]/35',
    slate: 'bg-[#21212B] text-[#A1A1AA] border-[#2E2E3E]',
    emerald: 'bg-emerald-950/40 text-emerald-300 border-emerald-700/40',
  };

  return (
    <Card hoverEffect className="p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-mono uppercase tracking-wider text-[#8E8E9E]">
          {label}
        </span>
        <div
          className={cn(
            'w-9 h-9 rounded-xl flex items-center justify-center border',
            iconColors[color]
          )}
        >
          {icon}
        </div>
      </div>

      <div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-cinematic font-bold text-white tracking-tight">
            {value}
          </span>
          {trend && (
            <span className="text-[11px] font-mono text-emerald-400 font-semibold">
              {trend}
            </span>
          )}
        </div>
        <p className="text-xs text-[#71717A] mt-1">{subtext}</p>
      </div>
    </Card>
  );
};

