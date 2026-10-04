import React, { useState } from 'react';
import { Search, MapPin, Layers, Compass, Box, ArrowRight, Database, Edit3, CircleDot } from 'lucide-react';
import { SiteInfo } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen1SiteProps {
  site: SiteInfo;
  onConfirmSite: () => void;
  onOpenDataSources: () => void;
  onSearchLocation: (query: string) => void;
  onSelectRadius: (radiusKm: number) => void;
  onToggleDrawMode: (active: boolean) => void;
  onToggle3D: () => void;
  is3DActive: boolean;
}

export const Screen1Site: React.FC<Screen1SiteProps> = ({
  site,
  onConfirmSite,
  onOpenDataSources,
  onSearchLocation,
  onSelectRadius,
  onToggleDrawMode,
  onToggle3D,
  is3DActive,
}) => {
  const [mode, setMode] = useState<'search' | 'radius' | 'draw'>('search');
  const [searchVal, setSearchVal] = useState('');
  const [selectedRadius, setSelectedRadius] = useState<number>(10);

  const handleModeChange = (newMode: 'search' | 'radius' | 'draw') => {
    setMode(newMode);
    if (newMode === 'draw') {
      onToggleDrawMode(true);
    } else {
      onToggleDrawMode(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) {
      onSearchLocation(searchVal.trim());
    }
  };

  const handleRadiusClick = (r: number) => {
    setSelectedRadius(r);
    onSelectRadius(r);
  };

  return (
    <div id="screen-1-container" className="relative w-full h-[calc(100vh-53px)] overflow-hidden flex flex-col bg-slate-100">
      {/* 1. TOP FLOATING CONTROL BAR */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Left: Mode Selection Tabs & Search */}
        <div className="flex flex-wrap items-center gap-2 pointer-events-auto">
          {/* Mode Tabs */}
          <div className="flex items-center gap-1 bg-white/85 backdrop-blur-md p-1 rounded-2xl border border-slate-200/80 shadow-glass">
            <button
              id="tab-mode-search"
              onClick={() => handleModeChange('search')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                mode === 'search'
                  ? 'bg-amber-400 text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search Site</span>
            </button>

            <button
              id="tab-mode-radius"
              onClick={() => handleModeChange('radius')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                mode === 'radius'
                  ? 'bg-amber-400 text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <CircleDot className="w-3.5 h-3.5" />
              <span>Radius Concession</span>
            </button>

            <button
              id="tab-mode-draw"
              onClick={() => handleModeChange('draw')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                mode === 'draw'
                  ? 'bg-amber-400 text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Draw Area</span>
            </button>
          </div>

          {/* Search Box (When Search Mode is Active) */}
          {mode === 'search' && (
            <form onSubmit={handleSearchSubmit} className="flex items-center">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="map-search-input"
                  data-testid="search-input"
                  type="text"
                  placeholder="Enter location (e.g. Bommuru, Rajahmundry)..."
                  value={searchVal}
                  onChange={(e) => setSearchVal(e.target.value)}
                  className="pl-9 pr-3 py-2 text-xs rounded-2xl bg-white/90 backdrop-blur-md border border-slate-200/90 shadow-glass focus:outline-none focus:ring-2 focus:ring-amber-400 w-64 sm:w-80 text-slate-800 placeholder-slate-400 font-medium"
                />
                <input id="search-input" type="hidden" value={searchVal} readOnly />
              </div>
            </form>
          )}

          {/* Radius selector container */}
          <div
            id="radius-mode-container"
            className={`flex items-center gap-1.5 bg-white/85 backdrop-blur-md px-3 py-1.5 rounded-2xl border border-slate-200/80 shadow-glass ${
              mode === 'radius' ? 'flex' : 'hidden'
            }`}
          >
            <span className="text-xs font-semibold text-slate-500 mr-1">Radius:</span>
            {[1, 5, 10, 25, 50, 100].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => handleRadiusClick(r)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                  selectedRadius === r
                    ? 'bg-amber-400 text-slate-950 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {r}km
              </button>
            ))}
          </div>

          {/* Draw mode hint */}
          <div
            id="draw-mode-hint"
            className={`flex items-center gap-2 bg-amber-50/90 border border-amber-300 text-amber-900 px-3 py-1.5 rounded-2xl text-xs font-medium shadow-glass backdrop-blur-md ${
              mode === 'draw' ? 'flex' : 'hidden'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span id="draw-status-label">Click on the satellite map to place boundary vertices.</span>
          </div>
        </div>

        {/* Right: Map Presets & 3D Toggle */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            id="btn-ctx-data-sources"
            onClick={onOpenDataSources}
            className="flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-white/85 hover:bg-white text-slate-700 font-semibold text-xs border border-slate-200/80 shadow-glass backdrop-blur-md transition-all active:scale-95"
          >
            <Database className="w-3.5 h-3.5 text-amber-500" />
            <span>Data Sources</span>
          </button>

          <button
            id="btn-s1-toggle-3d"
            onClick={onToggle3D}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-2xl font-bold text-xs border shadow-glass backdrop-blur-md transition-all active:scale-95 ${
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

      {/* 2. MAP CANVAS / 3D CONTAINER */}
      <div className="relative flex-1 w-full h-full">
        {/* 2D Leaflet Container */}
        <div id="map" className={`w-full h-full ${is3DActive ? 'hidden' : 'block'}`} />

        {/* 3D Cesium Container */}
        <div
          id="screen1-cesium"
          className={`w-full h-full absolute inset-0 ${is3DActive ? 'block' : 'hidden'}`}
        />
      </div>

      {/* 3. BOTTOM FLOATING SITE INSPECTION SHEET */}
      <div className="absolute bottom-4 left-4 right-4 md:left-6 md:right-auto md:max-w-md z-20 pointer-events-auto">
        <Card className="p-4 sm:p-5 flex flex-col gap-3 shadow-glass border-slate-200/90">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-xl bg-amber-100 text-amber-700">
                <MapPin className="w-4 h-4" />
              </span>
              <div>
                <h3 id="meta-location-name" className="text-sm font-bold text-slate-900 leading-tight">
                  {site.name}
                </h3>
                <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5 font-mono">
                  <span>Lat: <strong id="meta-latitude" className="text-slate-800">{site.lat.toFixed(4)}</strong>°</span>
                  <span>Lon: <strong id="meta-longitude" className="text-slate-800">{site.lon.toFixed(4)}</strong>°</span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="text-[11px] text-slate-400 font-medium">Concession Area</div>
              <div id="meta-area" className="text-sm font-black text-slate-900 font-mono">
                {site.areaKm2 ? site.areaKm2.toFixed(1) : '24.8'} km²
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between text-slate-600">
              <span>Terrain:</span>
              <span className="font-semibold text-slate-800">{site.terrainType}</span>
            </div>
            <div className="flex items-center justify-between text-slate-600">
              <span>Wind Resource:</span>
              <span className="font-semibold text-emerald-600">{site.windSpeedMps} m/s</span>
            </div>
          </div>

          <Button
            id="btn-confirm-site"
            variant="energy"
            size="md"
            onClick={onConfirmSite}
            className="w-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black mt-1 shadow-md"
          >
            <span>Confirm Site Boundary</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </Button>
        </Card>
      </div>
    </div>
  );
};
