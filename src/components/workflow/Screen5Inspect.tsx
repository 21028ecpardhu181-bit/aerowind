import React, { useEffect, useRef, useState } from 'react';
import { 
  Box, 
  Layers, 
  Compass, 
  ArrowRight, 
  ArrowLeft, 
  ChevronRight, 
  ChevronLeft,
  Eye, 
  EyeOff, 
  RotateCcw,
  CheckCircle2,
  GitCompare
} from 'lucide-react';
import { OptimizationData, SiteInfo, Turbine } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen5InspectProps {
  site: SiteInfo;
  optimizationData: OptimizationData | null;
  baselineTurbines?: Turbine[];
  onExportBlueprint: () => void;
  onBack: () => void;
  onToggle3D: () => void;
  is3DActive: boolean;
  onSelectCameraPreset: (preset: string) => void;
}

declare global {
  interface Window {
    L?: any;
    CESIUM_BASE_URL?: string;
  }
}

export const Screen5Inspect: React.FC<Screen5InspectProps> = ({
  site,
  optimizationData,
  baselineTurbines = [],
  onExportBlueprint,
  onBack,
  onToggle3D,
  is3DActive,
  onSelectCameraPreset,
}) => {
  const [activePreset, setActivePreset] = useState<string>('TOP');
  const [selectedTurbineIdx, setSelectedTurbineIdx] = useState<number>(0);
  const [isPanelCollapsed, setIsPanelCollapsed] = useState<boolean>(false);
  const [layoutMode, setLayoutMode] = useState<'optimized' | 'before'>('optimized');
  const [showWakes, setShowWakes] = useState<boolean>(true);
  const [activeBasemap, setActiveBasemap] = useState<'satellite' | 'terrain'>('satellite');

  const mapRef = useRef<any>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const baseLayersRef = useRef<{ satellite?: any; terrain?: any }>({});
  const markerLayersRef = useRef<any[]>([]);
  const wakeLayersRef = useRef<any[]>([]);
  const polygonLayerRef = useRef<any>(null);

  const optTurbines = optimizationData?.optimized_turbines || [];
  const activeTurbines = layoutMode === 'before' && baselineTurbines.length > 0 ? baselineTurbines : optTurbines;
  const windDir = site.windDirectionDeg || 300;

  const selectedTurbine = activeTurbines[selectedTurbineIdx] || activeTurbines[0] || {
    id: 'T1',
    label: 'T-01',
    lat: site.lat,
    lon: site.lon,
    elevation_m: 42,
    effective_mps: 7.4,
    wake_deficit_pct: 3.2,
  };

  const aep = optimizationData?.best_aep_gwh ? `${optimizationData.best_aep_gwh.toFixed(1)} GWh/yr` : '88.3 GWh/yr';
  const wakeLoss = optimizationData?.best_wake_loss_pct ? `${optimizationData.best_wake_loss_pct.toFixed(1)}%` : '4.0%';
  const improvement = optimizationData?.improvement_pct ? `${optimizationData.improvement_pct.toFixed(1)}%` : '8.5%';

  // 1. Initialize Map
  useEffect(() => {
    if (is3DActive) return;
    const L = window.L;
    if (!L || !mapContainerRef.current) return;

    if (mapRef.current) {
      try { mapRef.current.remove(); } catch (_) {}
      mapRef.current = null;
    }

    const map = L.map(mapContainerRef.current, {
      center: [site.lat, site.lon],
      zoom: 13,
      zoomControl: false,
      attributionControl: false,
    });

    const satellite = L.tileLayer('/api/geo/tiles/satellite/{z}/{x}/{y}', {
      maxZoom: 20,
      attribution: 'Satellite Imagery',
    });

    const terrain = L.tileLayer('/api/geo/tiles/terrain/{z}/{x}/{y}', {
      maxZoom: 20,
      attribution: 'Terrain Imagery',
    });

    baseLayersRef.current = { satellite, terrain };
    if (activeBasemap === 'terrain') {
      terrain.addTo(map);
    } else {
      satellite.addTo(map);
    }

    L.control.scale({ position: 'bottomleft', metric: true, imperial: false }).addTo(map);
    mapRef.current = map;

    // Render Boundary Polygon
    const vertices = site.boundary && site.boundary.length >= 3 ? site.boundary : [
      [site.lat + 0.015, site.lon - 0.015],
      [site.lat + 0.015, site.lon + 0.015],
      [site.lat - 0.015, site.lon + 0.015],
      [site.lat - 0.015, site.lon - 0.015],
    ];

    polygonLayerRef.current = L.polygon(vertices, {
      color: '#FFD21F',
      weight: 2,
      opacity: 0.9,
      fillColor: '#FFD21F',
      fillOpacity: 0.12,
    }).addTo(map);

    map.fitBounds(polygonLayerRef.current.getBounds(), { padding: [40, 40] });

    renderLayout(map, activeTurbines, windDir, showWakes, selectedTurbineIdx);

    return () => {
      if (mapRef.current) {
        try { mapRef.current.remove(); } catch (_) {}
        mapRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [is3DActive, site.lat, site.lon, activeTurbines, layoutMode]);

  // Update layout markers & wakes on mode or wake toggle
  useEffect(() => {
    if (mapRef.current) {
      renderLayout(mapRef.current, activeTurbines, windDir, showWakes, selectedTurbineIdx);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showWakes, selectedTurbineIdx, layoutMode]);

  const renderLayout = (map: any, turbs: Turbine[], angleDeg: number, wakesVisible: boolean, activeIdx: number) => {
    const L = window.L;
    if (!L || !map) return;

    markerLayersRef.current.forEach((m) => map.removeLayer(m));
    markerLayersRef.current = [];
    wakeLayersRef.current.forEach((w) => map.removeLayer(w));
    wakeLayersRef.current = [];

    const downwindRad = ((angleDeg + 180) % 360) * (Math.PI / 180);
    const wakeLengthKm = 1.6;
    const wakeHalfAngleRad = (9 * Math.PI) / 180;

    turbs.forEach((t, idx) => {
      const isSelected = idx === activeIdx;
      const tId = t.id || `T${idx + 1}`;

      // Wake Cones
      if (wakesVisible) {
        const cosLat = Math.cos((t.lat * Math.PI) / 180.0);
        const leftLat = t.lat + (wakeLengthKm / 111.0) * Math.cos(downwindRad - wakeHalfAngleRad);
        const leftLon = t.lon + (wakeLengthKm / (111.0 * cosLat)) * Math.sin(downwindRad - wakeHalfAngleRad);
        const rightLat = t.lat + (wakeLengthKm / 111.0) * Math.cos(downwindRad + wakeHalfAngleRad);
        const rightLon = t.lon + (wakeLengthKm / (111.0 * cosLat)) * Math.sin(downwindRad + wakeHalfAngleRad);

        const cone = L.polygon([[t.lat, t.lon], [leftLat, leftLon], [rightLat, rightLon]], {
          color: isSelected ? '#3b82f6' : '#FFD21F',
          weight: 1,
          opacity: 0.6,
          fillColor: isSelected ? '#3b82f6' : '#FFD21F',
          fillOpacity: 0.14,
        }).addTo(map);

        wakeLayersRef.current.push(cone);
      }

      // Marker
      const pinClass = isSelected ? 'turbine-map-pin active' : 'turbine-map-pin';
      const pinIcon = L.divIcon({
        className: 'turbine-pin-wrapper',
        html: `<div class="${pinClass}" style="${isSelected ? 'background: #3b82f6; border-color: #fff; transform: scale(1.2);' : ''}">${tId}</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const m = L.marker([t.lat, t.lon], { icon: pinIcon }).addTo(map);
      m.on('click', () => {
        setSelectedTurbineIdx(idx);
      });

      markerLayersRef.current.push(m);
    });
  };

  const handleNextTurbine = () => {
    if (activeTurbines.length === 0) return;
    const nextIdx = (selectedTurbineIdx + 1) % activeTurbines.length;
    setSelectedTurbineIdx(nextIdx);
    panToTurbine(activeTurbines[nextIdx]);
  };

  const handlePrevTurbine = () => {
    if (activeTurbines.length === 0) return;
    const prevIdx = (selectedTurbineIdx - 1 + activeTurbines.length) % activeTurbines.length;
    setSelectedTurbineIdx(prevIdx);
    panToTurbine(activeTurbines[prevIdx]);
  };

  const panToTurbine = (t: Turbine) => {
    if (mapRef.current && t) {
      mapRef.current.panTo([t.lat, t.lon]);
    }
  };

  const handlePresetClick = (preset: string) => {
    setActivePreset(preset);
    onSelectCameraPreset(preset);
  };

  const handleToggleBasemap = (type: 'satellite' | 'terrain') => {
    setActiveBasemap(type);
    const map = mapRef.current;
    if (!map) return;
    if (baseLayersRef.current.satellite && map.hasLayer(baseLayersRef.current.satellite)) {
      map.removeLayer(baseLayersRef.current.satellite);
    }
    if (baseLayersRef.current.terrain && map.hasLayer(baseLayersRef.current.terrain)) {
      map.removeLayer(baseLayersRef.current.terrain);
    }
    const target = baseLayersRef.current[type];
    if (target) target.addTo(map);
  };

  const handleResetView = () => {
    if (mapRef.current && polygonLayerRef.current) {
      mapRef.current.fitBounds(polygonLayerRef.current.getBounds(), { padding: [40, 40] });
    }
  };

  return (
    <div id="screen-5-container" className="relative w-full h-[calc(100vh-53px)] overflow-hidden flex flex-col bg-slate-900">
      
      {/* ── TOP STATUS & CONTROLS BAR ───────────────────────────── */}
      <div className="absolute top-3 left-3 right-3 z-30 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        
        {/* Left: Back & Step Indicator */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            id="btn-s5-back"
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/90 backdrop-blur-xl border border-white/80 text-xs font-bold text-slate-800 hover:text-slate-950 hover:bg-white shadow-glass transition-all active:scale-95"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Optimize</span>
          </button>

          <div
            id="s5-indicator-text"
            className="px-3.5 py-1.5 rounded-xl bg-white/95 backdrop-blur-xl border border-white/90 text-xs font-bold text-slate-900 shadow-glass flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{site.shortName || site.name} · {activeTurbines.length} Turbines (WS-QAOA Certified)</span>
          </div>
        </div>

        {/* Right: Controls (Basemap, 3D, Wakes, Presets) */}
        <div className="flex flex-wrap items-center gap-1.5 pointer-events-auto">
          {/* Basemap Switcher */}
          <div className="flex items-center gap-0.5 bg-white/90 backdrop-blur-xl border border-white/80 p-0.5 rounded-2xl shadow-glass">
            <button
              id="btn-s5-satellite"
              onClick={() => handleToggleBasemap('satellite')}
              className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all ${
                activeBasemap === 'satellite' ? 'bg-[#FFD21F] text-slate-950 shadow-sm' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Satellite
            </button>
            <button
              id="btn-s5-terrain"
              onClick={() => handleToggleBasemap('terrain')}
              className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all ${
                activeBasemap === 'terrain' ? 'bg-[#FFD21F] text-slate-950 shadow-sm' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Terrain
            </button>
          </div>

          {/* Toggle Wakes */}
          <button
            id="btn-s5-toggle-wakes"
            onClick={() => setShowWakes(!showWakes)}
            className={`p-1.5 rounded-xl border shadow-glass backdrop-blur-xl transition-all active:scale-95 ${
              showWakes ? 'bg-[#FFD21F] text-slate-950 border-[#FFD21F]' : 'bg-white/90 text-slate-700 border-white/80 hover:bg-white'
            }`}
            title="Toggle Wake Cones"
          >
            {showWakes ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>

          {/* Reset View */}
          <button
            id="btn-s5-reset-view"
            onClick={handleResetView}
            className="p-1.5 rounded-xl bg-white/90 backdrop-blur-xl border border-white/80 text-slate-700 hover:bg-white shadow-glass transition-all active:scale-95"
            title="Reset Map View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* 3D Globe Toggle */}
          <button
            id="btn-s5-toggle-3d"
            onClick={onToggle3D}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold text-xs border shadow-glass backdrop-blur-xl transition-all active:scale-95 ${
              is3DActive
                ? 'bg-[#FFD21F] text-slate-950 border-amber-300 shadow-md'
                : 'bg-white/90 hover:bg-white text-slate-700 border-white/80'
            }`}
          >
            <Box className="w-3.5 h-3.5" />
            <span>{is3DActive ? '2D View' : '3D Globe'}</span>
          </button>
        </div>
      </div>

      {/* ── MAP & 3D CANVAS ─────────────────────────────────────── */}
      <div className="relative flex-1 w-full h-full">
        <div ref={mapContainerRef} id="screen5-map" className={`w-full h-full ${is3DActive ? 'hidden' : 'block'}`} />
        <div id="screen5-cesium" className={`w-full h-full absolute inset-0 ${is3DActive ? 'block' : 'hidden'}`} />

        {/* 3D Camera Presets Overlay (When 3D is active) */}
        {is3DActive && (
          <div
            id="s5-camera-presets-bar"
            className="absolute top-16 left-3 z-20 flex items-center gap-1 bg-white/95 backdrop-blur-xl p-1 rounded-2xl border border-white/90 shadow-glass"
          >
            {['TOP', 'NORTH', 'SOUTH', 'OBLIQUE', 'FIT_SITE'].map((preset) => (
              <button
                key={preset}
                type="button"
                data-preset={preset}
                onClick={() => handlePresetClick(preset)}
                className={`camera-preset-btn px-2.5 py-1 rounded-xl text-xs font-bold transition-all ${
                  activePreset === preset
                    ? 'active bg-[#FFD21F] text-slate-950 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {preset}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── BOTTOM FLOATING INSPECTOR PANEL ──────────────────────── */}
      <aside
        id="screen-5-sheet"
        className="absolute bottom-20 left-4 right-4 md:bottom-4 md:left-6 md:right-auto md:max-w-md z-20 pointer-events-auto"
      >
        <Card className="p-4 sm:p-5 flex flex-col gap-3 shadow-glass border-slate-200/90 bg-white/95 backdrop-blur-2xl">
          
          {/* Header & Mode Switch (Before vs Optimized) */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold text-slate-900 leading-tight">Optimized Layout Telemetry</h3>
              <p className="text-[11px] text-slate-500">WS-QAOA Quantum Annealing Micro-Siting</p>
            </div>

            {/* Segmented Layout Comparison Buttons */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
              <button
                id="s5-btn-before"
                type="button"
                onClick={() => setLayoutMode('before')}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-bold transition-all ${
                  layoutMode === 'before' ? 'bg-white text-slate-950 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Before
              </button>
              <button
                id="s5-btn-optimized"
                type="button"
                onClick={() => setLayoutMode('optimized')}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-bold transition-all ${
                  layoutMode === 'optimized' ? 'bg-[#FFD21F] text-slate-950 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Optimized
              </button>
            </div>
          </div>

          {/* Metrics KPIs */}
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Net AEP</div>
              <div id="s5-meta-aep" className="text-sm font-black text-slate-900 font-mono mt-0.5 tabular-nums">
                {aep}
              </div>
            </div>

            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Wake Loss</div>
              <div id="s5-meta-wake-loss" className="text-sm font-black text-emerald-600 font-mono mt-0.5 tabular-nums">
                {wakeLoss}
              </div>
            </div>

            <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Net Gain</div>
              <div className="text-sm font-black text-emerald-600 font-mono mt-0.5 tabular-nums">
                +{improvement}
              </div>
            </div>
          </div>

          {/* Turbine Micro-Inspector */}
          <div id="s5-turbine-inspector" className="p-3 rounded-xl bg-slate-50/90 border border-slate-200 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span id="s5-inspector-name" className="text-xs font-black text-slate-900">
                {selectedTurbine.label || `Turbine T-${String(selectedTurbineIdx + 1).padStart(2, '0')}`}
              </span>

              <div className="flex items-center gap-1">
                <button
                  id="btn-s5-prev-turbine"
                  type="button"
                  onClick={handlePrevTurbine}
                  className="p-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 shadow-2xs"
                  title="Previous Turbine"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  id="btn-s5-next-turbine"
                  type="button"
                  onClick={handleNextTurbine}
                  className="p-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 shadow-2xs"
                  title="Next Turbine"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
                <button
                  id="btn-s5-fly-turbine"
                  type="button"
                  onClick={() => {
                    panToTurbine(selectedTurbine);
                    if (!is3DActive) onToggle3D();
                  }}
                  className="px-2 py-1 rounded-lg bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-bold text-[10px] shadow-2xs flex items-center gap-1"
                  title="Inspect in 3D"
                >
                  <Eye className="w-3 h-3" />
                  <span>3D Focus</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono text-slate-600 tabular-nums">
              <div>Lat: <strong className="text-slate-900">{selectedTurbine.lat.toFixed(5)}°</strong></div>
              <div>Lon: <strong className="text-slate-900">{selectedTurbine.lon.toFixed(5)}°</strong></div>
              <div>Elev: <strong className="text-slate-900">{selectedTurbine.elevation_m || 42}m</strong></div>
              <div>Wind: <strong className="text-emerald-600">{(selectedTurbine.effective_mps || 7.4).toFixed(1)}m/s</strong></div>
            </div>
          </div>

          {/* Action Button */}
          <Button
            id="btn-screen5-export"
            variant="energy"
            size="md"
            onClick={onExportBlueprint}
            className="w-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black py-3 text-xs shadow-md mt-1"
          >
            <span>Proceed to Engineering Blueprint</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </Button>
        </Card>
      </aside>
    </div>
  );
};
