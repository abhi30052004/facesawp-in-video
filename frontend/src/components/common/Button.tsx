import React from 'react';
import { cn } from '../../utils/cn';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'burgundy' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  leftIcon,
  rightIcon,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 select-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#09090B] disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.98]';

  const variants = {
    primary:
      'bg-gradient-to-r from-[#D6AD65] via-[#E2C07F] to-[#C99C4E] text-[#09090B] font-semibold hover:shadow-[0_0_20px_rgba(214,173,101,0.35)] hover:brightness-105 focus-visible:ring-[#D6AD65]',
    secondary:
      'bg-[#1F1F27] hover:bg-[#2A2A35] text-[#EDEDED] border border-[#2D2D3B] hover:border-[#3E3E50] focus-visible:ring-[#D6AD65]',
    burgundy:
      'bg-gradient-to-r from-[#8E3048] to-[#6E2235] text-white hover:shadow-[0_0_20px_rgba(142,48,72,0.4)] hover:brightness-110 focus-visible:ring-[#8E3048]',
    outline:
      'border border-[#D6AD65]/40 hover:border-[#D6AD65] text-[#D6AD65] hover:bg-[#D6AD65]/10 focus-visible:ring-[#D6AD65]',
    ghost:
      'text-[#A1A1AA] hover:text-[#EDEDED] hover:bg-[#1C1C24] focus-visible:ring-white/20',
    danger:
      'bg-red-950/40 text-red-300 border border-red-800/50 hover:bg-red-900/50 focus-visible:ring-red-500',
  };

  const sizes = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2.5 gap-2',
    lg: 'text-base px-6 py-3.5 gap-2.5',
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="w-4 h-4 animate-spin shrink-0" /> : leftIcon}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};

