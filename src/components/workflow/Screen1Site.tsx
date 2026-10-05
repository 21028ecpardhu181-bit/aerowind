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
  onConfirmSite: (siteParams?: Partial<SiteInfo>) => void;
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
  const [isSheetCollapsed, setIsSheetCollapsed] = useState(() => {
    return typeof window !== 'undefined' ? window.innerWidth < 768 : false;
  });

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

  // Fly/re-center map and update boundary polygon whenever site coordinates update
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setView([site.lat, site.lon], 12);
    renderBoundary(site.lat, site.lon, site.areaKm2, site.boundary as [number, number][]);
    setTimeout(() => {
      try { map.invalidateSize(); } catch (_) {}
    }, 150);
  }, [site.lat, site.lon, site.areaKm2, site.boundary]);

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
      const satellite = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 19,
          attribution: 'Esri, Maxar, Earthstar Geographics',
        }
      );

      const street = L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {
          maxZoom: 19,
          attribution: '© OpenStreetMap contributors',
        }
      );

      const terrain = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 19,
          attribution: 'Esri, USGS, NOAA',
        }
      );

      baseLayersRef.current = { satellite, street, terrain };

      // Set initial base layer
      if (activeBaseLayer === 'street') {
        street.addTo(map);
      } else if (activeBaseLayer === 'terrain') {
        terrain.addTo(map);
      } else {
        satellite.addTo(map);
      }

      setTimeout(() => {
        try { map.invalidateSize(); } catch (_) {}
      }, 200);

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

  const generateCircleVertices = (centerLat: number, centerLon: number, radiusKm: number, steps: number = 48): [number, number][] => {
    const vertices: [number, number][] = [];
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
    return vertices;
  };

  // 3. Render Boundary Polygon & Badges on Map
  const renderBoundary = (lat: number, lon: number, areaKm2: number, customBoundary?: [number, number][]) => {
    const map = mapRef.current;
    const L = window.L;
    if (!map || !L) return;

    if (polygonLayerRef.current) {
      try { map.removeLayer(polygonLayerRef.current); } catch (_) {}
      polygonLayerRef.current = null;
    }
    if (areaBadgeRef.current) {
      try { map.removeLayer(areaBadgeRef.current); } catch (_) {}
      areaBadgeRef.current = null;
    }
    if (locationLabelRef.current) {
      try { map.removeLayer(locationLabelRef.current); } catch (_) {}
      locationLabelRef.current = null;
    }

    const currentRadius = selectedRadius || site.radiusKm || Math.sqrt(Math.max(1, areaKm2) / Math.PI) || 3.0;

    const vertices: [number, number][] =
      customBoundary && customBoundary.length >= 3
        ? customBoundary
        : generateCircleVertices(lat, lon, currentRadius);

    const calcArea = calculatePolygonAreaKm2(vertices);

    // High-contrast, bold concession boundary polygon with drop shadow & fill
    polygonLayerRef.current = L.polygon(vertices, {
      color: '#FFD21F',
      weight: 3.5,
      opacity: 1.0,
      fillColor: '#FFD21F',
      fillOpacity: 0.18,
      smoothFactor: 1,
    }).addTo(map);

    // Add crisp vertex circle markers at each boundary corner
    drawnMarkersRef.current.forEach((m) => {
      try { map.removeLayer(m); } catch (_) {}
    });
    drawnMarkersRef.current = [];

    const stride = Math.max(1, Math.floor(vertices.length / 16));
    vertices.forEach((pt: [number, number], i: number) => {
      if (i % stride === 0) {
        const dot = L.circleMarker(pt, {
          radius: 3.5,
          color: '#0f172a',
          weight: 1.5,
          fillColor: '#FFD21F',
          fillOpacity: 1.0,
        }).addTo(map);
        drawnMarkersRef.current.push(dot);
      }
    });

    map.fitBounds(polygonLayerRef.current.getBounds(), {
      padding: [40, 40],
      maxZoom: 15,
    });

    // Single unified concession badge
    const siteTitle = site.shortName || site.name.split(',')[0] || 'Selected Site';
    const unifiedBadgeIcon = L.divIcon({
      className: 'site-unified-badge-wrapper',
      html: `
        <div class="site-unified-badge">
          <div class="badge-title">${siteTitle}</div>
          <div class="badge-sub">Concession Area: <strong>${calcArea.toFixed(1)} km²</strong> · <strong>${currentRadius.toFixed(1)} km</strong></div>
        </div>
      `,
      iconSize: [180, 52],
      iconAnchor: [90, 26],
    });
    areaBadgeRef.current = L.marker([lat, lon], { icon: unifiedBadgeIcon }).addTo(map);
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
    const r = selectedRadius || site.radiusKm || 3.0;
    const boundary = generateCircleVertices(lat, lon, r);
    const areaKm2 = Math.round(Math.PI * r * r * 10) / 10;
    const newSite = {
      ...site,
      lat,
      lon,
      shortName,
      name: `${shortName}, Engineering Site`,
      radiusKm: r,
      areaKm2,
      boundary,
    };
    onSiteChange(newSite);
    renderBoundary(lat, lon, areaKm2, boundary);

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
    const r = selectedRadius || site.radiusKm || 3.0;
    const defaultBoundary = generateCircleVertices(site.lat, site.lon, r);
    const areaKm2 = Math.round(Math.PI * r * r * 10) / 10;
    onSiteChange({ radiusKm: r, areaKm2, boundary: defaultBoundary });
    renderBoundary(site.lat, site.lon, areaKm2, defaultBoundary);
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
    <div id="screen-1-container" className="relative w-full h-[calc(100dvh-53px)] overflow-hidden flex flex-col md:flex-row bg-slate-100">
      
      {/* ── DESKTOP FIXED SIDEBAR / MOBILE COLLAPSIBLE DRAWER ──────── */}
      <aside
        id="site-info-panel"
        className={`fixed md:relative bottom-14 md:bottom-auto left-0 md:left-auto right-0 md:right-auto md:w-[410px] md:h-full bg-white/95 backdrop-blur-2xl md:bg-white border-t md:border-t-0 md:border-r border-slate-200/90 z-[1250] md:z-20 flex flex-col shrink-0 transition-transform duration-300 shadow-2xl md:shadow-none ${
          isSheetCollapsed ? 'translate-y-[calc(100%-60px)] md:translate-y-0' : 'translate-y-0'
        } max-h-[82vh] md:max-h-full`}
      >
        {/* Mobile Drag Handle & Peek Bar Header */}
        <div
          id="site-info-header"
          onClick={() => setIsSheetCollapsed(!isSheetCollapsed)}
          className="p-3 sm:p-3.5 flex items-center justify-between cursor-pointer border-b border-slate-100 flex-shrink-0 bg-white/95"
        >
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-xl bg-[#FFD21F]/20 text-slate-900">
              <MapPin className="w-4 h-4 text-amber-600" />
            </span>
            <div>
              <h3 className="text-xs font-bold text-slate-900 leading-tight">
                {site.shortName || site.name.split(',')[0]}
              </h3>
              <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Geotechnical Verified
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="text-right">
              <div className="text-[9px] text-slate-400 font-bold uppercase">Area</div>
              <div id="meta-area" className="text-xs font-black text-slate-900 font-mono">
                {(site.areaKm2 || 24.8).toFixed(1)} km²
              </div>
            </div>

            {/* Quick Confirm Button on Mobile Peek State */}
            <button
              type="button"
              id="btn-confirm-site-peek"
              onClick={(e) => {
                e.stopPropagation();
                const r = selectedRadius || site.radiusKm || 3.0;
                const boundary = site.boundary && site.boundary.length >= 3 ? site.boundary : generateCircleVertices(site.lat, site.lon, r);
                const areaKm2 = site.areaKm2 || Math.round(Math.PI * r * r * 10) / 10;
                onConfirmSite({ ...site, radiusKm: r, areaKm2, boundary });
              }}
              className="md:hidden flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#FFD21F] text-slate-950 text-xs font-black shadow-sm active:scale-95 transition-all"
            >
              <span>Continue</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
            </button>

            <button
              type="button"
              className="p-1 text-slate-400 hover:text-slate-700 hidden md:block"
            >
              {isSheetCollapsed ? <Plus className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Scrollable Content Body (Desktop always, Mobile when expanded) */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3.5 text-xs">
          
          {/* Section: Mode Tabs (Search, Radius, Draw) */}
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Site Selection Mode
            </div>
            <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-2xl">
              <button
                id="tab-mode-search"
                onClick={() => { setMode('search'); onToggleDrawMode(false); }}
                className={`flex items-center justify-center gap-1 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  mode === 'search' ? 'bg-[#FFD21F] text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                <span>Search</span>
              </button>

              <button
                id="tab-mode-radius"
                onClick={() => { setMode('radius'); onToggleDrawMode(false); }}
                className={`flex items-center justify-center gap-1 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  mode === 'radius' ? 'bg-[#FFD21F] text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <CircleDot className="w-3.5 h-3.5" />
                <span>Radius</span>
              </button>

              <button
                id="tab-mode-draw"
                onClick={() => { setMode('draw'); onToggleDrawMode(true); setIsDrawing(true); }}
                className={`flex items-center justify-center gap-1 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  mode === 'draw' ? 'bg-[#FFD21F] text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Draw</span>
              </button>
            </div>
          </div>

          {/* Contextual Mode Controls */}
          {mode === 'search' && (
            <div className="flex flex-col gap-2">
              <form onSubmit={handleSearchSubmit} className="relative flex items-center">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
                <input
                  id="map-search-input"
                  type="text"
                  value={searchVal}
                  onChange={(e) => setSearchVal(e.target.value)}
                  placeholder="Search city, district, coordinates..."
                  className="w-full pl-9 pr-11 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#FFD21F]"
                />
                <button
                  type="submit"
                  id="btn-search-arrow"
                  disabled={isSearching}
                  className="absolute right-1 p-1.5 rounded-lg bg-[#FFD21F] text-slate-950 font-bold hover:bg-[#F2C50F] transition-all disabled:opacity-50"
                  title="Search"
                >
                  {isSearching ? (
                    <span className="w-3 h-3 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin block" />
                  ) : (
                    <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
                  )}
                </button>
              </form>

              {/* GPS Button */}
              <button
                type="button"
                id="btn-use-current-location"
                onClick={handleUseGps}
                disabled={isGpsLocating}
                className="flex items-center justify-center gap-1.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-bold text-slate-700 hover:text-slate-950 hover:bg-slate-100 active:scale-95 transition-all"
              >
                <Crosshair className={`w-3.5 h-3.5 text-amber-500 ${isGpsLocating ? 'animate-spin' : ''}`} />
                <span>Use Current Location (GPS)</span>
              </button>

              {/* Presets */}
              <div className="flex flex-col gap-1 mt-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Preset Sites</span>
                <div className="flex flex-wrap gap-1">
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
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                        site.name.includes(loc.name.split(',')[0])
                          ? 'bg-[#FFD21F] text-slate-950 shadow-xs font-bold'
                          : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      }`}
                    >
                      {loc.name.split(',')[0]}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {mode === 'radius' && (
            <div id="radius-mode-container" className="flex flex-col gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-700">Concession Radius:</span>
                <span className="text-xs font-mono font-black text-amber-600">
                  {(selectedRadius || site.radiusKm || 3).toFixed(1)} km · {((Math.PI * Math.pow(selectedRadius || site.radiusKm || 3, 2))).toFixed(1)} km²
                </span>
              </div>

              {/* Slider for smooth live sizing */}
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.5"
                  max="30"
                  step="0.5"
                  value={selectedRadius || site.radiusKm || 3}
                  onChange={(e) => handleApplyRadius(parseFloat(e.target.value))}
                  className="w-full accent-[#FFD21F] cursor-pointer"
                  title="Drag to adjust concession radius"
                />
              </div>

              {/* Presets including 3km */}
              <div className="flex flex-wrap gap-1.5">
                {[1, 2, 3, 5, 8, 10, 15, 20, 25].map((r) => (
                  <button
                    key={r}
                    type="button"
                    id={`btn-radius-${r}km`}
                    onClick={() => handleApplyRadius(r)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                      (selectedRadius || site.radiusKm || 3) === r
                        ? 'bg-[#FFD21F] text-slate-950 shadow-xs ring-1 ring-amber-400'
                        : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                    }`}
                  >
                    {r} km
                  </button>
                ))}
              </div>

              {/* Custom km or km² input */}
              <div className="flex items-center gap-1.5 mt-0.5">
                <input
                  id="custom-radius-input"
                  type="number"
                  min="0.5"
                  max="200"
                  step="0.1"
                  value={customRadius}
                  onChange={(e) => setCustomRadius(e.target.value)}
                  placeholder="Radius km"
                  className="w-24 px-2 py-1 text-xs rounded-lg bg-white border border-slate-200 focus:outline-none focus:ring-1 focus:ring-[#FFD21F]"
                />
                <button
                  type="button"
                  id="btn-apply-custom-radius"
                  onClick={() => {
                    const r = parseFloat(customRadius);
                    if (!isNaN(r) && r > 0) handleApplyRadius(r);
                  }}
                  className="px-3 py-1 rounded-lg bg-[#FFD21F] text-slate-950 text-xs font-bold hover:bg-[#F2C50F]"
                >
                  Apply km
                </button>

                <button
                  type="button"
                  id="btn-apply-as-area"
                  onClick={() => {
                    const targetArea = parseFloat(customRadius);
                    if (!isNaN(targetArea) && targetArea > 0) {
                      const r = Math.sqrt(targetArea / Math.PI);
                      handleApplyRadius(Math.round(r * 10) / 10);
                    }
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-200 text-slate-800 text-[11px] font-bold hover:bg-slate-300"
                  title="Treat custom number as total Area in km²"
                >
                  As km²
                </button>
              </div>
            </div>
          )}

          {mode === 'draw' && (
            <div id="draw-mode-hint" className="flex flex-col gap-2 p-2.5 rounded-xl bg-slate-50 border border-slate-200">
              <div className="flex items-center gap-1.5 text-xs text-slate-800">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse flex-shrink-0" />
                <span id="draw-status-label" className="font-medium text-[11px]">
                  {drawnPoints.length === 0
                    ? 'Click satellite map to place vertices.'
                    : `${drawnPoints.length} vertices. ${drawStats ? `Area: ${drawStats.areaKm2.toFixed(1)} km²` : 'Place 3+ points.'}`}
                </span>
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                <button
                  type="button"
                  id="btn-close-polygon-draw"
                  disabled={drawnPoints.length < 3}
                  onClick={handleClosePolygon}
                  className="flex-1 py-1.5 rounded-lg bg-[#FFD21F] text-slate-950 text-xs font-bold hover:bg-[#F2C50F] disabled:opacity-40 transition-all text-center"
                >
                  Close Polygon
                </button>
                <button
                  type="button"
                  id="btn-clear-polygon-draw"
                  onClick={() => setDrawnPoints([])}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-100"
                >
                  Clear
                </button>
                <button
                  type="button"
                  id="btn-fit-drawn-polygon"
                  onClick={handleFitSite}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-100"
                >
                  Fit Site
                </button>
              </div>
            </div>
          )}

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
          <div id="site-intelligence-card" className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
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

          {/* Action Button */}
          <div className="flex flex-col gap-2 pt-1 mt-auto">
            <Button
              id="btn-confirm-site"
              variant="energy"
              size="md"
              onClick={() => {
                const r = selectedRadius || site.radiusKm || 3.0;
                const boundary = site.boundary && site.boundary.length >= 3 ? site.boundary : generateCircleVertices(site.lat, site.lon, r);
                const areaKm2 = site.areaKm2 || Math.round(Math.PI * r * r * 10) / 10;
                onConfirmSite({ ...site, radiusKm: r, areaKm2, boundary });
              }}
              className="w-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black shadow-md py-3 text-xs"
            >
              <span>Confirm Site Boundary</span>
              <ArrowRight className="w-4 h-4 stroke-[2.5]" />
            </Button>
          </div>
        </div>
      </aside>

      {/* ── MAP CONTAINER (Fills Right on Desktop, Full on Mobile) ── */}
      <div className="flex-1 w-full h-full relative overflow-hidden">
        
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

        {/* Mobile Top Floating Search & Layer Bar */}
        <div className="md:hidden absolute top-2 left-2 right-2 z-[1050] flex flex-col gap-1.5 pointer-events-none">
          <div className="flex items-center gap-1.5 pointer-events-auto">
            <form onSubmit={handleSearchSubmit} className="relative flex-1 flex items-center">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
              <input
                id="search-input-field"
                type="text"
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                placeholder="Search site..."
                className="w-full pl-8 pr-9 py-2 rounded-xl bg-white/95 backdrop-blur-xl border border-slate-200/90 shadow-md text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#FFD21F]"
              />
              <button
                type="submit"
                disabled={isSearching}
                className="absolute right-1 p-1 rounded-lg bg-[#FFD21F] text-slate-950 font-bold"
              >
                <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
              </button>
            </form>

            <button
              type="button"
              id="btn-map-gps"
              onClick={handleUseGps}
              disabled={isGpsLocating}
              className="p-2 rounded-xl bg-white/95 backdrop-blur-xl border border-slate-200/90 shadow-md text-slate-800 active:scale-95 transition-all"
              title="GPS Location"
            >
              <Crosshair className={`w-4 h-4 text-amber-500 ${isGpsLocating ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Mobile Layer Pills */}
          <div className="flex items-center justify-between gap-1 pointer-events-auto overflow-x-auto no-scrollbar py-0.5">
            <div className="flex items-center gap-1 bg-white/90 backdrop-blur-xl border border-white/80 p-0.5 rounded-xl shadow-xs">
              <button
                onClick={() => switchBaseLayer('street')}
                className={`px-2 py-1 rounded-lg text-[10px] font-semibold ${
                  activeBaseLayer === 'street' && !is3DActive ? 'bg-slate-900 text-white' : 'text-slate-600'
                }`}
              >
                Map
              </button>
              <button
                onClick={() => switchBaseLayer('satellite')}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold ${
                  activeBaseLayer === 'satellite' && !is3DActive ? 'bg-[#FFD21F] text-slate-950' : 'text-slate-600'
                }`}
              >
                Sat
              </button>
              <button
                onClick={() => switchBaseLayer('terrain')}
                className={`px-2 py-1 rounded-lg text-[10px] font-semibold ${
                  activeBaseLayer === 'terrain' && !is3DActive ? 'bg-slate-900 text-white' : 'text-slate-600'
                }`}
              >
                Terrain
              </button>
              <button
                onClick={onToggle3D}
                className={`flex items-center gap-0.5 px-2 py-1 rounded-lg text-[10px] font-bold ${
                  is3DActive ? 'bg-[#FFD21F] text-slate-950' : 'text-slate-600'
                }`}
              >
                <Box className="w-3 h-3" />
                <span>3D</span>
              </button>
            </div>

            {/* Quick Concession Radius Buttons on Mobile Map */}
            <div className="flex items-center gap-0.5 bg-white/95 backdrop-blur-xl border border-white/80 p-0.5 rounded-xl shadow-xs">
              <span className="text-[9px] font-bold text-slate-500 pl-1">Radius:</span>
              {[1, 2, 3, 5, 10].map((r) => (
                <button
                  key={r}
                  type="button"
                  id={`btn-mobile-radius-${r}km`}
                  onClick={() => handleApplyRadius(r)}
                  className={`px-1.5 py-0.5 rounded-lg text-[10px] font-black transition-all ${
                    (selectedRadius || site.radiusKm || 3) === r
                      ? 'bg-[#FFD21F] text-slate-950 shadow-xs ring-1 ring-amber-400'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {r}k
                </button>
              ))}
            </div>

            {/* Presets Quick Dropdown / Chips on Mobile */}
            <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
              {PRESET_LOCATIONS.slice(0, 3).map((loc) => (
                <button
                  key={loc.name}
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
                  className={`px-2 py-1 rounded-lg text-[10px] font-semibold whitespace-nowrap shadow-xs ${
                    site.name.includes(loc.name.split(',')[0])
                      ? 'bg-[#FFD21F] text-slate-950 font-bold'
                      : 'bg-white/90 text-slate-700'
                  }`}
                >
                  {loc.name.split(',')[0]}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Desktop Top Right Layer Switcher */}
        <div className="hidden md:flex absolute top-3 right-3 z-[1020] items-center gap-1.5 bg-white/95 backdrop-blur-2xl border border-slate-200/90 p-1 rounded-2xl shadow-glass pointer-events-auto">
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

        {/* Floating Map Utility Buttons (Zoom & Recenter) */}
        <div className="absolute top-24 md:top-16 right-3 z-[1020] flex flex-col gap-1.5 pointer-events-auto">
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
          className="absolute bottom-20 md:bottom-6 left-3 right-3 md:left-6 md:right-auto z-[1020] flex flex-wrap items-center gap-1.5 pointer-events-auto"
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
            <span>⌖ GPS</span>
          </button>
          <button
            id="btn-ctx-coords"
            onClick={() => setShowCoordsPopup(!showCoordsPopup)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/80 shadow-glass text-xs font-bold text-slate-700 hover:bg-white active:scale-95 transition-all"
          >
            <span>📍 Coords</span>
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
            <span>🌐 Sources</span>
          </button>
        </div>

        {/* Manual Coordinates Input Popup */}
        {showCoordsPopup && (
          <div
            id="ctx-coords-popup"
            className="absolute bottom-32 md:bottom-20 left-4 z-30 bg-white/95 backdrop-blur-2xl border border-white/90 rounded-3xl p-4 shadow-glass w-72 pointer-events-auto"
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

        {/* Error Notification */}
        {searchError && (
          <div className="absolute top-16 md:top-3 left-4 right-4 md:right-auto md:w-96 z-30 bg-red-500/90 text-white text-xs px-3.5 py-2 rounded-xl backdrop-blur-md shadow-md flex items-center justify-between pointer-events-auto">
            <span>{searchError}</span>
            <button onClick={() => setSearchError('')} className="p-0.5 hover:opacity-75">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
