import React from 'react';
import { Plus, Minus, Layers, Navigation, Box, Maximize2 } from 'lucide-react';
import { GlassPanel } from './GlassPanel';
import { cn } from '../../lib/utils';

export interface MapControlsProps {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onResetNorth?: () => void;
  onToggle3D?: () => void;
  is3D?: boolean;
  onFitSite?: () => void;
  onLayerChange?: () => void;
  className?: string;
}

export const MapControls: React.FC<MapControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onResetNorth,
  onToggle3D,
  is3D = false,
  onFitSite,
  onLayerChange,
  className,
}) => {
  return (
    <div className={cn('flex flex-col items-center gap-2 select-none pointer-events-auto', className)}>
      {/* Layer selector */}
      <GlassPanel variant="subtle" className="p-1 rounded-xl shadow-glass flex flex-col gap-1">
        <button
          onClick={onLayerChange}
          className="p-2 rounded-lg text-slate-700 hover:text-slate-950 hover:bg-white/80 active:scale-95 transition-all"
          title="Switch Map Layers"
          aria-label="Map Layers"
        >
          <Layers className="w-4 h-4" />
        </button>
      </GlassPanel>

      {/* Compass / 3D Toggle */}
      <GlassPanel variant="subtle" className="p-1 rounded-xl shadow-glass flex flex-col gap-1">
        <button
          onClick={onResetNorth}
          className="p-2 rounded-lg text-slate-700 hover:text-slate-950 hover:bg-white/80 active:scale-95 transition-all"
          title="Reset View to North"
          aria-label="Reset North"
        >
          <Navigation className="w-4 h-4 text-blue-600" />
        </button>
        <button
          onClick={onToggle3D}
          className={cn(
            'px-2 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95 flex items-center justify-center',
            is3D
              ? 'bg-[#FFD21F] text-slate-950 shadow-sm'
              : 'text-slate-700 hover:text-slate-950 hover:bg-white/80'
          )}
          title="Toggle 2D / 3D Mode"
          aria-label="Toggle 3D"
        >
          {is3D ? '3D' : '2D'}
        </button>
        {onFitSite && (
          <button
            onClick={onFitSite}
            className="p-2 rounded-lg text-slate-700 hover:text-slate-950 hover:bg-white/80 active:scale-95 transition-all"
            title="Fit Concession Site"
            aria-label="Fit Site"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        )}
      </GlassPanel>

      {/* Zoom In & Zoom Out */}
      <GlassPanel variant="subtle" className="p-1 rounded-xl shadow-glass flex flex-col gap-1">
        <button
          onClick={onZoomIn}
          className="p-2 rounded-lg text-slate-700 hover:text-slate-950 hover:bg-white/80 active:scale-95 transition-all"
          title="Zoom In"
          aria-label="Zoom In"
        >
          <Plus className="w-4 h-4" />
        </button>
        <div className="w-full h-px bg-slate-200/60" />
        <button
          onClick={onZoomOut}
          className="p-2 rounded-lg text-slate-700 hover:text-slate-950 hover:bg-white/80 active:scale-95 transition-all"
          title="Zoom Out"
          aria-label="Zoom Out"
        >
          <Minus className="w-4 h-4" />
        </button>
      </GlassPanel>
    </div>
  );
};
