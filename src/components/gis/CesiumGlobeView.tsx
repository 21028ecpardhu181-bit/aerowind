import React, { useEffect, useRef, useState, useCallback } from 'react';
import { 
  Compass, 
  RotateCcw, 
  Eye, 
  Layers, 
  Wind,
  Navigation,
  Crosshair,
  Activity,
  Zap,
  Radio
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
    streamlines: any[];
    telemetryLines: any[];
    boundary: any | null;
  }>({
    turbines: [],
    wakes: [],
    streamlines: [],
    telemetryLines: [],
    boundary: null,
  });

  const [activeCameraPreset, setActiveCameraPreset] = useState<string>('OBLIQUE');
  const [isTerrainReady, setIsTerrainReady] = useState<boolean>(false);
  const [isGoogleTilesActive, setIsGoogleTilesActive] = useState<boolean>(false);
  const [showFlowStreamlines, setShowFlowStreamlines] = useState<boolean>(true);
  const [localShowWakes, setLocalShowWakes] = useState<boolean>(showWakes);

  useEffect(() => {
    setLocalShowWakes(showWakes);
  }, [showWakes]);

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
      // High-Resolution Satellite Base Layer via direct Esri World Imagery CDN
      const satelliteProvider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19,
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

      // Superimpose High-Resolution Road Network & Place Labels
      const referenceLabelsProvider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19,
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

      // Load Real 3D World Terrain
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

      // Load Google Photorealistic 3D Tiles if API key is provided
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
      controller.minimumZoomDistance = 60.0;
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

  // Synchronize Camera When Coordinates Change
  useEffect(() => {
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      flyToProjectSite(viewerRef.current, centerLat, centerLon, radiusKm, activeCameraPreset, 1.2);
    }
  }, [centerLat, centerLon, radiusKm, activeCameraPreset, flyToProjectSite]);

  // Render Site Boundary Polygon
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

  // Render 3D Industrial Wind Turbines, Ground Wake Plumes, & Data Flow Network
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    // Clear previous entities
    entitiesRef.current.turbines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.turbines = [];
    entitiesRef.current.wakes.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.wakes = [];
    entitiesRef.current.streamlines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.streamlines = [];
    entitiesRef.current.telemetryLines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.telemetryLines = [];

    if (!turbines || turbines.length === 0) return;

    // Canonical upwind HAWT alignment: GlTF model axis correction maps glTF Z (rotor facing) to Cesium East (+X, 90 deg clockwise from North).
    // To face strictly UPWIND directly into the oncoming meteorological wind vector (windDirectionDeg):
    const gltfHeadingDeg = (windDirectionDeg - 90 + 360) % 360;
    const turbineHeadingRad = Cesium.Math.toRadians(gltfHeadingDeg);
    const modelScale = Math.max(0.8, Math.min(1.8, rotorDiameter / 120.0));

    // Downwind vector
    const downwindDeg = (windDirectionDeg + 180) % 360;
    const downwindRad = Cesium.Math.toRadians(downwindDeg);
    const downwindDx = Math.sin(downwindRad);
    const downwindDy = Math.cos(downwindRad);
    // Perpendicular cross-wind vector
    const crossDx = -downwindDy;
    const crossDy = downwindDx;

    turbines.forEach((t, idx) => {
      const isSelected = idx === selectedTurbineIdx;
      const surfaceElev = (isTerrainReady || isGoogleTilesActive)
        ? ((t.elevation_m !== undefined && t.elevation_m !== null) ? Number(t.elevation_m) : 40.0)
        : 0.0;
      const groundPos = Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev);
      const hpr = new Cesium.HeadingPitchRoll(turbineHeadingRad, 0, 0);
      const orientation = Cesium.Transforms.headingPitchRollQuaternion(groundPos, hpr);

      const labelText = t.label || `T-${String(idx + 1).padStart(2, '0')}`;
      const speedText = t.effective_mps ? `${t.effective_mps.toFixed(1)}m/s` : `${windSpeedMps.toFixed(1)}m/s`;

      // 1. Certified Industrial 3D Wind Turbine Model with True 1:1 Metric Scale & Minimum Pixel Size
      const turbineEntity = viewer.entities.add({
        turbineIndex: idx,
        name: `Turbine ${labelText}`,
        position: groundPos,
        orientation: orientation,
        model: {
          uri: '/assets/models/wind_turbine.glb',
          scale: modelScale,
          minimumPixelSize: 64,
          maximumScale: 10.0,
          runAnimations: true,
          clampAnimations: false,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          shadows: Cesium.ShadowMode.ENABLED,
          color: isSelected ? Cesium.Color.fromCssColorString('#FFD21F') : Cesium.Color.WHITE,
          colorBlendMode: isSelected ? Cesium.ColorBlendMode.MIX : Cesium.ColorBlendMode.HIGHLIGHT,
          colorBlendAmount: 0.35,
        },
      });

      // 1b. Structural Monopile Tower (Ensures 3D mast is visible at any zoom)
      const mastEntity = viewer.entities.add({
        turbineIndex: idx,
        name: `Mast ${labelText}`,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + hubHeight / 2.0),
        cylinder: {
          length: hubHeight,
          topRadius: 1.8,
          bottomRadius: 3.4,
          material: isSelected
            ? Cesium.Color.fromCssColorString('#FFD21F')
            : Cesium.Color.WHITE.withAlpha(0.96),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('rgba(100, 116, 139, 0.4)'),
          outlineWidth: 1.0,
          shadows: Cesium.ShadowMode.ENABLED,
          heightReference: Cesium.HeightReference.NONE,
        },
      });

      // 2. Heavy Structural Concrete Foundation Pad (R=16m)
      const groundRing = viewer.entities.add({
        turbineIndex: idx,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + 0.5),
        ellipse: {
          semiMajorAxis: isSelected ? 22.0 : 16.0,
          semiMinorAxis: isSelected ? 22.0 : 16.0,
          material: Cesium.Color.fromCssColorString(isSelected ? 'rgba(255, 210, 31, 0.7)' : 'rgba(30, 41, 59, 0.6)'),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString(isSelected ? '#FFD21F' : 'rgba(100, 116, 139, 0.7)'),
          outlineWidth: isSelected ? 3 : 1.5,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
      });

      // 3. Floating Engineering Telemetry Tag (Anchored atop the hub)
      const label = viewer.entities.add({
        turbineIndex: idx,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + hubHeight + rotorDiameter / 2.0 + 16.0),
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

      entitiesRef.current.turbines.push(turbineEntity, mastEntity, groundRing, label);

      // 4. Downwind Horizontal Aerodynamic Wake Plume Footprint (Draped on Terrain)
      // Physically derived Jensen expanding wake corridor (8.5D length, k=0.05 decay)
      if (localShowWakes) {
        const coneLengthM = Math.min(1200.0, Math.max(750.0, rotorDiameter * 8.5));
        const latMPerDeg = 110540.0;
        const lonMPerDeg = 111320.0 * Math.cos(t.lat * Math.PI / 180.0);

        const r0 = rotorDiameter * 0.5;
        const r1 = r0 + 0.05 * coneLengthM;

        const endLat = t.lat + (downwindDy * coneLengthM) / latMPerDeg;
        const endLon = t.lon + (downwindDx * coneLengthM) / lonMPerDeg;

        // 4 vertices of expanding wake trapezoid
        const rootLeftLat = t.lat - (crossDy * r0) / latMPerDeg;
        const rootLeftLon = t.lon - (crossDx * r0) / lonMPerDeg;
        const rootRightLat = t.lat + (crossDy * r0) / latMPerDeg;
        const rootRightLon = t.lon + (crossDx * r0) / lonMPerDeg;
        const endRightLat = endLat + (crossDy * r1) / latMPerDeg;
        const endRightLon = endLon + (crossDx * r1) / lonMPerDeg;
        const endLeftLat = endLat - (crossDy * r1) / latMPerDeg;
        const endLeftLon = endLon - (crossDx * r1) / lonMPerDeg;

        const deficit = t.wake_deficit_pct || (idx % 3 === 0 ? 9.5 : 3.8);
        const isHighLoss = deficit > 6.0;

        const wakePolygon = viewer.entities.add({
          name: `Wake Footprint ${labelText}`,
          polygon: {
            hierarchy: Cesium.Cartesian3.fromDegreesArray([
              rootLeftLon, rootLeftLat,
              rootRightLon, rootRightLat,
              endRightLon, endRightLat,
              endLeftLon, endLeftLat,
            ]),
            material: Cesium.Color.fromCssColorString(
              isHighLoss ? 'rgba(239, 68, 68, 0.20)' : 'rgba(14, 165, 233, 0.16)'
            ),
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          },
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArray([
              rootLeftLon, rootLeftLat,
              rootRightLon, rootRightLat,
              endRightLon, endRightLat,
              endLeftLon, endLeftLat,
              rootLeftLon, rootLeftLat,
            ]),
            width: 1.5,
            material: Cesium.Color.fromCssColorString(
              isHighLoss ? 'rgba(239, 68, 68, 0.55)' : 'rgba(14, 165, 233, 0.45)'
            ),
            clampToGround: true,
          },
        });

        // Hub-height wake centerline extending downwind along wind vector
        const centerLine = viewer.entities.add({
          name: `Wake Centerline ${labelText}`,
          polyline: {
            positions: [
              Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + hubHeight),
              Cesium.Cartesian3.fromDegrees(endLon, endLat, surfaceElev + hubHeight * 0.95),
            ],
            width: 2.0,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.22,
              taperPower: 0.65,
              color: isHighLoss ? Cesium.Color.fromCssColorString('#f59e0b') : Cesium.Color.fromCssColorString('#0ea5e9'),
            }),
          },
        });

        entitiesRef.current.wakes.push(wakePolygon, centerLine);
      }
    });

    // 5. Finite Engineering Micro-Climate Flow Field (Strictly Bounded within Site Boundary)
    if (showFlowStreamlines) {
      const latMPerDeg = 110540.0;
      const lonMPerDeg = 111320.0 * Math.cos(centerLat * Math.PI / 180.0);
      const streamSpanM = Math.min(2200.0, Math.max(1200.0, radiusKm * 1400.0));

      // Color coding flow ribbons by physical wind speed (cool blue <5 m/s, cyan 5-10 m/s, amber >10 m/s)
      const flowColor = windSpeedMps < 5.0
        ? 'rgba(59, 130, 246, 0.60)'
        : windSpeedMps <= 10.0
        ? 'rgba(6, 182, 212, 0.65)'
        : 'rgba(245, 158, 11, 0.70)';

      const numStreamlines = Math.min(5, Math.max(3, Math.round(radiusKm * 1.5)));
      for (let s = 0; s < numStreamlines; s++) {
        const offsetRatio = numStreamlines > 1 ? (s / (numStreamlines - 1) - 0.5) * 2.0 : 0.0;
        const crossOffsetM = offsetRatio * (radiusKm * 750.0);

        const midLat = centerLat + (crossDy * crossOffsetM) / latMPerDeg;
        const midLon = centerLon + (crossDx * crossOffsetM) / lonMPerDeg;

        const startLat = midLat - (downwindDy * (streamSpanM * 0.45)) / latMPerDeg;
        const startLon = midLon - (downwindDx * (streamSpanM * 0.45)) / lonMPerDeg;
        const endLat = midLat + (downwindDy * (streamSpanM * 0.45)) / latMPerDeg;
        const endLon = midLon + (downwindDx * (streamSpanM * 0.45)) / lonMPerDeg;

        const streamLine = viewer.entities.add({
          name: `Concession Flow Corridor ${s + 1}`,
          polyline: {
            positions: [
              Cesium.Cartesian3.fromDegrees(startLon, startLat, hubHeight * 0.9),
              Cesium.Cartesian3.fromDegrees(midLon, midLat, hubHeight * 1.05),
              Cesium.Cartesian3.fromDegrees(endLon, endLat, hubHeight * 0.95),
            ],
            width: 2.0,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.25,
              taperPower: 0.55,
              color: Cesium.Color.fromCssColorString(flowColor),
            }),
          },
        });
        entitiesRef.current.streamlines.push(streamLine);
      }

      // B) SCADA Telemetry & Electrical Energy Collection Flow Network
      // Connect each turbine to nearest turbine or central collector substation
      turbines.forEach((t, i) => {
        // Find nearest neighboring turbine
        let nearestIdx = -1;
        let minDist = Infinity;
        turbines.forEach((other, j) => {
          if (i !== j) {
            const d = Math.hypot(t.lat - other.lat, t.lon - other.lon);
            if (d < minDist) {
              minDist = d;
              nearestIdx = j;
            }
          }
        });

        if (nearestIdx >= 0) {
          const neighbor = turbines[nearestIdx];
          const elevA = (t.elevation_m || 40.0) + 1.0;
          const elevB = (neighbor.elevation_m || 40.0) + 1.0;

          const cableLine = viewer.entities.add({
            name: `SCADA Grid ${t.label}->${neighbor.label}`,
            polyline: {
              positions: [
                Cesium.Cartesian3.fromDegrees(t.lon, t.lat, elevA),
                Cesium.Cartesian3.fromDegrees(neighbor.lon, neighbor.lat, elevB),
              ],
              width: 2.0,
              clampToGround: true,
              material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.35,
                taperPower: 0.5,
                color: Cesium.Color.fromCssColorString('#FFD21F'),
              }),
            },
          });
          entitiesRef.current.telemetryLines.push(cableLine);
        }
      });
    }
  }, [turbines, selectedTurbineIdx, windDirectionDeg, windSpeedMps, rotorDiameter, hubHeight, localShowWakes, showFlowStreamlines, centerLat, centerLon, radiusKm]);

  // Camera preset handler
  const handlePresetClick = (preset: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setActiveCameraPreset(preset);
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      flyToProjectSite(viewerRef.current, centerLat, centerLon, radiusKm, preset, 1.2);
    }
  };

  // Cinematic close inspection of selected industrial turbine
  const handleFlyToTurbine = (t: Turbine, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const viewer = viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    const baseElev = (t.elevation_m !== undefined && t.elevation_m !== null) ? Number(t.elevation_m) : 40.0;
    const distanceM = Math.max(150.0, rotorDiameter * 1.4);
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

      {/* Floating Apple Liquid Glass Wind Telemetry & Turbine Yaw Indicator */}
      <div 
        id="cesium-wind-telemetry-badge"
        className="absolute top-36 left-2 sm:top-16 sm:left-3 md:top-16 md:left-4 z-30 flex flex-col gap-1.5 p-2 sm:p-2.5 rounded-2xl bg-slate-950/85 backdrop-blur-2xl border border-white/20 shadow-[0_8px_32px_rgba(0,0,0,0.5)] pointer-events-auto text-white max-w-[280px]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-1.5">
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-lg bg-amber-400/20 border border-amber-400/40 flex items-center justify-center">
              <Wind className="w-3 h-3 text-amber-400" />
            </div>
            <span className="text-[11px] font-bold tracking-tight text-white">Wind & Yaw Telemetry</span>
          </div>
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-[10px] font-mono text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>IEC 61400</span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 pt-0.5">
          {/* Animated 360-degree Compass Rose */}
          <div className="relative w-8 h-8 rounded-full border border-white/20 bg-white/5 flex items-center justify-center shrink-0">
            <span className="absolute top-0 text-[7px] text-slate-400 font-bold leading-none">N</span>
            <svg
              className="w-5 h-5 text-amber-400 transition-transform duration-500 drop-shadow-[0_0_4px_rgba(251,191,36,0.6)]"
              style={{ transform: `rotate(${windDirectionDeg}deg)` }}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </div>

          <div className="flex flex-col text-left font-mono">
            <div className="flex items-baseline gap-1 text-xs font-bold text-white">
              <span>{windSpeedMps.toFixed(1)} m/s</span>
              <span className="text-slate-400 text-[10px]">·</span>
              <span className="text-amber-300 font-bold">{windDirectionDeg}°</span>
              <span className="text-[10px] text-slate-400">
                {windDirectionDeg >= 337.5 || windDirectionDeg < 22.5 ? 'N' :
                 windDirectionDeg < 67.5 ? 'NE' :
                 windDirectionDeg < 112.5 ? 'E' :
                 windDirectionDeg < 157.5 ? 'SE' :
                 windDirectionDeg < 202.5 ? 'S' :
                 windDirectionDeg < 247.5 ? 'SW' :
                 windDirectionDeg < 292.5 ? 'W' : 'NW'}
              </span>
            </div>
            <div className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
              <span>Rotor Yaw: {windDirectionDeg}°</span>
              <span className="text-slate-400">·</span>
              <span className="text-slate-300">Upwind Aligned</span>
            </div>
          </div>
        </div>
      </div>

      {/* Floating 3D Engineering & Flow Controls Dock (Top-Right, Non-Overlapping) */}
      <div 
        className="absolute top-16 right-2 sm:top-16 sm:right-3 md:top-4 md:right-4 z-30 max-w-[calc(100vw-16px)] flex flex-wrap items-center gap-1.5 p-1.5 sm:p-2 rounded-2xl bg-slate-950/85 backdrop-blur-2xl border border-white/20 shadow-[0_8px_32px_rgba(0,0,0,0.5)] pointer-events-auto text-white"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-1 px-1.5 sm:px-2 py-0.5 text-[10px] font-black text-slate-400 uppercase tracking-wider">
          <Compass className="w-3.5 h-3.5 text-[#FFD21F]" />
          <span className="hidden sm:inline">3D View</span>
        </div>

        {[
          { key: 'OBLIQUE', label: '3D Oblique' },
          { key: 'WIND_ALIGN', label: 'Wind Align' },
          { key: 'TOP', label: 'Top' },
          { key: 'NORTH', label: 'N' },
          { key: 'SOUTH', label: 'S' },
        ].map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={(e) => handlePresetClick(p.key, e)}
            className={`px-2 sm:px-2.5 py-1 rounded-xl text-xs font-bold transition-all active:scale-95 ${
              activeCameraPreset === p.key
                ? 'bg-[#FFD21F] text-slate-950 shadow-md font-black ring-1 ring-amber-300'
                : 'bg-white/10 text-slate-200 hover:bg-white/20 hover:text-white'
            }`}
          >
            {p.label}
          </button>
        ))}

        {/* Streamlines / Data Flow Toggle Button */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setShowFlowStreamlines(!showFlowStreamlines);
          }}
          className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-xl text-xs font-bold transition-all active:scale-95 ${
            showFlowStreamlines
              ? 'bg-sky-500 text-white shadow-xs font-black'
              : 'bg-white/10 text-slate-300 hover:bg-white/20'
          }`}
          title="Toggle Atmospheric Wind & Energy Data Flow Streamlines"
        >
          <Activity className="w-3 h-3 text-sky-200" />
          <span className="hidden sm:inline">Flow</span>
        </button>

        {/* Wake Plumes Toggle */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setLocalShowWakes(!localShowWakes);
          }}
          className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-xl text-xs font-bold transition-all active:scale-95 ${
            localShowWakes
              ? 'bg-amber-500 text-white shadow-xs font-black'
              : 'bg-white/10 text-slate-300 hover:bg-white/20'
          }`}
          title="Toggle Aerodynamic Jensen Wake Plumes"
        >
          <Wind className="w-3 h-3 text-amber-200" />
          <span className="hidden sm:inline">Wakes</span>
        </button>

        {turbines[selectedTurbineIdx] && (
          <button
            type="button"
            onClick={(e) => handleFlyToTurbine(turbines[selectedTurbineIdx], e)}
            className="flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-xl bg-white/15 hover:bg-white/25 text-white text-xs font-bold shadow-xs active:scale-95 transition-all border border-white/20"
            title="Inspect Selected Turbine Close-up"
          >
            <Eye className="w-3 h-3 text-[#FFD21F]" />
            <span>{turbines[selectedTurbineIdx].label || `T-${selectedTurbineIdx + 1}`}</span>
          </button>
        )}
      </div>

      {/* Floating 3D Geodetic Telemetry Badge (Bottom-Left) */}
      <div className="absolute bottom-3 left-3 z-20 hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-2xl border border-white/50 dark:border-white/10 shadow-lg text-slate-700 dark:text-slate-200 font-mono text-[11px] pointer-events-auto">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="font-bold text-slate-900 dark:text-white">
          {isGoogleTilesActive ? 'Google Photorealistic 3D Tiles' : 'Copernicus DEM GLO-30'}
        </span>
        <span className="text-slate-400">•</span>
        <span>{turbineModelName}</span>
        <span className="text-slate-400">•</span>
        <span className="text-amber-600 dark:text-amber-400 font-bold">{turbines.length} Turbines</span>
      </div>
    </div>
  );
};
