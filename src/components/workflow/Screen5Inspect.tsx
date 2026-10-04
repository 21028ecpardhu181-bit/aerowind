import React, { useState } from 'react';
import { Box, Layers, Compass, ArrowRight, ArrowLeft, ChevronRight, Eye } from 'lucide-react';
import { OptimizationData, SiteInfo, Turbine } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen5InspectProps {
  site: SiteInfo;
  optimizationData: OptimizationData | null;
  onExportBlueprint: () => void;
  onBack: () => void;
  onToggle3D: () => void;
  is3DActive: boolean;
  onSelectCameraPreset: (preset: string) => void;
}

export const Screen5Inspect: React.FC<Screen5InspectProps> = ({
  site,
  optimizationData,
  onExportBlueprint,
  onBack,
  onToggle3D,
  is3DActive,
  onSelectCameraPreset,
}) => {
  const [activePreset, setActivePreset] = useState<string>('TOP');
  const [selectedTurbineIdx, setSelectedTurbineIdx] = useState<number>(0);
  const [isPanelCollapsed, setIsPanelCollapsed] = useState<boolean>(false);

  const turbines = optimizationData?.optimized_turbines || [];
  const selectedTurbine = turbines[selectedTurbineIdx] || turbines[0] || {
    id: 'T1',
    label: 'T-01',
    lat: site.lat,
    lon: site.lon,
    elevation_m: 42,
    effective_mps: 7.4,
    wake_deficit_pct: 3.2,
  };

  const handleNextTurbine = () => {
    if (turbines.length === 0) return;
    const nextIdx = (selectedTurbineIdx + 1) % turbines.length;
    setSelectedTurbineIdx(nextIdx);
  };

  const handlePresetClick = (preset: string) => {
    setActivePreset(preset);
    onSelectCameraPreset(preset);
  };

  const aep = optimizationData?.best_aep_gwh ? `${optimizationData.best_aep_gwh.toFixed(1)} GWh/year` : '88.3 GWh/year';
  const wakeLoss = optimizationData?.best_wake_loss_pct ? `${optimizationData.best_wake_loss_pct.toFixed(0)} %` : '4 %';

  return (
    <div id="screen-5-container" className="relative w-full h-[calc(100vh-53px)] overflow-hidden flex flex-col bg-slate-900">
      {/* 1. TOP FLOATING STATUS BAR & CAMERA PRESETS */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/85 backdrop-blur-md border border-slate-200/80 text-xs font-semibold text-slate-700 hover:text-slate-900 shadow-glass"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Optimize</span>
          </button>

          <div
            id="s5-indicator-text"
            className="px-3.5 py-1.5 rounded-xl bg-white/90 backdrop-blur-md border border-slate-200/90 text-xs font-bold text-slate-900 shadow-glass flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{site.shortName || site.name} · {turbines.length || 12} Turbines (QAOA)</span>
          </div>
        </div>

        {/* 3D Camera Presets Bar */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <div
            id="s5-camera-presets-bar"
            className={`flex items-center gap-1 bg-white/85 backdrop-blur-md p-1 rounded-2xl border border-slate-200/80 shadow-glass ${
              is3DActive ? 'flex' : 'hidden'
            }`}
          >
            {['TOP', 'NORTH', 'SOUTH', 'OBLIQUE', 'FIT_SITE'].map((preset) => (
              <button
                key={preset}
                type="button"
                data-preset={preset}
                onClick={() => handlePresetClick(preset)}
                className={`camera-preset-btn px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                  activePreset === preset
                    ? 'active bg-amber-400 text-slate-950 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {preset}
              </button>
            ))}
          </div>

          <button
            id="btn-s5-toggle-3d"
            onClick={onToggle3D}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-2xl font-bold text-xs border shadow-glass backdrop-blur-md transition-all active:scale-95 ${
              is3DActive
                ? 'bg-amber-400 text-slate-950 border-amber-300 shadow-md'
                : 'bg-white/85 hover:bg-white text-slate-700 border-slate-200/80'
            }`}
          >
            <Box className="w-3.5 h-3.5" />
            <span>{is3DActive ? '2D View' : '3D Globe'}</span>
          </button>
        </div>
      </div>

      {/* 2. MAP & CESIUM CONTAINERS */}
      <div className="relative flex-1 w-full h-full">
        <div id="screen5-map" className={`w-full h-full ${is3DActive ? 'hidden' : 'block'}`} />
        <canvas id="screen5-canvas" className="absolute inset-0 pointer-events-none w-full h-full" />
        <div id="screen5-cesium" className={`w-full h-full absolute inset-0 ${is3DActive ? 'block' : 'hidden'}`} />
      </div>

      {/* 3. BOTTOM FLOATING INSPECTOR PANEL */}
      <div
        id="screen-5-sheet"
        className="absolute bottom-4 left-4 right-4 md:left-6 md:right-auto md:max-w-md z-20 pointer-events-auto"
      >
        <Card className="p-4 sm:p-5 flex flex-col gap-3 shadow-glass border-slate-200/90">
          <div
            id="s5-panel-toggle"
            onClick={() => setIsPanelCollapsed(!isPanelCollapsed)}
            className="flex items-center justify-between pb-2 border-b border-slate-100 cursor-pointer select-none"
          >
            <div>
              <h3 className="text-sm font-bold text-slate-900">Optimized Farm Telemetry</h3>
              <div className="text-[11px] text-slate-500 flex items-center gap-3 mt-0.5">
                <span>AEP: <strong id="s5-meta-aep" className="text-slate-800">{aep}</strong></span>
                <span>Wake: <strong id="s5-meta-wake-loss" className="text-emerald-600">{wakeLoss}</strong></span>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
              QAOA Ready
            </span>
          </div>

          {/* Turbine Micro-Inspector */}
          <div id="s5-turbine-inspector" className="p-3 rounded-xl bg-slate-50/90 border border-slate-200/80 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span id="s5-inspector-name" className="text-xs font-black text-slate-900">
                {selectedTurbine.label || `Turbine T-${String(selectedTurbineIdx + 1).padStart(2, '0')}`}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  id="btn-s5-next-turbine"
                  type="button"
                  onClick={handleNextTurbine}
                  className="px-2 py-1 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-700 hover:bg-slate-100 shadow-2xs"
                >
                  Next Turbine
                </button>
                <button
                  id="btn-s5-fly-turbine"
                  type="button"
                  className="p-1 rounded-lg bg-amber-400 hover:bg-amber-500 text-slate-950 shadow-2xs"
                  title="Inspect in 3D"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600">
              <div>Lat: <span className="font-semibold text-slate-900">{selectedTurbine.lat.toFixed(6)}°</span></div>
              <div>Lon: <span className="font-semibold text-slate-900">{selectedTurbine.lon.toFixed(6)}°</span></div>
              <div>Elev: <span className="font-semibold text-slate-900">{selectedTurbine.elevation_m || 42} m</span></div>
              <div>Wind: <span className="font-semibold text-emerald-600">{selectedTurbine.effective_mps || 7.4} m/s</span></div>
            </div>
          </div>

          <Button
            id="btn-screen5-export"
            variant="energy"
            size="md"
            onClick={onExportBlueprint}
            className="w-full text-slate-950 font-bold mt-1"
          >
            <span>Proceed to Engineering Blueprint</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </Button>
        </Card>
      </div>
    </div>
  );
};
