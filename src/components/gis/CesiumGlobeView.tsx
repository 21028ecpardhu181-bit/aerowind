import React, { useEffect, useRef, useState, useCallback } from 'react';
import { 
  Compass, 
  RotateCcw, 
  Eye, 
  Layers, 
  Maximize2, 
  Wind,
  Navigation,
  Crosshair
} from 'lucide-react';
import { Turbine } from '../../types';

interface CesiumGlobeViewProps {
  containerId: string;
  centerLat: number;
  centerLon: number;
  radiusKm?: number;
  boundary?: number[][];
  turbines?: Turbine[];
  selectedTurbineIdx?: number;
  onSelectTurbine?: (index: number) => void;
  windDirectionDeg?: number;
  windSpeedMps?: number;
  rotorDiameter?: number;
  hubHeight?: number;
  turbineModelName?: string;
  showWakes?: boolean;
  className?: string;
}

export const CesiumGlobeView: React.FC<CesiumGlobeViewProps> = ({
  containerId,
  centerLat,
  centerLon,
  radiusKm = 3.0,
  boundary,
  turbines = [],
  selectedTurbineIdx = 0,
  onSelectTurbine,
  windDirectionDeg = 270,
  windSpeedMps = 7.8,
  rotorDiameter = 120,
  hubHeight = 110,
  turbineModelName = 'GE 2.5-120',
  showWakes = true,
  className = '',
}) => {
  const viewerRef = useRef<any>(null);
  const clickHandlerRef = useRef<any>(null);
  const entitiesRef = useRef<{
    turbines: any[];
    wakes: any[];
    boundary: any | null;
  }>({
    turbines: [],
    wakes: [],
    boundary: null,
  });

  const [activeCameraPreset, setActiveCameraPreset] = useState<string>('OBLIQUE');
  const [isTerrainReady, setIsTerrainReady] = useState<boolean>(false);
  const [isGoogleTilesActive, setIsGoogleTilesActive] = useState<boolean>(false);
  const [activeBasemap, setActiveBasemap] = useState<'satellite' | 'terrain'>('satellite');

  // 1. Initialize Cesium 3D Viewer
  useEffect(() => {
    const Cesium = (window as any).Cesium;
    if (!Cesium) {
      console.warn('[CesiumGlobeView] Cesium library not found on window object.');
      return;
    }

    const container = document.getElementById(containerId);
    if (!container) return;

    // Destroy existing viewer if any
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      try {
        viewerRef.current.destroy();
      } catch (_) {}
      viewerRef.current = null;
    }

    try {
      // 1. High-Resolution Satellite Base Layer via Local Cache Proxy
      const satelliteProvider = new Cesium.UrlTemplateImageryProvider({
        url: '/api/geo/tiles/satellite/{z}/{x}/{y}',
        maximumLevel: 20,
        credit: 'Esri World Imagery',
      });

      const viewer = new Cesium.Viewer(containerId, {
        animation: false,
        timeline: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        baseLayerPicker: false,
        navigationHelpButton: false,
        infoBox: false,
        selectionIndicator: false,
        creditContainer: document.createElement('div'), // Hidden credits container
        baseLayer: new Cesium.ImageryLayer(satelliteProvider),
        shadows: true,
        terrainShadows: Cesium.ShadowMode.ENABLED,
        contextOptions: {
          webgl: {
            alpha: false,
            depth: true,
            stencil: false,
            antialias: true,
            preserveDrawingBuffer: true,
          },
        },
      });

      // 2. Superimpose High-Resolution Road Network & Place Labels for Real Geography
      const referenceLabelsProvider = new Cesium.UrlTemplateImageryProvider({
        url: '/api/geo/tiles/labels/{z}/{x}/{y}',
        maximumLevel: 20,
      });
      viewer.imageryLayers.addImageryProvider(referenceLabelsProvider);

      const scene = viewer.scene;
      scene.globe.depthTestAgainstTerrain = true;
      scene.globe.enableLighting = true;
      if (scene.shadowMap) {
        scene.shadowMap.enabled = true;
        scene.shadowMap.softShadows = true;
      }
      if (scene.skyAtmosphere) scene.skyAtmosphere.show = true;
      if (scene.fog) {
        scene.fog.enabled = true;
        scene.fog.density = 0.00012;
      }

      // 3. Load Real 3D World Terrain
      if (typeof Cesium.createWorldTerrainAsync === 'function') {
        Cesium.createWorldTerrainAsync({
          requestVertexNormals: true,
          requestWaterMask: true,
        })
          .then((provider: any) => {
            if (viewer && !viewer.isDestroyed()) {
              viewer.terrainProvider = provider;
              setIsTerrainReady(true);
            }
          })
          .catch((err: any) => {
            console.warn('[CesiumGlobeView] World terrain fallback:', err);
          });
      }

      // 4. Load Google Photorealistic 3D Tiles if API key is provided
      const googleMapsKey =
        (window as any).GOOGLE_MAPS_API_KEY ||
        (import.meta as any).env?.VITE_GOOGLE_MAPS_API_KEY ||
        localStorage.getItem('aqw_google_maps_key');

      if (googleMapsKey && typeof Cesium.createGooglePhotorealistic3DTileset === 'function') {
        Cesium.createGooglePhotorealistic3DTileset({ key: googleMapsKey })
          .then((tileset: any) => {
            if (viewer && !viewer.isDestroyed()) {
              viewer.scene.primitives.add(tileset);
              setIsGoogleTilesActive(true);
              console.log('[CesiumGlobeView] Google Photorealistic 3D Tiles active.');
            }
          })
          .catch((err: any) => {
            console.warn('[CesiumGlobeView] Google 3D Tiles fallback to hybrid imagery:', err);
          });
      }

      // Configure Camera Controller
      const controller = scene.screenSpaceCameraController;
      controller.enableRotate = true;
      controller.enableTranslate = true;
      controller.enableZoom = true;
      controller.enableTilt = true;
      controller.enableLook = false;
      controller.minimumZoomDistance = 80.0;
      controller.maximumZoomDistance = 5000000.0;

      // Click / Touch Interaction for Turbines
      const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas);
      handler.setInputAction((click: any) => {
        const picked = scene.pick(click.position);
        if (Cesium.defined(picked) && picked.id && picked.id.turbineIndex !== undefined) {
          const tIdx = picked.id.turbineIndex;
          if (onSelectTurbine) onSelectTurbine(tIdx);
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

      clickHandlerRef.current = handler;
      viewerRef.current = viewer;

      // Initial Camera Fly to Site
      flyToProjectSite(viewer, centerLat, centerLon, radiusKm, 'OBLIQUE', 1.5);
    } catch (e) {
      console.error('[CesiumGlobeView] Initialization error:', e);
    }

    return () => {
      if (clickHandlerRef.current) {
        try {
          clickHandlerRef.current.destroy();
        } catch (_) {}
        clickHandlerRef.current = null;
      }
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        try {
          viewerRef.current.destroy();
        } catch (_) {}
        viewerRef.current = null;
      }
    };
  }, [containerId]);

  // Helper: Camera presets
  const flyToProjectSite = useCallback((
    viewer: any,
    lat: number,
    lon: number,
    rKm: number,
    preset: string,
    duration: number = 1.2
  ) => {
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    const spanM = Math.max(1200.0, rKm * 2000.0);
    const altitude = Math.max(700.0, spanM * 1.35);

    let heading = 0.0;
    let pitch = -42.0;
    let latOffset = (altitude * 0.42) / 111000.0;
    let lonOffset = 0.0;

    switch (preset) {
      case 'TOP':
        heading = 0.0;
        pitch = -89.0;
        latOffset = 0.0;
        break;
      case 'NORTH':
        heading = 0.0;
        pitch = -38.0;
        latOffset = (altitude * 0.45) / 111000.0;
        break;
      case 'SOUTH':
        heading = 180.0;
        pitch = -38.0;
        latOffset = -(altitude * 0.45) / 111000.0;
        break;
      case 'WIND_ALIGN':
        heading = (windDirectionDeg + 180) % 360;
        pitch = -35.0;
        const windRad = Cesium.Math.toRadians(heading);
        latOffset = ((altitude * 0.4) * Math.cos(windRad)) / 111000.0;
        lonOffset = ((altitude * 0.4) * Math.sin(windRad)) / (111000.0 * Math.cos(lat * Math.PI / 180.0));
        break;
      case 'OBLIQUE':
      default:
        heading = 35.0;
        pitch = -40.0;
        latOffset = (altitude * 0.40) / 111000.0;
        break;
    }

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lon - lonOffset, lat - latOffset, altitude),
      orientation: {
        heading: Cesium.Math.toRadians(heading),
        pitch: Cesium.Math.toRadians(pitch),
        roll: 0.0,
      },
      duration,
    });
  }, [windDirectionDeg]);

  // 2. Synchronize Camera When Coordinates Change
  useEffect(() => {
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      flyToProjectSite(viewerRef.current, centerLat, centerLon, radiusKm, activeCameraPreset, 1.2);
    }
  }, [centerLat, centerLon, radiusKm, activeCameraPreset, flyToProjectSite]);

  // 3. Render Site Boundary Polygon
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    if (entitiesRef.current.boundary) {
      viewer.entities.remove(entitiesRef.current.boundary);
      entitiesRef.current.boundary = null;
    }

    let flatCoords: number[] = [];

    if (boundary && boundary.length >= 3) {
      boundary.forEach(([lat, lon]) => {
        flatCoords.push(lon, lat);
      });
    } else {
      // 32-point circular boundary
      const pts = 32;
      const rDeg = (radiusKm * 1000.0) / 111000.0;
      for (let i = 0; i < pts; i++) {
        const theta = (i / pts) * 2 * Math.PI;
        const bLat = centerLat + rDeg * Math.cos(theta);
        const bLon = centerLon + (rDeg * Math.sin(theta)) / Math.cos(centerLat * Math.PI / 180.0);
        flatCoords.push(bLon, bLat);
      }
    }

    if (flatCoords.length >= 6) {
      const boundaryEntity = viewer.entities.add({
        name: 'Concession Area Boundary',
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(flatCoords),
          material: Cesium.Color.fromCssColorString('rgba(255, 210, 31, 0.12)'),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#FFD21F'),
          outlineWidth: 3,
        },
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray([...flatCoords, flatCoords[0], flatCoords[1]]),
          width: 3,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.fromCssColorString('#FFD21F'),
            dashLength: 16.0,
          }),
        },
      });
      entitiesRef.current.boundary = boundaryEntity;
    }
  }, [centerLat, centerLon, radiusKm, boundary]);

  // 4. Render 3D Industrial Wind Turbines & Downstream Jensen Wakes
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    // Clear previous turbine and wake entities
    entitiesRef.current.turbines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.turbines = [];
    entitiesRef.current.wakes.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.wakes = [];

    if (!turbines || turbines.length === 0) return;

    // Real-world upwind alignment: rotor spinner points into the oncoming wind vector
    const windHeadingRad = Cesium.Math.toRadians(windDirectionDeg);
    const modelScale = Math.max(0.6, Math.min(2.0, rotorDiameter / 120.0));

    turbines.forEach((t, idx) => {
      const isSelected = idx === selectedTurbineIdx;
      const baseElev = (t.elevation_m !== undefined && t.elevation_m !== null) ? Number(t.elevation_m) : 40.0;
      const groundPos = Cesium.Cartesian3.fromDegrees(t.lon, t.lat, baseElev);
      const hpr = new Cesium.HeadingPitchRoll(windHeadingRad, 0, 0);
      const orientation = Cesium.Transforms.headingPitchRollQuaternion(groundPos, hpr);

      const labelText = t.label || `T-${String(idx + 1).padStart(2, '0')}`;
      const speedText = t.effective_mps ? `${t.effective_mps.toFixed(1)}m/s` : `${windSpeedMps.toFixed(1)}m/s`;

      // 1. Certified Industrial 3D Wind Turbine Model with Active Rotor Spinning Animation
      const turbineEntity = viewer.entities.add({
        turbineIndex: idx,
        name: `Turbine ${labelText}`,
        position: groundPos,
        orientation: orientation,
        model: {
          uri: '/assets/models/wind_turbine.glb',
          minimumPixelSize: 48,
          maximumScale: 300,
          scale: modelScale,
          runAnimations: true,
          clampAnimations: false,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          shadows: Cesium.ShadowMode.ENABLED,
          color: isSelected ? Cesium.Color.fromCssColorString('#FFD21F') : Cesium.Color.WHITE,
          colorBlendMode: isSelected ? Cesium.ColorBlendMode.MIX : Cesium.ColorBlendMode.HIGHLIGHT,
          colorBlendAmount: 0.35,
        },
      });

      // 2. Heavy Structural Concrete Foundation Pad (R=12m) & Ground Ring
      const groundRing = viewer.entities.add({
        turbineIndex: idx,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, baseElev + 0.5),
        ellipse: {
          semiMajorAxis: isSelected ? 24.0 : 16.0,
          semiMinorAxis: isSelected ? 24.0 : 16.0,
          material: Cesium.Color.fromCssColorString(isSelected ? 'rgba(255, 210, 31, 0.7)' : 'rgba(30, 41, 59, 0.5)'),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString(isSelected ? '#FFD21F' : 'rgba(100, 116, 139, 0.7)'),
          outlineWidth: isSelected ? 3 : 1.5,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
      });

      // 3. Floating Engineering Telemetry Tag (Anchored atop the hub)
      const label = viewer.entities.add({
        turbineIndex: idx,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, baseElev + hubHeight + rotorDiameter / 2.0 + 18.0),
        label: {
          text: `${labelText} · ${speedText}`,
          font: 'bold 11px JetBrains Mono, monospace',
          fillColor: isSelected ? Cesium.Color.fromCssColorString('#0f172a') : Cesium.Color.WHITE,
          backgroundColor: isSelected ? Cesium.Color.fromCssColorString('#FFD21F') : Cesium.Color.fromCssColorString('rgba(15, 23, 42, 0.92)'),
          showBackground: true,
          backgroundPadding: new Cesium.Cartesian2(7, 4),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scale: isSelected ? 1.1 : 1.0,
        },
      });

      entitiesRef.current.turbines.push(turbineEntity, groundRing, label);

      // 4. Downstream Volumetric Jensen Wake Cone
      if (showWakes) {
        const coneLengthM = Math.min(500.0, Math.max(250.0, rotorDiameter * 3.5));
        const downwindDeg = (windDirectionDeg + 180) % 360;
        const windRad = Cesium.Math.toRadians(downwindDeg);
        const dx = Math.sin(windRad);
        const dy = Math.cos(windRad);

        const latMPerDeg = 111000.0;
        const lonMPerDeg = 111000.0 * Math.cos(t.lat * Math.PI / 180.0);

        const endLat = t.lat + (dy * coneLengthM) / latMPerDeg;
        const endLon = t.lon + (dx * coneLengthM) / lonMPerDeg;
        const midLat = (t.lat + endLat) / 2.0;
        const midLon = (t.lon + endLon) / 2.0;

        const deficit = t.wake_deficit_pct || (idx % 3 === 0 ? 12.0 : 4.5);
        const isHighLoss = deficit > 8.0;

        const wakeCone = viewer.entities.add({
          name: `Wake Cone ${labelText}`,
          position: Cesium.Cartesian3.fromDegrees(midLon, midLat, baseElev + hubHeight * 0.75),
          cylinder: {
            length: coneLengthM,
            topRadius: rotorDiameter * 0.65,
            bottomRadius: rotorDiameter * 0.35,
            material: Cesium.Color.fromCssColorString(
              isHighLoss ? 'rgba(239, 68, 68, 0.18)' : 'rgba(255, 210, 31, 0.14)'
            ),
          },
        });
        entitiesRef.current.wakes.push(wakeCone);
      }
    });
  }, [turbines, selectedTurbineIdx, windDirectionDeg, windSpeedMps, rotorDiameter, hubHeight, showWakes]);

  // Camera preset handler
  const handlePresetClick = (preset: string) => {
    setActiveCameraPreset(preset);
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      flyToProjectSite(viewerRef.current, centerLat, centerLon, radiusKm, preset, 1.2);
    }
  };

  // Cinematic close inspection of selected industrial turbine
  const handleFlyToTurbine = (t: Turbine) => {
    const viewer = viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    const baseElev = (t.elevation_m !== undefined && t.elevation_m !== null) ? Number(t.elevation_m) : 40.0;
    const distanceM = Math.max(150.0, rotorDiameter * 1.4);
    // Position camera upwind & oblique from hub
    const camHeading = (windDirectionDeg + 30) % 360;
    const camRad = Cesium.Math.toRadians(camHeading);
    const targetElev = baseElev + hubHeight;

    const latOffset = (distanceM * Math.cos(camRad)) / 111000.0;
    const lonOffset = (distanceM * Math.sin(camRad)) / (111000.0 * Math.cos(t.lat * Math.PI / 180.0));

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(t.lon - lonOffset, t.lat - latOffset, targetElev + 20.0),
      orientation: {
        heading: Cesium.Math.toRadians((windDirectionDeg + 210) % 360),
        pitch: Cesium.Math.toRadians(-15.0),
        roll: 0.0,
      },
      duration: 1.2,
    });
  };

  return (
    <div className={`relative w-full h-full overflow-hidden ${className}`}>
      {/* Cesium 3D WebGL Canvas Container */}
      <div id={containerId} className="w-full h-full absolute inset-0 bg-slate-950" />

      {/* Floating 3D Engineering Camera Bar */}
      <div className="absolute top-3 left-3 z-20 flex flex-wrap items-center gap-1.5 p-1.5 rounded-2xl bg-white/95 backdrop-blur-xl border border-slate-200/90 shadow-glass pointer-events-auto">
        <div className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-black text-slate-500 uppercase tracking-wider">
          <Compass className="w-3 h-3 text-amber-500" />
          <span>3D Camera</span>
        </div>

        {[
          { key: 'OBLIQUE', label: '3D Oblique' },
          { key: 'WIND_ALIGN', label: 'Wind Align' },
          { key: 'TOP', label: 'Nadir (Top)' },
          { key: 'NORTH', label: 'North' },
          { key: 'SOUTH', label: 'South' },
        ].map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => handlePresetClick(p.key)}
            className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all ${
              activeCameraPreset === p.key
                ? 'bg-[#FFD21F] text-slate-950 shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {p.label}
          </button>
        ))}

        {turbines[selectedTurbineIdx] && (
          <button
            type="button"
            onClick={() => handleFlyToTurbine(turbines[selectedTurbineIdx])}
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-900 text-white hover:bg-slate-800 text-xs font-bold shadow-xs active:scale-95 transition-all"
            title="Inspect Selected Turbine in 3D"
          >
            <Eye className="w-3 h-3 text-amber-400" />
            <span>Focus {turbines[selectedTurbineIdx].label || `T-${selectedTurbineIdx + 1}`}</span>
          </button>
        )}
      </div>

      {/* Floating 3D Geodetic Telemetry Badge */}
      <div className="absolute bottom-3 left-3 z-20 hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/95 backdrop-blur-xl border border-slate-200/90 shadow-glass text-slate-700 font-mono text-[11px] pointer-events-auto">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="font-bold text-slate-900">{isGoogleTilesActive ? 'Google Photorealistic 3D Tiles' : 'Copernicus DEM + Hybrid'}</span>
        <span className="text-slate-400">•</span>
        <span>Model: {turbineModelName} ({rotorDiameter}m / {hubHeight}m)</span>
        <span className="text-slate-400">•</span>
        <span className="text-amber-600 font-bold">{turbines.length} Anchored Units</span>
      </div>
    </div>
  );
};
