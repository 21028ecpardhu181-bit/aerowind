import React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'energy' | 'glass' | 'primary' | 'outline' | 'ghost' | 'secondary';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-xl focus:outline-none focus:ring-2 focus:ring-energy-400 focus:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none select-none';

    const variants = {
      energy: 'bg-amber-400 hover:bg-amber-500 text-slate-900 font-semibold shadow-sm hover:shadow active:scale-[0.98]',
      glass: 'bg-white/80 hover:bg-white text-slate-800 border border-slate-200/80 shadow-subtle backdrop-blur-md active:scale-[0.98]',
      primary: 'bg-slate-900 hover:bg-slate-800 text-white shadow-sm active:scale-[0.98]',
      secondary: 'bg-slate-100 hover:bg-slate-200 text-slate-900 active:scale-[0.98]',
      outline: 'border border-slate-300 hover:bg-slate-50 text-slate-700 active:scale-[0.98]',
      ghost: 'hover:bg-slate-100 text-slate-600 hover:text-slate-900',
    };

    const sizes = {
      sm: 'text-xs px-3 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2.5 gap-2',
      lg: 'text-base px-5 py-3 gap-2.5 font-semibold',
      icon: 'p-2.5 w-10 h-10',
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
