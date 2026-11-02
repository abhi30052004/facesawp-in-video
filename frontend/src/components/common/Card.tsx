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
  style,
  ...props
}) => {
  return (
    <div
      className={cn(
        'rounded-2xl p-6 transition-all duration-300 relative border',
        hoverEffect && 'hover:-translate-y-0.5 hover:shadow-md',
        glow && 'cinema-card-glow',
        className
      )}
      style={{
        backgroundColor: 'var(--bg-card)',
        borderColor: goldBorder ? 'var(--gold)' : burgundyBorder ? 'var(--burgundy)' : 'var(--border-card)',
        color: 'var(--text-primary)',
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
};
