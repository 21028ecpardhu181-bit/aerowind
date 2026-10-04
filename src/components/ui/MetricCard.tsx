import React from 'react';
import { cn } from '../../lib/utils';
import { GlassPanel } from './GlassPanel';
import { Sparkline } from './Sparkline';
import { TrendingUp, TrendingDown } from 'lucide-react';

export interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  trendText?: string;
  trendDirection?: 'up' | 'down';
  trendType?: 'positive' | 'negative' | 'neutral';
  subtitle?: string;
  sparklineData?: number[];
  sparklineColor?: 'yellow' | 'blue' | 'emerald';
  className?: string;
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  icon,
  trendText,
  trendDirection = 'up',
  trendType = 'positive',
  subtitle,
  sparklineData,
  sparklineColor = 'yellow',
  className,
  onClick,
}) => {
  return (
    <GlassPanel
      variant="standard"
      className={cn(
        'p-4 sm:p-5 flex flex-col justify-between gap-3 group select-none',
        onClick && 'cursor-pointer hover:shadow-glass-hover',
        className
      )}
      onClick={onClick}
    >
      {/* Header: Icon & Title */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {icon && (
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600">
              {icon}
            </div>
          )}
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</span>
        </div>
      </div>

      {/* Main KPI Value with Tabular Numerals */}
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight tabular-nums font-mono">
          {value}
        </span>
        {unit && <span className="text-xs sm:text-sm font-semibold text-slate-500">{unit}</span>}
      </div>

      {/* Footer: Trend pill or subtitle + Sparkline */}
      <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-100/80">
        {trendText ? (
          <div
            className={cn(
              'inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full tabular-nums',
              trendType === 'positive' && 'text-emerald-700 bg-emerald-500/10',
              trendType === 'negative' && 'text-rose-700 bg-rose-500/10',
              trendType === 'neutral' && 'text-slate-600 bg-slate-500/10'
            )}
          >
            {trendDirection === 'up' ? (
              <TrendingUp className="w-3 h-3 stroke-[2.5]" />
            ) : (
              <TrendingDown className="w-3 h-3 stroke-[2.5]" />
            )}
            <span>{trendText}</span>
          </div>
        ) : subtitle ? (
          <span className="text-[11px] text-slate-500 font-medium tabular-nums">{subtitle}</span>
        ) : (
          <div />
        )}

        {/* Real Sparkline Curve */}
        <div className="w-20 sm:w-24 h-6 flex items-center justify-end">
          <Sparkline color={sparklineColor} width={80} height={24} />
        </div>
      </div>
    </GlassPanel>
  );
};
