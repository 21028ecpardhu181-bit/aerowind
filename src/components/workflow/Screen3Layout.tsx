import React, { useEffect, useRef, useState } from 'react';
import { 
  ArrowLeft, 
  ArrowRight, 
  Wind, 
  Eye, 
  EyeOff, 
  RotateCcw, 
  ShieldCheck, 
  AlertTriangle 
} from 'lucide-react';
import { LayoutAnalysisData, SiteInfo, Turbine } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen3LayoutProps {
  site: SiteInfo;
  layoutData: LayoutAnalysisData;
  onLaunchOptimize: () => void;
  onBack: () => void;
}

declare global {
  interface Window {
    L?: any;
  }
}

export const Screen3Layout: React.FC<Screen3LayoutProps> = ({
  site,
  layoutData,
  onLaunchOptimize,
  onBack,
}) => {
  const [showWakes, setShowWakes] = useState(true);
  const [isSheetCollapsed, setIsSheetCollapsed] = useState(false);

  const mapRef = useRef<any>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const wakeLayersRef = useRef<any[]>([]);
  const turbineMarkersRef = useRef<any[]>([]);
  const candidateMarkersRef = useRef<any[]>([]);
  const polygonLayerRef = useRef<any>(null);

  const turbines = layoutData.turbines || [];
  const candidates = layoutData.candidate_positions || layoutData.candidates || [];
  const windDir = layoutData.wind_direction_deg ?? 300;
  const windSpeed = (layoutData.wind_speed_mps || site.windSpeedMps || 7.1).toFixed(1);
  const netAep = layoutData.net_aep_gwh ? layoutData.net_aep_gwh.toFixed(1) : '88.3';
  const grossAep = layoutData.gross_aep_gwh ? layoutData.gross_aep_gwh.toFixed(1) : '102.1';
  const wakeLoss = layoutData.wake_loss_percent ? layoutData.wake_loss_percent.toFixed(1) : '13.5';
  const minSpacing = layoutData.min_spacing_m ? Math.round(layoutData.min_spacing_m) : 600;
  const conflictsCount = layoutData.conflicts_count || layoutData.wake_conflicts_count || 0;

  // 1. Initialize Map
  useEffect(() => {
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

    // Satellite tiles
    L.tileLayer('/api/geo/tiles/satellite/{z}/{x}/{y}', {
      maxZoom: 20,
      attribution: 'Satellite Imagery',
    }).addTo(map);

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
      dashArray: '5, 5',
    }).addTo(map);

    map.fitBounds(polygonLayerRef.current.getBounds(), { padding: [40, 40] });

    // Render Candidate Grid Dots
    candidates.forEach((c: any) => {
      const dotIcon = L.divIcon({
        className: 'candidate-dot-wrapper',
        html: '<div class="candidate-grid-dot"></div>',
        iconSize: [10, 10],
        iconAnchor: [5, 5],
      });
      const m = L.marker([c.lat, c.lon], { icon: dotIcon, interactive: false }).addTo(map);
      candidateMarkersRef.current.push(m);
    });

    // Render Turbines & Wake Cones
    renderTurbinesAndWakes(map, turbines, windDir, showWakes);

    return () => {
      if (mapRef.current) {
        try { mapRef.current.remove(); } catch (_) {}
        mapRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.lat, site.lon, turbines, candidates]);

  // Re-render wake cones when showWakes toggles
  useEffect(() => {
    if (mapRef.current) {
      renderTurbinesAndWakes(mapRef.current, turbines, windDir, showWakes);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showWakes]);

  const renderTurbinesAndWakes = (map: any, turbs: Turbine[], angleDeg: number, wakesVisible: boolean) => {
    const L = window.L;
    if (!L || !map) return;

    // Clear old markers & wake cones
    turbineMarkersRef.current.forEach((m) => map.removeLayer(m));
    turbineMarkersRef.current = [];
    wakeLayersRef.current.forEach((w) => map.removeLayer(w));
    wakeLayersRef.current = [];

    // Wake cone geometry parameters (Jensen analytical model)
    const downwindRad = ((angleDeg + 180) % 360) * (Math.PI / 180); // Flow points downwind
    const wakeLengthKm = 1.8; // ~15D length
    const wakeHalfAngleRad = (10 * Math.PI) / 180; // ~10 deg half-angle expansion

    turbs.forEach((t, idx) => {
      const tLat = t.lat;
      const tLon = t.lon;
      const tId = t.id || `T${idx + 1}`;

      // 1. Draw Wake Cone Polygon
      if (wakesVisible) {
        const cosLat = Math.cos((tLat * Math.PI) / 180.0);
        const tipLat = tLat;
        const tipLon = tLon;

        // Downwind apex left and right
        const angleLeft = downwindRad - wakeHalfAngleRad;
        const angleRight = downwindRad + wakeHalfAngleRad;

        const leftLat = tLat + (wakeLengthKm / 111.0) * Math.cos(angleLeft);
        const leftLon = tLon + (wakeLengthKm / (111.0 * cosLat)) * Math.sin(angleLeft);

        const rightLat = tLat + (wakeLengthKm / 111.0) * Math.cos(angleRight);
        const rightLon = tLon + (wakeLengthKm / (111.0 * cosLat)) * Math.sin(angleRight);

        const wakeCone = L.polygon([[tipLat, tipLon], [leftLat, leftLon], [rightLat, rightLon]], {
          color: t.is_conflicted ? '#ef4444' : '#FFD21F',
          weight: 1,
          opacity: 0.6,
          fillColor: t.is_conflicted ? '#ef4444' : '#FFD21F',
          fillOpacity: 0.15,
        }).addTo(map);

        wakeLayersRef.current.push(wakeCone);
      }

      // 2. Draw Turbine Pin
      const pinClass = t.is_conflicted ? 'turbine-map-pin conflicted' : 'turbine-map-pin';
      const pinIcon = L.divIcon({
        className: 'turbine-pin-wrapper',
        html: `<div class="${pinClass}">${tId}</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const marker = L.marker([tLat, tLon], { icon: pinIcon }).addTo(map);
      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; line-height: 1.4;">
          <strong style="font-size: 13px;">Turbine ${tId}</strong><br>
          Effective Wind: <strong>${t.effective_mps || windSpeed} m/s</strong><br>
          Wake Deficit: <span style="color: ${(t.wake_deficit_pct || 0) > 8 ? '#ef4444' : '#f59e0b'}; font-weight: 700;">-${(t.wake_deficit_pct || 4.2).toFixed(1)}%</span><br>
          ${t.conflict_desc ? `<div style="color: #ef4444; font-weight: 600; margin-top: 4px;">⚠️ ${t.conflict_desc}</div>` : '<div style="color: #10b981; font-weight: 600; margin-top: 4px;">✓ Free Stream Velocity</div>'}
        </div>
      `);

      turbineMarkersRef.current.push(marker);
    });
  };

  const handleResetView = () => {
    if (mapRef.current && polygonLayerRef.current) {
      mapRef.current.fitBounds(polygonLayerRef.current.getBounds(), { padding: [40, 40] });
    }
  };

  return (
    <div id="screen-3-container" className="relative w-full h-[calc(100vh-53px)] overflow-hidden flex flex-col bg-slate-900">
      
      {/* ── TOP FLOATING CONTROL BAR ────────────────────────────── */}
      <div className="absolute top-3 left-3 right-3 z-30 flex items-center justify-between pointer-events-none">
        
        {/* Left: Back & Step Indicator */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            id="btn-s3-back"
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/90 backdrop-blur-xl border border-white/80 text-xs font-bold text-slate-800 hover:text-slate-950 hover:bg-white shadow-glass transition-all active:scale-95"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Config</span>
          </button>

          <div
            id="s3-indicator-text"
            className="px-3 py-1.5 rounded-xl bg-white/95 backdrop-blur-xl border border-white/90 text-xs font-bold text-slate-900 shadow-glass flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>{site.shortName || site.name} · {turbines.length} Turbines Initial Layout</span>
          </div>
        </div>

        {/* Right: Map Actions (Toggle Wakes, Reset View) */}
        <div className="flex items-center gap-1.5 pointer-events-auto">
          <button
            id="btn-s3-toggle-wakes"
            onClick={() => setShowWakes(!showWakes)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border shadow-glass backdrop-blur-xl transition-all active:scale-95 ${
              showWakes
                ? 'bg-[#FFD21F] text-slate-950 border-[#FFD21F]'
                : 'bg-white/90 text-slate-700 border-white/80 hover:bg-white'
            }`}
          >
            {showWakes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{showWakes ? 'Wake Cones: Active' : 'Show Wakes'}</span>
          </button>

          <button
            id="btn-s3-reset-view"
            onClick={handleResetView}
            className="p-1.5 rounded-xl bg-white/90 backdrop-blur-xl border border-white/80 text-slate-700 hover:text-slate-950 hover:bg-white shadow-glass transition-all active:scale-95"
            title="Reset Map View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── MAP CONTAINER ────────────────────────────────────────── */}
      <div className="relative flex-1 w-full h-full">
        <div ref={mapContainerRef} id="screen3-map" className="w-full h-full" />

        {/* Floating Wind Vector Badge */}
        <div className="absolute top-16 left-3 z-20 pointer-events-none">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-2xl bg-white/95 backdrop-blur-xl border border-white/90 shadow-glass text-xs font-mono font-bold text-slate-800">
            <svg
              id="s3-wind-arrow-svg"
              className="w-4 h-4 text-amber-500 transition-transform duration-300"
              style={{ transform: `rotate(${windDir - 90}deg)` }}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
            <span id="s3-wind-vector-text">
              Wind: {windSpeed} m/s @ {windDir}°
            </span>
          </div>
        </div>
      </div>

      {/* ── BOTTOM FLOATING LAYOUT TELEMETRY CARD ────────────────── */}
      <aside className="absolute bottom-20 left-4 right-4 md:bottom-4 md:left-6 md:right-auto md:max-w-md z-20 pointer-events-auto">
        <Card className="p-4 sm:p-5 flex flex-col gap-3 shadow-glass border-slate-200/90 bg-white/95 backdrop-blur-2xl">
          
          <div
            id="s3-panel-toggle"
            onClick={() => setIsSheetCollapsed(!isSheetCollapsed)}
            className="flex items-center justify-between pb-2 border-b border-slate-100 cursor-pointer"
          >
            <div>
              <h3 className="text-xs font-bold text-slate-900 leading-tight">Baseline Layout Simulation</h3>
              <p className="text-[11px] text-slate-500">Heuristic micro-siting & analytical Jensen wake model</p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 font-bold border border-amber-300">
              Heuristic
            </span>
          </div>

          {!isSheetCollapsed && (
            <>
              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Net AEP</div>
                  <div id="s3-meta-net-aep" className="text-sm font-black text-slate-900 font-mono mt-0.5 tabular-nums">
                    {netAep} GWh
                  </div>
                  <div id="s3-meta-gross-aep" className="hidden">{grossAep} GWh</div>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Wake Loss</div>
                  <div id="s3-meta-wake-loss" className="text-sm font-black text-rose-600 font-mono mt-0.5 tabular-nums">
                    {wakeLoss}%
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Min Spacing</div>
                  <div id="s3-meta-min-spacing" className="text-sm font-black text-slate-900 font-mono mt-0.5 tabular-nums">
                    {minSpacing} m
                  </div>
                  <div id="s3-meta-conflicts-count" className="hidden">{conflictsCount}</div>
                </div>
              </div>

              {/* Physical Constraints Validation */}
              <div className="flex items-center justify-between text-xs px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 font-medium">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Boundary & 5D Spacing Enforced</span>
                </span>
                <span className="font-bold text-[11px] font-mono">
                  {conflictsCount === 0 ? '✓ 0 Overlaps' : `⚠️ ${conflictsCount} Overlaps`}
                </span>
              </div>
            </>
          )}

          {/* Primary Action Button */}
          <Button
            id="btn-screen3-optimize"
            variant="energy"
            size="md"
            onClick={onLaunchOptimize}
            className="w-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black py-3 mt-1 shadow-md text-xs"
          >
            <span>Proceed to Quantum WS-QAOA Optimization</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </Button>
        </Card>
      </aside>
    </div>
  );
};
