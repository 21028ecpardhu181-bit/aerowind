import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps {
  status?: string;
  children?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ status = 'optimized', children, className }) => {
  const norm = status.toLowerCase();

  let dotColor = 'bg-emerald-500';
  let badgeBg = 'bg-emerald-50 border-emerald-200 text-emerald-700';
  let label = children || status;

  if (norm.includes('opt') || norm.includes('done')) {
    dotColor = 'bg-emerald-500';
    badgeBg = 'bg-emerald-50/90 border-emerald-200 text-emerald-800';
    label = children || 'Optimized';
  } else if (norm.includes('analysis') || norm.includes('simul')) {
    dotColor = 'bg-blue-500';
    badgeBg = 'bg-blue-50/90 border-blue-200 text-blue-800';
    label = children || 'Analysis Complete';
  } else if (norm.includes('draft') || norm.includes('config')) {
    dotColor = 'bg-amber-500';
    badgeBg = 'bg-amber-50/90 border-amber-200 text-amber-800';
    label = children || 'Draft';
  } else {
    dotColor = 'bg-slate-400';
    badgeBg = 'bg-slate-100 border-slate-200 text-slate-700';
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm',
        badgeBg,
        className
      )}
    >
      <span className={cn('w-2 h-2 rounded-full animate-pulse', dotColor)} />
      {label}
    </span>
  );
};
