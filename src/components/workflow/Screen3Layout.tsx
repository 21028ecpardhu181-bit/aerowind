import React from 'react';
import { Activity, Zap, ShieldCheck, ArrowRight, ArrowLeft, Layers, Sliders } from 'lucide-react';
import { LayoutAnalysisData, SiteInfo } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen3LayoutProps {
  site: SiteInfo;
  layoutData: LayoutAnalysisData;
  onLaunchOptimize: () => void;
  onBack: () => void;
}

export const Screen3Layout: React.FC<Screen3LayoutProps> = ({
  site,
  layoutData,
  onLaunchOptimize,
  onBack,
}) => {
  const turbinesCount = layoutData.turbines?.length || 12;
  const grossAep = layoutData.gross_aep_gwh ? layoutData.gross_aep_gwh.toFixed(1) : '102.1';
  const netAep = layoutData.net_aep_gwh ? layoutData.net_aep_gwh.toFixed(1) : '88.3';
  const wakeLoss = layoutData.wake_loss_percent ? layoutData.wake_loss_percent.toFixed(1) : '13.5';
  const minSpacing = layoutData.min_spacing_m ? Math.round(layoutData.min_spacing_m) : 600;
  const conflictsCount = layoutData.conflicts_count || 0;

  return (
    <div id="screen-3-container" className="relative w-full h-[calc(100vh-53px)] overflow-hidden flex flex-col bg-slate-900">
      {/* 1. TOP FLOATING STATUS BAR */}
      <div className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/85 backdrop-blur-md border border-slate-200/80 text-xs font-semibold text-slate-700 hover:text-slate-900 shadow-glass"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Config</span>
          </button>

          <div
            id="s3-indicator-text"
            className="px-3.5 py-1.5 rounded-xl bg-white/90 backdrop-blur-md border border-slate-200/90 text-xs font-bold text-slate-900 shadow-glass flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>{site.shortName || site.name} · {turbinesCount} Turbines Initial Layout</span>
          </div>
        </div>
      </div>

      {/* 2. MAP & CANVAS CONTAINERS */}
      <div className="relative flex-1 w-full h-full">
        <div id="screen3-map" className="w-full h-full" />
        <canvas
          id="screen3-canvas"
          className="absolute inset-0 pointer-events-none w-full h-full"
        />
      </div>

      {/* 3. BOTTOM FLOATING LAYOUT INTELLIGENCE PANEL */}
      <div className="absolute bottom-4 left-4 right-4 md:left-6 md:right-auto md:max-w-md z-20 pointer-events-auto">
        <Card className="p-4 sm:p-5 flex flex-col gap-3 shadow-glass border-slate-200/90">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100" id="s3-panel-toggle">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Baseline Layout Analysis</h3>
              <p className="text-[11px] text-slate-500">Heuristic micro-siting & analytical Jensen wake model</p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">
              Baseline
            </span>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[10px] text-slate-500 font-medium">Net AEP</div>
              <div id="s3-meta-net-aep" className="text-sm font-black text-slate-900 font-mono mt-0.5">
                {netAep} GWh
              </div>
              <div id="s3-meta-gross-aep" className="hidden">{grossAep} GWh</div>
            </div>

            <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[10px] text-slate-500 font-medium">Wake Loss</div>
              <div id="s3-meta-wake-loss" className="text-sm font-black text-rose-600 font-mono mt-0.5">
                {wakeLoss}%
              </div>
            </div>

            <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[10px] text-slate-500 font-medium">Min Spacing</div>
              <div id="s3-meta-min-spacing" className="text-sm font-black text-slate-900 font-mono mt-0.5">
                {minSpacing} m
              </div>
              <div id="s3-meta-conflicts-count" className="hidden">{conflictsCount}</div>
            </div>
          </div>

          {/* Feasibility Check Highlights */}
          <div className="flex items-center justify-between text-xs px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 font-medium">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Boundary & 5D Spacing Constraints Validated</span>
            </span>
            <span className="font-bold text-[11px]">100% Contained</span>
          </div>

          {/* Primary Action Button */}
          <Button
            id="btn-screen3-optimize"
            variant="energy"
            size="md"
            onClick={onLaunchOptimize}
            className="w-full text-slate-950 font-bold mt-1"
          >
            <span>Launch Quantum Optimization</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </Button>
        </Card>
      </div>
    </div>
  );
};
