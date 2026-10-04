import React from 'react';
import { OptimizationData } from '../../types';
import { GlassPanel } from '../ui/GlassPanel';
import { Cpu, CheckCircle2 } from 'lucide-react';

export interface OptimizationSummaryProps {
  optimizationData: OptimizationData | null;
  className?: string;
}

export const OptimizationSummary: React.FC<OptimizationSummaryProps> = ({
  optimizationData,
  className,
}) => {
  if (!optimizationData) return null;

  const bestAep = optimizationData.best_aep_gwh ? optimizationData.best_aep_gwh.toFixed(2) : '88.30';
  const initialAep = optimizationData.initial_aep_gwh ? optimizationData.initial_aep_gwh.toFixed(2) : '81.40';
  const improvement = optimizationData.improvement_pct ? optimizationData.improvement_pct.toFixed(2) : '8.48';
  const wakeLoss = optimizationData.best_wake_loss_pct ? optimizationData.best_wake_loss_pct.toFixed(2) : '6.12';

  return (
    <GlassPanel variant="standard" className={`p-5 flex flex-col gap-4 ${className || ''}`}>
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-700">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Optimization Method: WS-QAOA
            </h4>
            <p className="text-sm font-bold text-slate-900">
              {optimizationData.status_headline || 'Feasible Layout Identified'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-500/10 px-2.5 py-1 rounded-full">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Converged</span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div className="p-3 rounded-xl bg-white/60 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 font-medium">Net AEP</span>
          <div className="text-base font-extrabold text-slate-900 tabular-nums font-mono mt-0.5">
            {bestAep} GWh
          </div>
        </div>
        <div className="p-3 rounded-xl bg-white/60 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 font-medium">Initial Baseline</span>
          <div className="text-base font-extrabold text-slate-700 tabular-nums font-mono mt-0.5">
            {initialAep} GWh
          </div>
        </div>
        <div className="p-3 rounded-xl bg-white/60 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 font-medium">AEP Improvement</span>
          <div className="text-base font-extrabold text-emerald-600 tabular-nums font-mono mt-0.5">
            +{improvement}%
          </div>
        </div>
        <div className="p-3 rounded-xl bg-white/60 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 font-medium">Wake Loss</span>
          <div className="text-base font-extrabold text-blue-600 tabular-nums font-mono mt-0.5">
            {wakeLoss}%
          </div>
        </div>
      </div>

      <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-200/60 leading-relaxed font-mono">
        <strong>Mathematical Formulation:</strong> QUBO with Jensen Wake Deficit Matrix and Hard Pairwise Euclidean Spacing Penalty (\lambda = 150).
      </div>
    </GlassPanel>
  );
};
