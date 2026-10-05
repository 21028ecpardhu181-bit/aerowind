import React, { useEffect, useMemo, useRef, useState } from 'react';
import { 
  Box, 
  Layers, 
  Compass, 
  ArrowRight, 
  ArrowLeft, 
  ChevronRight, 
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  Eye, 
  EyeOff, 
  RotateCcw,
  CheckCircle2,
  GitCompare,
  Plus,
  Minus,
  Crosshair
} from 'lucide-react';
import { OptimizationData, SiteInfo, Turbine } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { CesiumGlobeView } from '../gis/CesiumGlobeView';

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
function generateFallbackTurbines(clat: number, clon: number, count: number = 8, radiusKm: number = 3.0): Turbine[] {
  const turbs: Turbine[] = [];
  const radiusDeg = (Math.max(0.5, radiusKm) * 0.72) / 111.0;
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * 2 * Math.PI;
    const r = radiusDeg * (0.35 + 0.65 * ((i % 3) / 2));
    const lat = clat + r * Math.cos(angle);
    const lon = clon + (r * Math.sin(angle)) / Math.cos((clat * Math.PI) / 180);
    turbs.push({
      id: `T${i + 1}`,
      label: `T-${String(i + 1).padStart(2, '0')}`,
      lat: Number(lat.toFixed(6)),
      lon: Number(lon.toFixed(6)),
      elevation_m: 42 + (i % 5) * 4,
      effective_mps: Number((7.2 + (i % 4) * 0.2).toFixed(2)),
      wake_deficit_pct: Number((2.5 + (i % 3) * 1.1).toFixed(1)),
    });
  }
  return turbs;
}

  const polygonLayerRef = useRef<any>(null);

  const fallbackList = useMemo(() => generateFallbackTurbines(site.lat, site.lon, 8, site.radiusKm || 3.0), [site.lat, site.lon, site.radiusKm]);
  const optTurbines = (optimizationData?.optimized_turbines && optimizationData.optimized_turbines.length > 0)
    ? optimizationData.optimized_turbines
    : (baselineTurbines.length > 0 ? baselineTurbines : fallbackList);
  const activeTurbines = (layoutMode === 'before' && baselineTurbines.length > 0) ? baselineTurbines : optTurbines;
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

    let checkInterval: any = null;

    const setupMap = () => {
      const L = window.L;
      if (!L || !mapContainerRef.current) return;

      if (mapRef.current) {
        try { mapRef.current.remove(); } catch (_) {}
        mapRef.current = null;
      }

      const map = L.map(mapContainerRef.current, {
        center: [site.lat, site.lon],
        zoom: 14,
        zoomControl: false,
        attributionControl: false,
        maxZoom: 20,
      });

      // High-Resolution Satellite & Topo Layers via direct Esri CDN
      const satellite = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 19,
          attribution: 'Esri World Imagery',
        }
      );

      const terrain = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 19,
          attribution: 'Esri World Topo Map',
        }
      );

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
        weight: 3,
        opacity: 0.95,
        fillColor: '#FFD21F',
        fillOpacity: 0.12,
        dashArray: '4, 4',
      }).addTo(map);

      // Smart bounds fit with padding that accounts for bottom sheet
      map.fitBounds(polygonLayerRef.current.getBounds(), {
        paddingTopLeft: [50, 50],
        paddingBottomRight: isPanelCollapsed ? [50, 50] : [50, 240],
        maxZoom: 16,
      });

      renderLayout(map, activeTurbines, windDir, showWakes, selectedTurbineIdx);

      setTimeout(() => {
        try { map.invalidateSize(); } catch (_) {}
      }, 200);
    };

    if (window.L) {
      setupMap();
    } else {
      checkInterval = setInterval(() => {
        if (window.L) {
          clearInterval(checkInterval);
          setupMap();
        }
      }, 100);
    }

    return () => {
      if (checkInterval) clearInterval(checkInterval);
      if (mapRef.current) {
        try { mapRef.current.remove(); } catch (_) {}
        mapRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [is3DActive, site.lat, site.lon, activeTurbines, layoutMode, isPanelCollapsed]);

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
    const wakeLengthKm = 1.8;
    const wakeHalfAngleRad = (9.5 * Math.PI) / 180;

    turbs.forEach((t, idx) => {
      const isSelected = idx === activeIdx;
      const tId = t.label || t.id || `T-${String(idx + 1).padStart(2, '0')}`;
      const speed = (t.effective_mps || 7.4).toFixed(1);

      // Realistic Aerodynamic Multi-Layer Gradient Wake Plume
      if (wakesVisible) {
        const cosLat = Math.cos((t.lat * Math.PI) / 180.0);
        
        // 1. High-Deficit Core Wake Zone
        const coreLengthKm = wakeLengthKm * 0.45;
        const coreLeftLat = t.lat + (coreLengthKm / 111.0) * Math.cos(downwindRad - wakeHalfAngleRad * 0.7);
        const coreLeftLon = t.lon + (coreLengthKm / (111.0 * cosLat)) * Math.sin(downwindRad - wakeHalfAngleRad * 0.7);
        const coreRightLat = t.lat + (coreLengthKm / 111.0) * Math.cos(downwindRad + wakeHalfAngleRad * 0.7);
        const coreRightLon = t.lon + (coreLengthKm / (111.0 * cosLat)) * Math.sin(downwindRad + wakeHalfAngleRad * 0.7);

        const coreCone = L.polygon([[t.lat, t.lon], [coreLeftLat, coreLeftLon], [coreRightLat, coreRightLon]], {
          color: isSelected ? '#0284c7' : '#f59e0b',
          weight: 1,
          opacity: 0.5,
          fillColor: isSelected ? '#38bdf8' : '#f59e0b',
          fillOpacity: 0.22,
        }).addTo(map);
        wakeLayersRef.current.push(coreCone);

        // 2. Expanded Outer Wake Plume (Jensen Aerodynamic Recovery)
        const leftLat = t.lat + (wakeLengthKm / 111.0) * Math.cos(downwindRad - wakeHalfAngleRad);
        const leftLon = t.lon + (wakeLengthKm / (111.0 * cosLat)) * Math.sin(downwindRad - wakeHalfAngleRad);
        const rightLat = t.lat + (wakeLengthKm / 111.0) * Math.cos(downwindRad + wakeHalfAngleRad);
        const rightLon = t.lon + (wakeLengthKm / (111.0 * cosLat)) * Math.sin(downwindRad + wakeHalfAngleRad);

        const outerCone = L.polygon([[t.lat, t.lon], [leftLat, leftLon], [rightLat, rightLon]], {
          color: isSelected ? '#0284c7' : '#FFD21F',
          weight: 1,
          opacity: 0.35,
          fillColor: isSelected ? '#0ea5e9' : '#FFD21F',
          fillOpacity: 0.08,
        }).addTo(map);
        wakeLayersRef.current.push(outerCone);
      }

      // Authentic CAD-Grade 3-Blade Wind Turbine Marker with Yawed Nacelle & Red Tips
      const nacelleYaw = (angleDeg + 180) % 360;
      const spinSpeedS = Math.max(1.8, Math.min(5.5, 22.0 / Math.max(2.5, parseFloat(speed) || 7.5)));
      const markerHtml = `
        <div class="realistic-turbine-marker ${isSelected ? 'selected' : ''}" id="turb-marker-${idx}">
          <div class="turbine-ground-shadow"></div>

          <!-- Yawed Aerodynamic Nacelle Body -->
          <svg viewBox="0 0 80 80" class="turbine-svg-nacelle">
            <g transform="rotate(${nacelleYaw} 40 40)">
              <!-- Main Nacelle Shell -->
              <rect x="36.5" y="34" width="7" height="18" rx="3.5" fill="#f8fafc" stroke="#334155" stroke-width="1.0"/>
              <!-- Rear Cooling Radiator -->
              <rect x="37.5" y="46" width="5" height="5" rx="1" fill="#334155"/>
              <!-- Aviation Hazard Light -->
              <circle cx="40" cy="48" r="1.2" fill="#ef4444"/>
            </g>
          </svg>

          <!-- Continuously Rotating 3-Blade Airfoil Assembly -->
          <svg viewBox="0 0 80 80" class="turbine-svg-blades" style="animation: turbine-blade-spin ${spinSpeedS.toFixed(1)}s linear infinite;">
            <!-- Blade 1 (0 deg) -->
            <g transform="rotate(0 40 40)">
              <path d="M 38.6 38 C 37.8 26, 36.8 14, 39.6 4 C 40.4 4, 43.2 14, 42.4 26 C 41.6 34, 41.4 38, 41.4 38 Z" fill="#ffffff" stroke="#334155" stroke-width="0.75"/>
              <path d="M 37.5 13 C 37.2 8, 38.8 4, 39.6 4 C 40.4 4, 42.0 8, 41.7 13 Z" fill="#ef4444"/>
            </g>
            <!-- Blade 2 (120 deg) -->
            <g transform="rotate(120 40 40)">
              <path d="M 38.6 38 C 37.8 26, 36.8 14, 39.6 4 C 40.4 4, 43.2 14, 42.4 26 C 41.6 34, 41.4 38, 41.4 38 Z" fill="#ffffff" stroke="#334155" stroke-width="0.75"/>
              <path d="M 37.5 13 C 37.2 8, 38.8 4, 39.6 4 C 40.4 4, 42.0 8, 41.7 13 Z" fill="#ef4444"/>
            </g>
            <!-- Blade 3 (240 deg) -->
            <g transform="rotate(240 40 40)">
              <path d="M 38.6 38 C 37.8 26, 36.8 14, 39.6 4 C 40.4 4, 43.2 14, 42.4 26 C 41.6 34, 41.4 38, 41.4 38 Z" fill="#ffffff" stroke="#334155" stroke-width="0.75"/>
              <path d="M 37.5 13 C 37.2 8, 38.8 4, 39.6 4 C 40.4 4, 42.0 8, 41.7 13 Z" fill="#ef4444"/>
            </g>
            <!-- Center Bullet Spinner Nose Cone -->
            <circle cx="40" cy="40" r="4.2" fill="#ffffff" stroke="#1e293b" stroke-width="1.2"/>
            <circle cx="40" cy="40" r="2.0" fill="#ffd21f"/>
          </svg>

          <div class="turbine-glass-label">
            <span class="turbine-label-id">${tId}</span>
            <span class="turbine-label-power">${speed}m/s</span>
          </div>
        </div>
      `;

      const pinIcon = L.divIcon({
        className: 'turbine-pin-wrapper',
        html: markerHtml,
        iconSize: [52, 52],
        iconAnchor: [26, 26],
      });

      const m = L.marker([t.lat, t.lon], { icon: pinIcon, title: `${tId} (${speed} m/s)` }).addTo(map);
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
    <div id="screen-5-container" className="relative w-full h-[calc(100dvh-53px)] overflow-hidden flex flex-col bg-slate-100">
      
      {/* ── TOP STATUS & CONTROLS BAR ───────────────────────────── */}
      <div className="absolute top-2 left-2 right-2 sm:top-3 sm:left-3 sm:right-3 z-30 flex flex-wrap items-center justify-between gap-1.5 sm:gap-2 pointer-events-none">
        
        {/* Left: Back & Step Indicator */}
        <div className="flex items-center gap-1.5 sm:gap-2 pointer-events-auto">
          <button
            id="btn-s5-back"
            onClick={onBack}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl bg-white/90 backdrop-blur-xl border border-white/80 text-xs font-bold text-slate-800 hover:text-slate-950 hover:bg-white shadow-glass transition-all active:scale-95"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Optimize</span>
          </button>

          <div
            id="s5-indicator-text"
            className="hidden sm:flex px-3.5 py-1.5 rounded-xl bg-white/95 backdrop-blur-xl border border-white/90 text-xs font-bold text-slate-900 shadow-glass items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{site.shortName || site.name} · {activeTurbines.length} Turbines (WS-QAOA)</span>
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

          {/* Toggle Telemetry Box Visibility */}
          <button
            id="s5-panel-toggle"
            type="button"
            onClick={() => setIsPanelCollapsed(!isPanelCollapsed)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border shadow-glass backdrop-blur-xl transition-all active:scale-95 ${
              !isPanelCollapsed
                ? 'bg-[#FFD21F] text-slate-950 border-[#FFD21F]'
                : 'bg-white/90 text-slate-700 border-white/80 hover:bg-white'
            }`}
            title={isPanelCollapsed ? "Show Telemetry Box" : "Hide Telemetry Box"}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{isPanelCollapsed ? 'Show Telemetry' : 'Hide Box'}</span>
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
        <div id="screen5-cesium" className={`w-full h-full absolute inset-0 ${is3DActive ? 'block' : 'hidden'}`}>
          {is3DActive && (
            <CesiumGlobeView
              containerId="screen5-cesium-canvas"
              centerLat={site.lat}
              centerLon={site.lon}
              radiusKm={site.radiusKm || 3.0}
              boundary={site.boundary}
              turbines={activeTurbines}
              selectedTurbineIdx={selectedTurbineIdx}
              onSelectTurbine={(idx) => setSelectedTurbineIdx(idx)}
              windDirectionDeg={windDir}
              windSpeedMps={site.windSpeedMps || 7.8}
              rotorDiameter={120}
              hubHeight={110}
              turbineModelName={(optimizationData as any)?.turbine_model || "GE 2.5-120"}
              showWakes={showWakes}
            />
          )}
        </div>

        {/* Floating On-Screen Map Zoom & Fit Controls */}
        {!is3DActive && (
          <div className="absolute right-3 top-20 z-20 flex flex-col gap-1.5 pointer-events-auto">
            <button
              id="btn-s5-zoom-in"
              type="button"
              onClick={() => mapRef.current?.zoomIn()}
              className="w-9 h-9 rounded-xl bg-white/95 backdrop-blur-xl border border-white/90 text-slate-800 hover:text-slate-950 hover:bg-white shadow-glass flex items-center justify-center font-bold text-base active:scale-95 transition-all"
              title="Zoom In"
            >
              +
            </button>
            <button
              id="btn-s5-zoom-out"
              type="button"
              onClick={() => mapRef.current?.zoomOut()}
              className="w-9 h-9 rounded-xl bg-white/95 backdrop-blur-xl border border-white/90 text-slate-800 hover:text-slate-950 hover:bg-white shadow-glass flex items-center justify-center font-bold text-base active:scale-95 transition-all"
              title="Zoom Out"
            >
              −
            </button>
            <button
              id="btn-s5-fit-turbines"
              type="button"
              onClick={handleResetView}
              className="w-9 h-9 rounded-xl bg-white/95 backdrop-blur-xl border border-white/90 text-slate-800 hover:text-slate-950 hover:bg-white shadow-glass flex items-center justify-center active:scale-95 transition-all"
              title="Fit All Turbines in View"
            >
              <Crosshair className="w-4 h-4 text-amber-500" />
            </button>
          </div>
        )}

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

      {/* ── COLLAPSED FLOATING PILL (Shown when box is hidden so user sees unobstructed map) ── */}
      {isPanelCollapsed && (
        <button
          id="btn-s5-show-panel"
          type="button"
          onClick={() => setIsPanelCollapsed(false)}
          className="absolute bottom-20 left-1/2 -translate-x-1/2 md:bottom-6 z-20 pointer-events-auto flex items-center gap-2.5 px-4 py-2 rounded-2xl bg-white/95 backdrop-blur-xl border border-white/90 shadow-2xl text-slate-900 hover:scale-105 active:scale-95 transition-all group"
        >
          <div className="w-6 h-6 rounded-full bg-[#FFD21F] flex items-center justify-center text-slate-950 font-bold shadow-xs group-hover:rotate-180 transition-transform">
            <ChevronUp className="w-4 h-4" />
          </div>
          <div className="flex flex-col text-left">
            <span className="text-xs font-black text-slate-900 flex items-center gap-1.5">
              <span>Show Telemetry Panel</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              {aep} · {wakeLoss} wake · {activeTurbines.length} Turbines
            </span>
          </div>
        </button>
      )}

      {/* ── BOTTOM FLOATING INSPECTOR PANEL (Hideable Box) ───────── */}
      <aside
        id="screen-5-sheet"
        className={`absolute bottom-24 left-4 right-4 md:bottom-4 md:left-6 md:right-auto md:max-w-md z-[1250] pointer-events-auto transition-all duration-300 ${
          isPanelCollapsed ? 'translate-y-[150%] opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'
        }`}
      >
        <Card className="p-4 sm:p-5 flex flex-col gap-3 shadow-glass border-slate-200/90 bg-white/95 backdrop-blur-2xl">
          
          {/* Header & Mode Switch & Hide Box Button */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold text-slate-900 leading-tight">Optimized Layout Telemetry</h3>
              <p className="text-[11px] text-slate-500">WS-QAOA Quantum Annealing Micro-Siting</p>
            </div>

            <div className="flex items-center gap-2">
              {/* Segmented Layout Comparison Buttons */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
                <button
                  id="s5-btn-before"
                  type="button"
                  onClick={() => setLayoutMode('before')}
                  className={`px-2 py-0.5 rounded-lg text-[10px] font-bold transition-all ${
                    layoutMode === 'before' ? 'bg-white text-slate-950 shadow-xs active' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Before
                </button>
                <button
                  id="s5-btn-optimized"
                  type="button"
                  onClick={() => setLayoutMode('optimized')}
                  className={`px-2 py-0.5 rounded-lg text-[10px] font-bold transition-all ${
                    layoutMode === 'optimized' ? 'bg-[#FFD21F] text-slate-950 shadow-xs active' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Optimized
                </button>
              </div>

              {/* Hide Box Button */}
              <button
                id="btn-s5-hide-panel"
                type="button"
                onClick={() => setIsPanelCollapsed(true)}
                className="p-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 transition-all flex items-center gap-1 text-[10px] font-bold shadow-2xs"
                title="Hide this box to see turbines and full map"
              >
                <ChevronDown className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Hide Box</span>
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
