import React from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: boolean;
  goldBorder?: boolean;
  burgundyBorder?: boolean;
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  glow = false,
  goldBorder = false,
  burgundyBorder = false,
  hoverEffect = false,
  ...props
}) => {
  return (
    <div
      className={cn(
        'bg-[#17171C] border border-[#272733] rounded-2xl p-6 transition-all duration-300 relative',
        hoverEffect && 'hover:border-[#383849] hover:bg-[#1A1A22] hover:-translate-y-0.5',
        goldBorder && 'border-[#D6AD65]/30 hover:border-[#D6AD65]/60',
        burgundyBorder && 'border-[#8E3048]/35 hover:border-[#8E3048]/60',
        glow && 'cinema-card-glow',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

