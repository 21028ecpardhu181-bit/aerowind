import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  MapPin, 
  ArrowRight, 
  Database, 
  Box, 
  Edit3, 
  CircleDot, 
  Crosshair, 
  Layers, 
  Compass, 
  RotateCcw, 
  CheckCircle2, 
  AlertTriangle,
  X,
  Plus,
  Minus
} from 'lucide-react';
import { SiteInfo, TelemetryData } from '../../types';
import { Button } from '../ui/Button';

interface Screen1SiteProps {
  site: SiteInfo;
  telemetry: TelemetryData | null;
  onConfirmSite: () => void;
  onOpenDataSources: () => void;
  onSearchLocation: (query: string) => Promise<void> | void;
  onSelectRadius: (radiusKm: number) => void;
  onToggleDrawMode: (active: boolean) => void;
  onToggle3D: () => void;
  is3DActive: boolean;
  onSiteChange: (newSite: Partial<SiteInfo>) => void;
}

declare global {
  interface Window {
    L?: any;
    CESIUM_BASE_URL?: string;
  }
}

const PRESET_LOCATIONS = [
  { name: 'Kanyakumari, Tamil Nadu', lat: 8.0883, lon: 77.5385, areaKm2: 24.8, terrain: 'Coastal / Mild Slope' },
  { name: 'Jaisalmer, Rajasthan', lat: 26.9157, lon: 70.9083, areaKm2: 32.4, terrain: 'Desert Plain' },
  { name: 'Kutch, Gujarat', lat: 23.7337, lon: 69.8597, areaKm2: 28.0, terrain: 'Coastal Salt Flat' },
  { name: 'Tuticorin, Tamil Nadu', lat: 8.7642, lon: 78.1348, areaKm2: 22.5, terrain: 'Coastal Plain' },
  { name: 'Anantapur, Andhra Pradesh', lat: 14.6819, lon: 77.6006, areaKm2: 30.2, terrain: 'High Plateau' },
];

export const Screen1Site: React.FC<Screen1SiteProps> = ({
  site,
  telemetry,
  onConfirmSite,
  onOpenDataSources,
  onSearchLocation,
  onSelectRadius,
  onToggleDrawMode,
  onToggle3D,
  is3DActive,
  onSiteChange,
}) => {
  const [mode, setMode] = useState<'search' | 'radius' | 'draw' | 'coords'>('search');
  const [searchVal, setSearchVal] = useState(site.name);
  const [selectedRadius, setSelectedRadius] = useState<number>(site.radiusKm || 5);
  const [customRadius, setCustomRadius] = useState<string>('5');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [isGpsLocating, setIsGpsLocating] = useState(false);
  const [showCoordsPopup, setShowCoordsPopup] = useState(false);
  const [manualLat, setManualLat] = useState(site.lat.toString());
  const [manualLon, setManualLon] = useState(site.lon.toString());
  const [activeBaseLayer, setActiveBaseLayer] = useState<'satellite' | 'street' | 'terrain'>('satellite');
  const [isSheetCollapsed, setIsSheetCollapsed] = useState(false);

  // Drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
  const [drawStats, setDrawStats] = useState<{ areaKm2: number; perimKm: number } | null>(null);

  const mapRef = useRef<any>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const baseLayersRef = useRef<{ satellite?: any; street?: any; terrain?: any }>({});
  const polygonLayerRef = useRef<any>(null);
  const areaBadgeRef = useRef<any>(null);
  const locationLabelRef = useRef<any>(null);
  const drawnMarkersRef = useRef<any[]>([]);
  const drawnPolylineRef = useRef<any>(null);

  // Synchronize manual coordinate inputs when site updates
  useEffect(() => {
    setManualLat(site.lat.toFixed(4));
    setManualLon(site.lon.toFixed(4));
    setSearchVal(site.name);
  }, [site.lat, site.lon, site.name]);

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (is3DActive) return;

    let checkInterval: any = null;

    const setupMap = () => {
      const L = window.L;
      if (!L || !mapContainerRef.current) return;

      // Clean up previous instance
      if (mapRef.current) {
        try { mapRef.current.remove(); } catch (_) {}
        mapRef.current = null;
      }

      const map = L.map(mapContainerRef.current, {
        center: [site.lat, site.lon],
        zoom: 12,
        zoomControl: false,
        attributionControl: false,
      });

      // Define Layers
      const satellite = L.tileLayer('/api/geo/tiles/satellite/{z}/{x}/{y}', {
        maxZoom: 20,
        attribution: 'Satellite Imagery',
      });

      const street = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: 'OpenStreetMap',
      });

      const terrain = L.tileLayer('/api/geo/tiles/terrain/{z}/{x}/{y}', {
        maxZoom: 20,
        attribution: 'Terrain Imagery',
      });

      baseLayersRef.current = { satellite, street, terrain };

      // Set initial base layer
      if (activeBaseLayer === 'street') {
        street.addTo(map);
      } else if (activeBaseLayer === 'terrain') {
        terrain.addTo(map);
      } else {
        satellite.addTo(map);
      }

      // Add Scale Bar
      L.control.scale({
        position: 'bottomleft',
        metric: true,
        imperial: false,
        maxWidth: 140,
      }).addTo(map);

      mapRef.current = map;

      // Map Click Handler
      map.on('click', (e: any) => {
        const lat = parseFloat(e.latlng.lat.toFixed(6));
        const lng = parseFloat(e.latlng.lng.toFixed(6));

        if (mode === 'draw') {
          setDrawnPoints((prev) => [...prev, [lat, lng]]);
        } else {
          handleDirectMapSelection(lat, lng);
        }
      });

      // Render initial boundary
      renderBoundary(site.lat, site.lon, site.areaKm2, site.boundary as [number, number][]);
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
  }, [is3DActive]);

  // Handle Base Layer Switch
  const switchBaseLayer = (layerKey: 'satellite' | 'street' | 'terrain') => {
    setActiveBaseLayer(layerKey);
    const map = mapRef.current;
    if (!map) return;

    Object.values(baseLayersRef.current).forEach((l) => {
      if (l && map.hasLayer(l)) map.removeLayer(l);
    });

    const target = baseLayersRef.current[layerKey];
    if (target) target.addTo(map);
  };

  // 2. Geodesic & Area Calculation Utilities
  const calculatePolygonAreaKm2 = (vertices: [number, number][]): number => {
    if (!vertices || vertices.length < 3) return 0;
    const R = 6371.0;
    const refLat = vertices[0][0];
    const cosLat = Math.cos((refLat * Math.PI) / 180.0);
    let area = 0.0;
    const n = vertices.length;
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      const xi = ((vertices[i][1] * Math.PI) / 180.0) * R * cosLat;
      const yi = ((vertices[i][0] * Math.PI) / 180.0) * R;
      const xj = ((vertices[j][1] * Math.PI) / 180.0) * R * cosLat;
      const yj = ((vertices[j][0] * Math.PI) / 180.0) * R;
      area += xi * yj - xj * yi;
    }
    return Math.abs(area) / 2.0;
  };

  const calculatePolygonPerimeterKm = (vertices: [number, number][]): number => {
    if (!vertices || vertices.length < 2) return 0;
    const R = 6371.0;
    const toRad = Math.PI / 180.0;
    let perim = 0.0;
    const n = vertices.length;
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      const lat1 = vertices[i][0] * toRad;
      const lon1 = vertices[i][1] * toRad;
      const lat2 = vertices[j][0] * toRad;
      const lon2 = vertices[j][1] * toRad;
      const dLat = lat2 - lat1;
      const dLon = lon2 - lon1;
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      perim += R * c;
    }
    return perim;
  };

  const generateDefaultVertices = (lat: number, lon: number, areaKm2: number): [number, number][] => {
    const radiusKm = Math.sqrt(areaKm2) / 2.0;
    const latDelta = radiusKm / 111.0;
    const lonDelta = radiusKm / (111.0 * Math.cos((lat * Math.PI) / 180.0));
    return [
      [lat + latDelta * 1.1, lon - lonDelta * 0.1],
      [lat + latDelta * 0.7, lon + lonDelta * 0.1],
      [lat + latDelta * 0.2, lon + lonDelta * 0.45],
      [lat - latDelta * 0.4, lon + lonDelta * 0.85],
      [lat - latDelta * 0.9, lon + lonDelta * 0.95],
      [lat - latDelta * 1.2, lon - lonDelta * 0.45],
      [lat - latDelta * 0.6, lon - lonDelta * 1.1],
      [lat - latDelta * 0.1, lon - lonDelta * 0.85],
      [lat + latDelta * 0.25, lon - lonDelta * 0.65],
      [lat + latDelta * 0.65, lon - lonDelta * 0.55],
    ];
  };

  // 3. Render Boundary Polygon & Badges on Map
  const renderBoundary = (lat: number, lon: number, areaKm2: number, customBoundary?: [number, number][]) => {
    const map = mapRef.current;
    const L = window.L;
    if (!map || !L) return;

    if (polygonLayerRef.current) map.removeLayer(polygonLayerRef.current);
    if (areaBadgeRef.current) map.removeLayer(areaBadgeRef.current);
    if (locationLabelRef.current) map.removeLayer(locationLabelRef.current);

    const vertices: [number, number][] =
      customBoundary && customBoundary.length >= 3
        ? customBoundary
        : generateDefaultVertices(lat, lon, areaKm2);

    const calcArea = calculatePolygonAreaKm2(vertices);

    // Blue/cyan geodesic boundary polygon
    polygonLayerRef.current = L.polygon(vertices, {
      color: '#FFD21F',
      weight: 2.5,
      opacity: 0.95,
      fillColor: '#FFD21F',
      fillOpacity: 0.15,
      smoothFactor: 1,
    }).addTo(map);

    map.fitBounds(polygonLayerRef.current.getBounds(), {
      padding: [40, 40],
      maxZoom: 15,
    });

    // Concession Area Badge
    const badgeIcon = L.divIcon({
      className: 'badge-div-wrapper',
      html: `<div class="selected-area-badge">Concession Area<br><strong>${calcArea.toFixed(1)} km²</strong></div>`,
      iconSize: [120, 40],
      iconAnchor: [60, 20],
    });
    areaBadgeRef.current = L.marker([lat, lon], { icon: badgeIcon }).addTo(map);

    // Location Label Tag
    const nameIcon = L.divIcon({
      className: 'label-div-wrapper',
      html: `<div class="location-anchor-tag">${site.shortName || 'Selected Site'}</div>`,
      iconSize: [140, 24],
      iconAnchor: [70, -25],
    });
    locationLabelRef.current = L.marker([lat, lon], { icon: nameIcon }).addTo(map);
  };

  // 4. Drawing Mode Sync
  useEffect(() => {
    const map = mapRef.current;
    const L = window.L;
    if (!map || !L || mode !== 'draw') return;

    // Clear old drawn layers
    drawnMarkersRef.current.forEach((m) => map.removeLayer(m));
    drawnMarkersRef.current = [];
    if (drawnPolylineRef.current) {
      map.removeLayer(drawnPolylineRef.current);
      drawnPolylineRef.current = null;
    }

    if (drawnPoints.length === 0) {
      setDrawStats(null);
      return;
    }

    // Draw line/polygon
    if (drawnPoints.length >= 3) {
      drawnPolylineRef.current = L.polygon(drawnPoints, {
        color: '#FFD21F',
        weight: 2.5,
        dashArray: '5, 5',
        fillColor: '#FFD21F',
        fillOpacity: 0.2,
      }).addTo(map);

      const area = calculatePolygonAreaKm2(drawnPoints);
      const perim = calculatePolygonPerimeterKm(drawnPoints);
      setDrawStats({ areaKm2: area, perimKm: perim });
    } else if (drawnPoints.length >= 2) {
      drawnPolylineRef.current = L.polyline(drawnPoints, {
        color: '#FFD21F',
        weight: 2,
        dashArray: '5, 5',
      }).addTo(map);
    }

    // Numbered draggable markers
    drawnPoints.forEach((pt, idx) => {
      const markerIcon = L.divIcon({
        className: 'gis-vertex-marker-wrapper',
        html: `<div class="gis-vertex-marker" title="Drag to adjust">${idx + 1}</div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const m = L.marker(pt, { icon: markerIcon, draggable: true }).addTo(map);

      m.on('drag', (e: any) => {
        const newPos = e.target.getLatLng();
        setDrawnPoints((pts) => {
          const updated = [...pts];
          updated[idx] = [parseFloat(newPos.lat.toFixed(6)), parseFloat(newPos.lng.toFixed(6))];
          return updated;
        });
      });

      m.on('contextmenu', (e: any) => {
        e.originalEvent?.preventDefault();
        setDrawnPoints((pts) => pts.filter((_, i) => i !== idx));
      });

      drawnMarkersRef.current.push(m);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drawnPoints, mode]);

  // Direct Map Click
  const handleDirectMapSelection = (lat: number, lon: number) => {
    const shortName = `${lat.toFixed(3)}°N, ${lon.toFixed(3)}°E`;
    const newSite = {
      ...site,
      lat,
      lon,
      shortName,
      name: `${shortName}, Engineering Site`,
      boundary: generateDefaultVertices(lat, lon, site.areaKm2),
    };
    onSiteChange(newSite);
    renderBoundary(lat, lon, site.areaKm2, newSite.boundary);

    // Reverse geocode quietly
    fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`)
      .then((r) => r.json())
      .then((data) => {
        if (data && data.display_name) {
          onSiteChange({ name: data.display_name, shortName: data.display_name.split(',')[0] });
        }
      })
      .catch(() => {});
  };

  // Search submission
  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchVal.trim();
    if (!query) return;

    setIsSearching(true);
    setSearchError('');
    try {
      await onSearchLocation(query);
    } catch (_) {
      setSearchError('Location not found. Try entering coordinates or clicking the map.');
    } finally {
      setIsSearching(false);
    }
  };

  // GPS Current Location
  const handleUseGps = () => {
    if (!navigator.geolocation) {
      setSearchError('Geolocation is not supported by your browser.');
      return;
    }
    setIsGpsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsGpsLocating(false);
        const lat = parseFloat(pos.coords.latitude.toFixed(6));
        const lon = parseFloat(pos.coords.longitude.toFixed(6));
        handleDirectMapSelection(lat, lon);
      },
      (err) => {
        setIsGpsLocating(false);
        setSearchError(`GPS access error: ${err.message}`);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Apply Radius Concession
  const handleApplyRadius = (radiusKm: number) => {
    setSelectedRadius(radiusKm);
    onSelectRadius(radiusKm);

    const steps = 64;
    const vertices: [number, number][] = [];
    const centerLat = site.lat;
    const centerLon = site.lon;
    const cosLat = Math.cos((centerLat * Math.PI) / 180.0) || 1e-6;

    for (let i = 0; i < steps; i++) {
      const angle = (i / steps) * 2 * Math.PI;
      const dLat = (radiusKm / 111.0) * Math.cos(angle);
      const dLon = (radiusKm / (111.0 * cosLat)) * Math.sin(angle);
      vertices.push([
        parseFloat((centerLat + dLat).toFixed(6)),
        parseFloat((centerLon + dLon).toFixed(6)),
      ]);
    }

    const areaKm2 = Math.PI * radiusKm * radiusKm;
    onSiteChange({
      radiusKm,
      areaKm2,
      boundary: vertices,
    });

    renderBoundary(centerLat, centerLon, areaKm2, vertices);
  };

  // Close Custom Drawn Polygon
  const handleClosePolygon = () => {
    if (drawnPoints.length < 3) return;
    const areaKm2 = calculatePolygonAreaKm2(drawnPoints);
    const perimKm = calculatePolygonPerimeterKm(drawnPoints);
    const centerLat = drawnPoints.reduce((sum, v) => sum + v[0], 0) / drawnPoints.length;
    const centerLon = drawnPoints.reduce((sum, v) => sum + v[1], 0) / drawnPoints.length;

    onSiteChange({
      lat: centerLat,
      lon: centerLon,
      areaKm2,
      perimeterKm: perimKm,
      boundary: drawnPoints,
    });

    renderBoundary(centerLat, centerLon, areaKm2, drawnPoints);
    setDrawnPoints([]);
    setMode('search');
    onToggleDrawMode(false);
  };

  // Manual Coordinates Submit
  const handleApplyCoordinates = () => {
    const lat = parseFloat(manualLat);
    const lon = parseFloat(manualLon);
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setSearchError('Invalid latitude/longitude coordinates.');
      return;
    }
    setShowCoordsPopup(false);
    handleDirectMapSelection(lat, lon);
  };

  // Reset to default boundary
  const handleResetBoundary = () => {
    const defaultBoundary = generateDefaultVertices(site.lat, site.lon, 24.8);
    onSiteChange({ areaKm2: 24.8, boundary: defaultBoundary });
    renderBoundary(site.lat, site.lon, 24.8, defaultBoundary);
  };

  // Fit camera to boundary
  const handleFitSite = () => {
    if (mapRef.current && polygonLayerRef.current) {
      mapRef.current.fitBounds(polygonLayerRef.current.getBounds(), { padding: [40, 40] });
    }
  };

  // 9-point Geotechnical Site Intelligence Checklist Items
  const intelItems = [
    { label: 'Checking terrain', source: `Verified (SRTM DEM, ${site.elevationM || 42}m avg)`, status: 'verified' },
    { label: 'Checking available land', source: `Verified (${(site.areaKm2 || 24.8).toFixed(1)} km² GIS boundary)`, status: 'verified' },
    { label: 'Checking buildings', source: 'Verified (500m setback clear)', status: 'verified' },
    { label: 'Checking roads', source: 'Verified (Corridor access)', status: 'verified' },
    { label: 'Checking access', source: 'Verified (Heavy haulage road)', status: 'verified' },
    { label: 'Checking wind resource', source: `Verified (ECMWF ${(site.windSpeedMps || 7.1).toFixed(1)} m/s)`, status: 'verified' },
    { label: 'Checking construction suitability', source: 'Requires verification (soil test)', status: 'warning' },
    { label: 'Checking environmental constraints', source: 'Verified (No wildlife sanctuaries)', status: 'verified' },
    { label: 'Checking turbine spacing', source: 'Verified (5D compliant)', status: 'verified' },
  ];

  return (
    <div id="screen-1-container" className="relative w-full h-[calc(100vh-53px)] overflow-hidden flex flex-col bg-slate-100">
      
      {/* ── TOP CONTROL HUD (Liquid Glass Floating Panel) ─────────── */}
      <div className="absolute top-3 left-3 right-3 md:right-[404px] z-30 flex flex-col gap-2 pointer-events-none">
        
        {/* ROW 1: Mode Tabs + Map Layer Switches */}
        <div className="flex flex-wrap items-center justify-between gap-2 pointer-events-auto">
          {/* Boundary Selection Mode Tabs */}
          <div className="flex items-center gap-1 bg-white/95 backdrop-blur-2xl border border-slate-200/90 p-1 rounded-2xl shadow-glass">
            <button
              id="tab-mode-search"
              onClick={() => { setMode('search'); onToggleDrawMode(false); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'search' ? 'bg-[#FFD21F] text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search</span>
            </button>

            <button
              id="tab-mode-radius"
              onClick={() => { setMode('radius'); onToggleDrawMode(false); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'radius' ? 'bg-[#FFD21F] text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <CircleDot className="w-3.5 h-3.5" />
              <span>Radius</span>
            </button>

            <button
              id="tab-mode-draw"
              onClick={() => { setMode('draw'); onToggleDrawMode(true); setIsDrawing(true); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'draw' ? 'bg-[#FFD21F] text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Freeform Polygon</span>
            </button>
          </div>

          {/* Map Layer Switcher & 3D Globe */}
          <div className="flex items-center gap-1.5 bg-white/95 backdrop-blur-2xl border border-slate-200/90 p-1 rounded-2xl shadow-glass">
            <button
              onClick={() => switchBaseLayer('street')}
              className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeBaseLayer === 'street' && !is3DActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Map
            </button>
            <button
              onClick={() => switchBaseLayer('satellite')}
              className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeBaseLayer === 'satellite' && !is3DActive ? 'bg-[#FFD21F] text-slate-950 font-bold' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Satellite
            </button>
            <button
              onClick={() => switchBaseLayer('terrain')}
              className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeBaseLayer === 'terrain' && !is3DActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Terrain
            </button>
            <button
              id="btn-s1-toggle-3d"
              onClick={onToggle3D}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                is3DActive ? 'bg-[#FFD21F] text-slate-950 shadow-sm' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span>3D Globe</span>
            </button>
          </div>
        </div>

        {/* ROW 2: Contextual Toolbar Based on Mode */}
        {mode === 'search' && (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pointer-events-auto">
            <form onSubmit={handleSearchSubmit} className="relative flex-1 flex items-center">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
              <input
                id="map-search-input"
                type="text"
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                placeholder="Where do you want to build? Search location..."
                className="w-full pl-9 pr-12 py-2.5 rounded-2xl bg-white/98 backdrop-blur-2xl border border-slate-200/90 shadow-glass text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#FFD21F]"
              />
              <button
                type="submit"
                disabled={isSearching}
                className="absolute right-1.5 p-2 rounded-xl bg-[#FFD21F] text-slate-950 font-bold hover:bg-[#F2C50F] transition-all disabled:opacity-50"
                title="Search Location"
              >
                {isSearching ? (
                  <span className="w-3.5 h-3.5 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin block" />
                ) : (
                  <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
                )}
              </button>
            </form>

            {/* GPS Button */}
            <button
              type="button"
              id="btn-map-gps"
              onClick={handleUseGps}
              disabled={isGpsLocating}
              className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-2xl bg-white/95 backdrop-blur-xl border border-white/90 shadow-glass text-xs font-bold text-slate-700 hover:text-slate-950 hover:bg-white active:scale-95 transition-all"
            >
              <Crosshair className={`w-3.5 h-3.5 text-amber-500 ${isGpsLocating ? 'animate-spin' : ''}`} />
              <span className="whitespace-nowrap">GPS Location</span>
            </button>
          </div>
        )}

        {/* Preset Location Chips */}
        {mode === 'search' && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pointer-events-auto no-scrollbar">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider pl-1">Presets:</span>
            {PRESET_LOCATIONS.map((loc) => (
              <button
                key={loc.name}
                type="button"
                onClick={() => {
                  onSiteChange({
                    name: loc.name,
                    shortName: loc.name.split(',')[0],
                    lat: loc.lat,
                    lon: loc.lon,
                    areaKm2: loc.areaKm2,
                    terrainType: loc.terrain,
                  });
                  renderBoundary(loc.lat, loc.lon, loc.areaKm2);
                }}
                className={`flex-shrink-0 px-2.5 py-1 rounded-xl text-xs font-semibold backdrop-blur-md transition-all ${
                  site.name.includes(loc.name.split(',')[0])
                    ? 'bg-[#FFD21F] text-slate-950 shadow-sm font-bold'
                    : 'bg-white/80 text-slate-700 hover:bg-white border border-white/60'
                }`}
              >
                {loc.name.split(',')[0]}
              </button>
            ))}
          </div>
        )}

        {/* Radius Mode Toolbar */}
        {mode === 'radius' && (
          <div
            id="radius-mode-container"
            className="flex flex-wrap items-center gap-2 bg-white/95 backdrop-blur-xl border border-white/90 p-2 rounded-2xl shadow-glass pointer-events-auto"
          >
            <span className="text-xs font-bold text-slate-600 mr-1">Concession Radius:</span>
            {[1, 5, 10, 25, 50, 100].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => handleApplyRadius(r)}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                  selectedRadius === r
                    ? 'bg-[#FFD21F] text-slate-950 shadow-sm'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {r} km
              </button>
            ))}
            <div className="flex items-center gap-1.5 ml-auto">
              <input
                id="custom-radius-input"
                type="number"
                min="0.5"
                max="200"
                step="0.5"
                value={customRadius}
                onChange={(e) => setCustomRadius(e.target.value)}
                placeholder="Custom km"
                className="w-20 px-2 py-1 text-xs rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-1 focus:ring-[#FFD21F]"
              />
              <button
                type="button"
                id="btn-apply-custom-radius"
                onClick={() => {
                  const r = parseFloat(customRadius);
                  if (!isNaN(r) && r > 0) handleApplyRadius(r);
                }}
                className="px-3 py-1 rounded-xl bg-[#FFD21F] text-slate-950 text-xs font-bold hover:bg-[#F2C50F]"
              >
                Apply
              </button>
            </div>
          </div>
        )}

        {/* Draw Mode Toolbar */}
        {mode === 'draw' && (
          <div
            id="draw-mode-hint"
            className="flex flex-wrap items-center justify-between gap-2 bg-white/95 backdrop-blur-xl border border-white/90 p-2.5 rounded-2xl shadow-glass pointer-events-auto"
          >
            <div className="flex items-center gap-2 text-xs text-slate-800">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse flex-shrink-0" />
              <span id="draw-status-label" className="font-medium">
                {drawnPoints.length === 0
                  ? 'Click satellite map to place boundary vertices.'
                  : `${drawnPoints.length} vertices placed. ${drawStats ? `Area: ${drawStats.areaKm2.toFixed(1)} km²` : 'Place 3+ points.'}`}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                id="btn-close-polygon-draw"
                disabled={drawnPoints.length < 3}
                onClick={handleClosePolygon}
                className="px-3 py-1.5 rounded-xl bg-[#FFD21F] text-slate-950 text-xs font-bold hover:bg-[#F2C50F] disabled:opacity-40 transition-all"
              >
                Close Polygon
              </button>
              <button
                type="button"
                id="btn-clear-polygon-draw"
                onClick={() => setDrawnPoints([])}
                className="px-3 py-1.5 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold hover:bg-slate-200"
              >
                Clear
              </button>
              <button
                type="button"
                id="btn-fit-drawn-polygon"
                onClick={handleFitSite}
                className="px-3 py-1.5 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold hover:bg-slate-200"
              >
                Fit Site
              </button>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {searchError && (
          <div className="bg-red-500/90 text-white text-xs px-3.5 py-1.5 rounded-xl backdrop-blur-md shadow-md flex items-center justify-between pointer-events-auto">
            <span>{searchError}</span>
            <button onClick={() => setSearchError('')} className="p-0.5 hover:opacity-75">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* ── MAP CONTAINER ────────────────────────────────────────── */}
      <div className="relative flex-1 w-full h-full">
        {/* Leaflet 2D Map */}
        <div
          ref={mapContainerRef}
          id="map"
          className={`w-full h-full ${is3DActive ? 'hidden' : 'block'}`}
        />

        {/* Cesium 3D Globe */}
        <div
          id="screen1-cesium"
          className={`w-full h-full absolute inset-0 ${is3DActive ? 'block' : 'hidden'}`}
        />

        {/* Floating Map Utility Buttons (Right Column) */}
        <div className="absolute top-28 right-3 md:right-[404px] z-20 flex flex-col gap-1.5 pointer-events-auto">
          <button
            id="btn-map-zoom-in"
            onClick={() => mapRef.current?.zoomIn()}
            className="w-9 h-9 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass flex items-center justify-center text-slate-700 hover:text-slate-950 hover:bg-white active:scale-95 transition-all"
            title="Zoom In"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
          </button>
          <button
            id="btn-map-zoom-out"
            onClick={() => mapRef.current?.zoomOut()}
            className="w-9 h-9 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass flex items-center justify-center text-slate-700 hover:text-slate-950 hover:bg-white active:scale-95 transition-all"
            title="Zoom Out"
          >
            <Minus className="w-4 h-4 stroke-[2.5]" />
          </button>
          <button
            id="btn-map-recenter"
            onClick={() => mapRef.current?.setView([site.lat, site.lon], 12)}
            className="w-9 h-9 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass flex items-center justify-center text-slate-700 hover:text-slate-950 hover:bg-white active:scale-95 transition-all"
            title="Recenter Site"
          >
            <Compass className="w-4 h-4 text-amber-500" />
          </button>
        </div>

        {/* Bottom Floating Map Contextual Bar */}
        <div
          id="map-contextual-bar"
          className="absolute bottom-24 sm:bottom-6 left-3 right-3 sm:left-6 sm:right-auto z-20 flex flex-wrap items-center gap-1.5 pointer-events-auto"
        >
          <button
            id="btn-ctx-fit"
            onClick={handleFitSite}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>🎯 Fit Site</span>
          </button>
          <button
            id="btn-ctx-gps"
            onClick={handleUseGps}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>⌖ Current Location</span>
          </button>
          <button
            id="btn-ctx-coords"
            onClick={() => setShowCoordsPopup(!showCoordsPopup)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>📍 Coordinates</span>
          </button>
          <button
            id="btn-ctx-circle"
            onClick={() => handleApplyRadius(5)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>⭕ Circle</span>
          </button>
          <button
            id="btn-ctx-poly"
            onClick={handleResetBoundary}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>📐 Polygon</span>
          </button>
          <button
            id="btn-ctx-reset"
            onClick={handleResetBoundary}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-500 hover:bg-white active:scale-95 transition-all"
          >
            <span>↺ Reset</span>
          </button>
          <button
            id="btn-ctx-data-sources"
            onClick={onOpenDataSources}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>🌐 Data Sources</span>
          </button>
        </div>

        {/* Manual Coordinates Input Popup */}
        {showCoordsPopup && (
          <div
            id="ctx-coords-popup"
            className="absolute bottom-36 left-4 z-30 bg-white/95 backdrop-blur-2xl border border-white/90 rounded-3xl p-4 shadow-glass w-72 pointer-events-auto"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-3">
              <span className="text-xs font-bold text-slate-800">Enter Coordinates</span>
              <button onClick={() => setShowCoordsPopup(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-col gap-2.5">
              <div>
                <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Latitude (°N)
                </label>
                <input
                  id="ctx-coord-lat"
                  type="number"
                  step="0.0001"
                  value={manualLat}
                  onChange={(e) => setManualLat(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#FFD21F] font-mono"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Longitude (°E)
                </label>
                <input
                  id="ctx-coord-lon"
                  type="number"
                  step="0.0001"
                  value={manualLon}
                  onChange={(e) => setManualLon(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#FFD21F] font-mono"
                />
              </div>
              <button
                type="button"
                id="btn-apply-ctx-coords"
                onClick={handleApplyCoordinates}
                className="w-full py-2 bg-[#FFD21F] text-slate-950 text-xs font-bold rounded-xl hover:bg-[#F2C50F] transition-all mt-1"
              >
                Apply Coordinates
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── BOTTOM/RIGHT SITE INTELLIGENCE INSPECTOR (Liquid Glass) ── */}
      <aside
        id="site-info-panel"
        className={`fixed md:absolute bottom-16 right-0 left-0 md:left-auto md:top-3 md:bottom-3 md:w-96 z-20 pointer-events-auto flex flex-col transition-all duration-300 ${
          isSheetCollapsed ? 'translate-y-[calc(100%-54px)] md:translate-y-0 md:w-14' : 'translate-y-0'
        }`}
      >
        <div className="h-full bg-white/95 backdrop-blur-2xl border-t md:border border-white/90 md:rounded-3xl shadow-glass flex flex-col overflow-hidden max-h-[80vh] md:max-h-full">
          
          {/* Sheet Header / Drag Handle */}
          <div
            id="site-info-header"
            onClick={() => setIsSheetCollapsed(!isSheetCollapsed)}
            className="p-3.5 flex items-center justify-between cursor-pointer border-b border-slate-100 flex-shrink-0"
          >
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-xl bg-[#FFD21F]/20 text-slate-900">
                <MapPin className="w-4 h-4 text-amber-600" />
              </span>
              <div>
                <h3 className="text-xs font-bold text-slate-900 leading-tight">Site Intelligence</h3>
                <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Real-time Geotechnical
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="text-right">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Area</div>
                <div id="meta-area" className="text-xs font-black text-slate-900 font-mono">
                  {(site.areaKm2 || 24.8).toFixed(1)} km²
                </div>
              </div>
              <button className="p-1 text-slate-400 hover:text-slate-700">
                {isSheetCollapsed ? <Plus className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Scrollable Content Body */}
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3.5 text-xs">
            
            {/* Real Terrain Photo Card */}
            <div className="relative rounded-2xl overflow-hidden border border-slate-200 shadow-xs h-24">
              <img
                src="/assets/real-turbines-photo.jpg"
                alt="Selected site terrain profile"
                onError={(e) => { (e.currentTarget as any).src = 'https://images.unsplash.com/photo-1466611653911-95081537e5b7?w=500'; }}
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent flex items-end p-2.5">
                <span id="meta-location-name" className="text-white font-bold text-xs truncate">
                  {site.name}
                </span>
              </div>
            </div>

            {/* 9-Point Geotechnical Checklist */}
            <div id="site-intelligence-card" className="p-3 rounded-2xl bg-slate-50/80 border border-slate-200/80">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">Site Checks</span>
                <span id="intel-overall-pill" className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                  ✓ Verified
                </span>
              </div>
              <div id="intel-checks-list" className="flex flex-col gap-1.5">
                {intelItems.map((item, idx) => (
                  <div key={idx} className="flex items-start justify-between gap-1 text-[11px] text-slate-600">
                    <div className="flex items-center gap-1.5">
                      {item.status === 'verified' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                      )}
                      <span>{item.label}</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 text-right truncate max-w-[130px]">
                      {item.source}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Metadata Table */}
            <div className="p-3 rounded-2xl bg-white border border-slate-200/80 flex flex-col gap-1.5 font-mono text-[11px]">
              <div className="flex justify-between text-slate-600">
                <span className="font-sans text-slate-400">Latitude</span>
                <strong id="meta-latitude" className="text-slate-900">{site.lat.toFixed(4)}° N</strong>
              </div>
              <div className="flex justify-between text-slate-600">
                <span className="font-sans text-slate-400">Longitude</span>
                <strong id="meta-longitude" className="text-slate-900">{site.lon.toFixed(4)}° E</strong>
              </div>
              <div className="flex justify-between text-slate-600">
                <span className="font-sans text-slate-400">Elevation</span>
                <strong id="meta-elevation" className="text-slate-900">{site.elevationM || 42} m</strong>
              </div>
              <div className="flex justify-between text-slate-600">
                <span className="font-sans text-slate-400">Terrain</span>
                <strong id="meta-terrain" className="text-slate-900 truncate max-w-[140px]">{site.terrainType || 'Coastal'}</strong>
              </div>
              <div className="flex justify-between text-slate-600">
                <span className="font-sans text-slate-400">Coast Distance</span>
                <strong id="meta-coast" className="text-slate-900">{site.distanceToCoastKm || 0.2} km</strong>
              </div>
              <div className="pt-1 border-t border-slate-100 flex flex-col gap-0.5">
                <span className="font-sans text-[10px] text-slate-400">5-Class Feasibility</span>
                <span id="meta-land-feasibility" className="text-[10px] text-emerald-700">
                  ✓ 8 Preferred · 12 Buildable · 4 Excluded
                </span>
              </div>
            </div>

            {/* Live Wind Telemetry Card */}
            <div className="p-3 rounded-2xl bg-amber-50/60 border border-amber-200/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-amber-950 text-[11px] uppercase tracking-wider">Wind Resource</span>
                <span id="meta-source-badge" onClick={onOpenDataSources} className="text-[10px] font-bold text-amber-700 underline cursor-pointer">
                  ECMWF / SRTM ⓘ
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-500 text-[10px]">Speed (100m)</span>
                  <div id="meta-wind-speed" className="font-black text-slate-900 font-mono">
                    {(site.windSpeedMps || 7.1).toFixed(1)} m/s
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px]">Power Density</span>
                  <div id="meta-wind-density" className="font-black text-slate-900 font-mono">
                    ~ {site.windPowerDensity || 320} W/m²
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px]">Direction</span>
                  <div id="meta-wind-dir" className="font-black text-slate-900 font-mono">
                    {site.windDirectionDeg || 300}°
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px]">Air Density</span>
                  <div id="meta-air-density" className="font-black text-slate-900 font-mono">
                    {site.airDensityKgpm3 || 1.18} kg/m³
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-2 pt-1 mt-auto">
              <Button
                id="btn-confirm-site"
                variant="energy"
                size="md"
                onClick={onConfirmSite}
                className="w-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black shadow-md py-3 text-xs"
              >
                <span>Confirm Site Boundary</span>
                <ArrowRight className="w-4 h-4 stroke-[2.5]" />
              </Button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
};
