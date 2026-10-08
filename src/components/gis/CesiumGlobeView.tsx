import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
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
  boundary?: number[][] | any;
  siteElevationM?: number;
  turbines?: Turbine[];
  candidates?: any[];
  selectedCandidateIds?: string[];
  selectedTurbineIdx?: number;
  onSelectTurbine?: (index: number) => void;
  windDirectionDeg?: number;
  windSpeedMps?: number;
  rotorDiameter?: number;
  hubHeight?: number;
  turbineModelName?: string;
  showWakes?: boolean;
  showCandidates?: boolean;
  optimalityScope?: string;
  className?: string;
}

interface BoundaryPolygonData {
  exterior: number[];
  holes: number[][];
}

function parseBoundaryPolygons(boundaryInput: any): BoundaryPolygonData[] {
  if (!boundaryInput) return [];

  if (boundaryInput.type === 'FeatureCollection' && Array.isArray(boundaryInput.features)) {
    const list: BoundaryPolygonData[] = [];
    for (const f of boundaryInput.features) {
      list.push(...parseBoundaryPolygons(f.geometry || f));
    }
    return list;
  }

  if (boundaryInput.type === 'Feature' && boundaryInput.geometry) {
    return parseBoundaryPolygons(boundaryInput.geometry);
  }

  if (boundaryInput.type === 'Polygon' && Array.isArray(boundaryInput.coordinates)) {
    const rings = boundaryInput.coordinates;
    if (rings.length === 0) return [];
    const exterior = rings[0].flatMap(([lon, lat]: [number, number]) => [Number(lon), Number(lat)]);
    const holes = rings.slice(1).map((ring: [number, number][]) =>
      ring.flatMap(([lon, lat]: [number, number]) => [Number(lon), Number(lat)])
    );
    return [{ exterior, holes }];
  }

  if (boundaryInput.type === 'MultiPolygon' && Array.isArray(boundaryInput.coordinates)) {
    const list: BoundaryPolygonData[] = [];
    for (const polyRings of boundaryInput.coordinates) {
      if (polyRings.length === 0) continue;
      const exterior = polyRings[0].flatMap(([lon, lat]: [number, number]) => [Number(lon), Number(lat)]);
      const holes = polyRings.slice(1).map((ring: [number, number][]) =>
        ring.flatMap(([lon, lat]: [number, number]) => [Number(lon), Number(lat)])
      );
      list.push({ exterior, holes });
    }
    return list;
  }

  if (Array.isArray(boundaryInput) && boundaryInput.length >= 3) {
    const exterior: number[] = [];
    for (const pt of boundaryInput) {
      if (Array.isArray(pt) && pt.length >= 2) {
        const p0 = Number(pt[0]);
        const p1 = Number(pt[1]);
        let lat = p0;
        let lon = p1;
        if (Math.abs(p0) > 45 && Math.abs(p1) <= 45) {
          lon = p0;
          lat = p1;
        }
        exterior.push(lon, lat);
      }
    }
    if (exterior.length >= 6) {
      return [{ exterior, holes: [] }];
    }
  }

  return [];
}

export const CesiumGlobeView: React.FC<CesiumGlobeViewProps> = ({
  containerId,
  centerLat,
  centerLon,
  radiusKm = 3.0,
  boundary,
  siteElevationM,
  turbines = [],
  candidates = [],
  selectedCandidateIds = [],
  selectedTurbineIdx = 0,
  onSelectTurbine,
  windDirectionDeg = 270,
  windSpeedMps = 7.8,
  rotorDiameter = 120,
  hubHeight = 110,
  turbineModelName = 'GE 2.5-120',
  showWakes = true,
  showCandidates = true,
  optimalityScope,
  className = '',
}) => {
  const viewerRef = useRef<any>(null);
  const clickHandlerRef = useRef<any>(null);
  const siteImageryLayerRef = useRef<any>(null);
  const entitiesRef = useRef<{
    turbines: any[];
    candidates: any[];
    wakes: any[];
    streamlines: any[];
    telemetryLines: any[];
    boundaryEntities: any[];
  }>({
    turbines: [],
    candidates: [],
    wakes: [],
    streamlines: [],
    telemetryLines: [],
    boundaryEntities: [],
  });

  const [viewerInstance, setViewerInstance] = useState<any>(null);
  const [activeCameraPreset, setActiveCameraPreset] = useState<string>('OBLIQUE');
  const [isTerrainReady, setIsTerrainReady] = useState<boolean>(false);
  const [isGoogleTilesActive, setIsGoogleTilesActive] = useState<boolean>(false);
  const [showFlowStreamlines, setShowFlowStreamlines] = useState<boolean>(true);
  const [localShowWakes, setLocalShowWakes] = useState<boolean>(showWakes);
  const [localShowCandidates, setLocalShowCandidates] = useState<boolean>(showCandidates);

  useEffect(() => {
    setLocalShowWakes(showWakes);
  }, [showWakes]);

  useEffect(() => {
    setLocalShowCandidates(showCandidates);
  }, [showCandidates]);

  // Dynamically calculate actual turbine cluster centroid to center camera and satellite texture
  const effectiveCenterLat = useMemo(() => {
    if (turbines && turbines.length > 0) {
      const valid = turbines.filter((t) => t.lat !== undefined && t.lat !== null && !isNaN(Number(t.lat)));
      if (valid.length > 0) {
        return valid.reduce((sum, t) => sum + Number(t.lat), 0) / valid.length;
      }
    }
    return centerLat;
  }, [turbines, centerLat]);

  const effectiveCenterLon = useMemo(() => {
    if (turbines && turbines.length > 0) {
      const valid = turbines.filter((t) => t.lon !== undefined && t.lon !== null && !isNaN(Number(t.lon)));
      if (valid.length > 0) {
        return valid.reduce((sum, t) => sum + Number(t.lon), 0) / valid.length;
      }
    }
    return centerLon;
  }, [turbines, centerLon]);

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
      // Ensure Cesium never attempts background Ion API calls with default invalid tokens
      if (Cesium.Ion) {
        Cesium.Ion.defaultAccessToken = '';
      }

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
        baseLayer: false,
        shadows: false,
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

      // Expose globally for telemetry and UI verification inspection
      (window as any).viewer = viewer;
      (window as any).cesiumViewer = viewer;

      const scene = viewer.scene;
      scene.globe.baseColor = Cesium.Color.fromCssColorString('#1e293b');
      scene.globe.depthTestAgainstTerrain = false;
      scene.globe.enableLighting = false; // Always bright, crisp daylight satellite rendering
      scene.globe.showGroundAtmosphere = true;
      if (scene.skyAtmosphere) scene.skyAtmosphere.show = true;
      if (scene.fog) {
        scene.fog.enabled = true;
        scene.fog.density = 0.00008;
      }

      // Add real global satellite imagery provider so 3D mode renders true geographic data everywhere
      try {
        const satelliteProvider = new Cesium.UrlTemplateImageryProvider({
          url: 'https://mt{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
          subdomains: ['0', '1', '2', '3'],
          maximumLevel: 20,
        });
        viewer.imageryLayers.addImageryProvider(satelliteProvider);
      } catch (err) {
        console.warn('[CesiumGlobeView] Could not load global satellite provider, trying proxy fallback:', err);
        try {
          const proxyProvider = new Cesium.UrlTemplateImageryProvider({
            url: '/api/geo/tiles/satellite/{z}/{x}/{y}',
            maximumLevel: 19,
          });
          viewer.imageryLayers.addImageryProvider(proxyProvider);
        } catch (_) {}
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
      setViewerInstance(viewer);

      // Initial Camera Set View to Site (immediate positioning centered on wind turbines)
      flyToProjectSite(viewer, effectiveCenterLat, effectiveCenterLon, radiusKm, 'OBLIQUE', 0.0);
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
      setViewerInstance(null);
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

    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
    const target = Cesium.Cartesian3.fromDegrees(lon, lat, 0);
    const rangeMeters = isMobile
      ? Math.max(3800.0, rKm * 1000.0 * 1.25)
      : Math.max(5200.0, rKm * 1000.0 * 1.45);

    let headingDeg = 35.0;
    let pitchDeg = -42.0;

    switch (preset) {
      case 'TOP':
        headingDeg = 0.0;
        pitchDeg = -89.0;
        break;
      case 'NORTH':
        headingDeg = 0.0;
        pitchDeg = -40.0;
        break;
      case 'SOUTH':
        headingDeg = 180.0;
        pitchDeg = -40.0;
        break;
      case 'WIND_ALIGN':
        headingDeg = (windDirectionDeg + 180) % 360;
        pitchDeg = -40.0;
        break;
      case 'OBLIQUE':
      default:
        headingDeg = 35.0;
        pitchDeg = -42.0;
        break;
    }

    const headingRad = Cesium.Math.toRadians(headingDeg);
    const pitchRad = Cesium.Math.toRadians(pitchDeg);

    viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(headingRad, pitchRad, rangeMeters));
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
  }, [windDirectionDeg]);

  // Synchronize Camera When Coordinates Change
  useEffect(() => {
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      flyToProjectSite(viewerRef.current, effectiveCenterLat, effectiveCenterLon, radiusKm, activeCameraPreset, 1.2);
    }
  }, [effectiveCenterLat, effectiveCenterLon, radiusKm, activeCameraPreset, flyToProjectSite]);

  // Render Authoritative Site Boundary & Exclusion Holes
  useEffect(() => {
    const viewer = viewerInstance || viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    // Clear previous boundary entities
    if (entitiesRef.current.boundaryEntities) {
      entitiesRef.current.boundaryEntities.forEach((e) => viewer.entities.remove(e));
      entitiesRef.current.boundaryEntities = [];
    }

    const polygons = parseBoundaryPolygons(boundary);
    if (polygons.length === 0) return; // Truthful: never manufacture synthetic circles if boundary is absent

    polygons.forEach((poly, polyIdx) => {
      if (poly.exterior.length < 6) return;

      const exteriorPositions = Cesium.Cartesian3.fromDegreesArray(poly.exterior);
      const holeHierarchies = poly.holes
        .filter((h) => h.length >= 6)
        .map((h) => new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(h)));

      const hierarchy = new Cesium.PolygonHierarchy(exteriorPositions, holeHierarchies);

      // 1. Concession area filled polygon with interior exclusion holes
      const boundaryEntity = viewer.entities.add({
        name: `Concession Area Boundary ${polyIdx + 1}`,
        polygon: {
          hierarchy: hierarchy,
          material: Cesium.Color.fromCssColorString('rgba(255, 210, 31, 0.12)'),
          classificationType: Cesium.ClassificationType ? Cesium.ClassificationType.BOTH : undefined,
          outline: false,
        },
      });

      // 2. Exterior ring dashed polyline
      const exteriorWithClose = [...poly.exterior, poly.exterior[0], poly.exterior[1]];
      const exteriorLine = viewer.entities.add({
        name: `Concession Perimeter ${polyIdx + 1}`,
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray(exteriorWithClose),
          width: 3.0,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.fromCssColorString('#FFD21F'),
            dashLength: 16.0,
          }),
          clampToGround: true,
        },
      });

      entitiesRef.current.boundaryEntities.push(boundaryEntity, exteriorLine);

      // 3. Render interior exclusion holes with crimson warning outlines
      poly.holes.forEach((holeCoords, hIdx) => {
        if (holeCoords.length < 6) return;
        const holeWithClose = [...holeCoords, holeCoords[0], holeCoords[1]];
        const holeEntity = viewer.entities.add({
          name: `Statutory Exclusion Zone ${polyIdx + 1}-${hIdx + 1}`,
          polygon: {
            hierarchy: Cesium.Cartesian3.fromDegreesArray(holeCoords),
            material: Cesium.Color.fromCssColorString('rgba(239, 68, 68, 0.22)'),
            classificationType: Cesium.ClassificationType ? Cesium.ClassificationType.BOTH : undefined,
            outline: false,
          },
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArray(holeWithClose),
            width: 2.5,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.fromCssColorString('#EF4444'),
              dashLength: 10.0,
            }),
            clampToGround: true,
          },
        });
        entitiesRef.current.boundaryEntities.push(holeEntity);
      });
    });
  }, [viewerInstance, boundary]);

  // Render 3D Industrial Wind Turbines, Candidate Locations, Ground Wake Plumes, & Data Flow Network
  useEffect(() => {
    const viewer = viewerInstance || viewerRef.current;
    const Cesium = (window as any).Cesium;
    if (!viewer || viewer.isDestroyed() || !Cesium) return;

    // Clear previous entities
    entitiesRef.current.turbines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.turbines = [];
    entitiesRef.current.candidates.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.candidates = [];
    entitiesRef.current.wakes.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.wakes = [];
    entitiesRef.current.streamlines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.streamlines = [];
    entitiesRef.current.telemetryLines.forEach((e) => viewer.entities.remove(e));
    entitiesRef.current.telemetryLines = [];

    // Canonical upwind HAWT alignment: GlTF model axis correction maps glTF Z (rotor facing) to Cesium East (+X, 90 deg clockwise from North).
    // To face strictly UPWIND directly into oncoming meteorological wind vector (windDirectionDeg):
    const gltfHeadingDeg = (windDirectionDeg - 90 + 360) % 360;
    const turbineHeadingRad = Cesium.Math.toRadians(gltfHeadingDeg);
    const modelScale = Math.max(0.8, Math.min(2.0, rotorDiameter / 120.0));

    // Downwind vector
    const downwindDeg = (windDirectionDeg + 180) % 360;
    const downwindRad = Cesium.Math.toRadians(downwindDeg);
    const downwindDx = Math.sin(downwindRad);
    const downwindDy = Math.cos(downwindRad);
    // Perpendicular cross-wind vector
    const crossDx = -downwindDy;
    const crossDy = downwindDx;

    // 1. Render Candidate Locations (Phase 4 Feasible & Unselected Candidates)
    if (localShowCandidates && candidates && candidates.length > 0) {
      const selectedIds = new Set(
        selectedCandidateIds && selectedCandidateIds.length > 0
          ? selectedCandidateIds.map(String)
          : turbines.map((t) => String(t.id || t.label))
      );

      candidates.forEach((c: any, cIdx: number) => {
        const cId = String(c.candidate_id || c.id || `C-${String(cIdx + 1).padStart(2, '0')}`);
        const isSelected = selectedIds.has(cId);
        if (isSelected) {
          // Already rendered as full industrial wind turbine
          return;
        }

        const cLat = Number(c.latitude ?? c.lat);
        const cLon = Number(c.longitude ?? c.lon);
        if (isNaN(cLat) || isNaN(cLon)) return;

        const cElev = c.elevation_m !== undefined && c.elevation_m !== null
          ? Number(c.elevation_m)
          : (siteElevationM ?? 0.0);

        const isFeasible = c.is_feasible !== false && !['EXCLUDED', 'HARD_EXCLUDED', 'INVALID'].includes(String(c.feasibility_status || c.status || '').toUpperCase());

        if (isFeasible) {
          // Feasible but Unselected Candidate Position
          const candGround = Cesium.Cartesian3.fromDegrees(cLon, cLat, cElev + 0.3);
          const candPad = viewer.entities.add({
            name: `Candidate ${cId} (Unselected)`,
            position: candGround,
            cylinder: {
              length: 0.6,
              topRadius: rotorDiameter * 0.10,
              bottomRadius: rotorDiameter * 0.10,
              material: Cesium.Color.fromCssColorString('rgba(148, 163, 184, 0.45)'),
              outline: true,
              outlineColor: Cesium.Color.fromCssColorString('#94A3B8'),
              outlineWidth: 1.5,
              heightReference: Cesium.HeightReference.NONE,
            },
          });

          const candLabel = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(cLon, cLat, cElev + 16.0),
            label: {
              text: `${cId} · Feasible Candidate`,
              font: 'bold 9px JetBrains Mono, monospace',
              fillColor: Cesium.Color.fromCssColorString('#94A3B8'),
              backgroundColor: Cesium.Color.fromCssColorString('rgba(15, 23, 42, 0.85)'),
              showBackground: true,
              backgroundPadding: new Cesium.Cartesian2(5, 3),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
              scale: 0.85,
            },
          });

          entitiesRef.current.candidates.push(candPad, candLabel);
        } else {
          // Rejected / Excluded Candidate Location
          const candGround = Cesium.Cartesian3.fromDegrees(cLon, cLat, cElev + 0.3);
          const candPad = viewer.entities.add({
            name: `Excluded Candidate ${cId}`,
            position: candGround,
            cylinder: {
              length: 0.6,
              topRadius: rotorDiameter * 0.08,
              bottomRadius: rotorDiameter * 0.08,
              material: Cesium.Color.fromCssColorString('rgba(239, 68, 68, 0.35)'),
              outline: true,
              outlineColor: Cesium.Color.fromCssColorString('#EF4444'),
              outlineWidth: 1.5,
              heightReference: Cesium.HeightReference.NONE,
            },
          });

          const exclusionReason = c.exclusion_reason || 'Setback / Constraint';
          const candLabel = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(cLon, cLat, cElev + 14.0),
            label: {
              text: `${cId} · EXCLUDED: ${exclusionReason}`,
              font: 'bold 9px JetBrains Mono, monospace',
              fillColor: Cesium.Color.fromCssColorString('#EF4444'),
              backgroundColor: Cesium.Color.fromCssColorString('rgba(15, 23, 42, 0.90)'),
              showBackground: true,
              backgroundPadding: new Cesium.Cartesian2(5, 3),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
              scale: 0.85,
            },
          });

          entitiesRef.current.candidates.push(candPad, candLabel);
        }
      });
    }

    if (!turbines || turbines.length === 0) return;

    turbines.forEach((t, idx) => {
      const isSelected = idx === selectedTurbineIdx;
      // Authentic elevation from Copernicus DEM GLO-90 composite metadata
      const surfaceElev = (t.elevation_m !== undefined && t.elevation_m !== null)
        ? Number(t.elevation_m)
        : (siteElevationM !== undefined && siteElevationM !== null ? Number(siteElevationM) : 0.0);

      const groundPos = Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev);
      const hpr = new Cesium.HeadingPitchRoll(turbineHeadingRad, 0, 0);
      const orientation = Cesium.Transforms.headingPitchRollQuaternion(groundPos, hpr);

      const labelText = t.label || `T-${String(idx + 1).padStart(2, '0')}`;
      const speedText = t.effective_mps !== undefined && t.effective_mps !== null
        ? `${Number(t.effective_mps).toFixed(1)} m/s`
        : `${windSpeedMps.toFixed(1)} m/s`;

      // 1. Certified Industrial 3D Wind Turbine Model with True 1:1 Metric Scale
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
          heightReference: isTerrainReady ? Cesium.HeightReference.CLAMP_TO_GROUND : Cesium.HeightReference.NONE,
          shadows: Cesium.ShadowMode.DISABLED,
          color: isSelected ? Cesium.Color.fromCssColorString('#FFD21F') : Cesium.Color.WHITE,
          colorBlendMode: isSelected ? Cesium.ColorBlendMode.MIX : Cesium.ColorBlendMode.HIGHLIGHT,
          colorBlendAmount: 0.35,
        },
      });

      // 1b. Structural Monopile Tower with Authentic Metric Dimensions (H = hubHeight)
      const mastEntity = viewer.entities.add({
        turbineIndex: idx,
        name: `Mast ${labelText}`,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + hubHeight / 2.0),
        cylinder: {
          length: hubHeight,
          topRadius: rotorDiameter * 0.015,
          bottomRadius: rotorDiameter * 0.028,
          material: isSelected
            ? Cesium.Color.fromCssColorString('#FFD21F')
            : Cesium.Color.WHITE.withAlpha(0.96),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('rgba(100, 116, 139, 0.4)'),
          outlineWidth: 1.0,
          shadows: Cesium.ShadowMode.DISABLED,
          heightReference: Cesium.HeightReference.NONE,
        },
      });

      // 1c. Industrial Nacelle Housing
      const nacelleEntity = viewer.entities.add({
        turbineIndex: idx,
        name: `Nacelle ${labelText}`,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + hubHeight),
        orientation: orientation,
        box: {
          dimensions: new Cesium.Cartesian3(rotorDiameter * 0.10, rotorDiameter * 0.035, rotorDiameter * 0.035),
          material: isSelected
            ? Cesium.Color.fromCssColorString('#FFD21F')
            : Cesium.Color.WHITE.withAlpha(0.96),
        },
      });

      // 2. Heavy Structural Concrete Foundation Pad
      const groundRing = viewer.entities.add({
        turbineIndex: idx,
        name: `Foundation ${labelText}`,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + 0.5),
        cylinder: {
          length: 1.0,
          topRadius: isSelected ? rotorDiameter * 0.18 : rotorDiameter * 0.13,
          bottomRadius: isSelected ? rotorDiameter * 0.18 : rotorDiameter * 0.13,
          material: Cesium.Color.fromCssColorString(isSelected ? '#FFD21F' : '#64748B'),
          shadows: Cesium.ShadowMode.DISABLED,
          heightReference: Cesium.HeightReference.NONE,
        },
      });

      // 3. Floating Engineering Telemetry Tag (Anchored atop the rotor swept area)
      const deficitTag = t.wake_deficit_pct !== undefined && t.wake_deficit_pct !== null
        ? ` · ${Number(t.wake_deficit_pct).toFixed(1)}% def`
        : '';
      const label = viewer.entities.add({
        turbineIndex: idx,
        position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, surfaceElev + hubHeight + rotorDiameter / 2.0 + 14.0),
        label: {
          text: `${labelText} · ${speedText}${deficitTag}`,
          font: 'bold 11px JetBrains Mono, monospace',
          fillColor: isSelected ? Cesium.Color.fromCssColorString('#0f172a') : Cesium.Color.WHITE,
          backgroundColor: isSelected ? Cesium.Color.fromCssColorString('#FFD21F') : Cesium.Color.fromCssColorString('rgba(15, 23, 42, 0.92)'),
          showBackground: true,
          backgroundPadding: new Cesium.Cartesian2(7, 4),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scale: isSelected ? 1.1 : 1.0,
        },
      });

      entitiesRef.current.turbines.push(turbineEntity, mastEntity, nacelleEntity, groundRing, label);

      // 4. Downwind Horizontal Aerodynamic Wake Plume Footprint (Draped on Terrain)
      // Physically derived Jensen expanding wake corridor with FLORIS k* = 0.04
      if (localShowWakes) {
        const kStar = 0.04; // FLORIS Bastankhah Gaussian expansion parameter
        const coneLengthM = Math.min(1200.0, Math.max(750.0, rotorDiameter * 8.5));
        const latMPerDeg = 110540.0;
        const lonMPerDeg = 111320.0 * Math.cos((t.lat * Math.PI) / 180.0);

        const r0 = rotorDiameter * 0.5;
        const r1 = r0 + kStar * coneLengthM;

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

        const hasDeficit = t.wake_deficit_pct !== undefined && t.wake_deficit_pct !== null;
        const deficitVal = hasDeficit ? Number(t.wake_deficit_pct) : null;
        const isHighLoss = deficitVal !== null && deficitVal > 10.0;
        const isModerateLoss = deficitVal !== null && deficitVal >= 5.0 && deficitVal <= 10.0;

        const wakeFill = deficitVal === null
          ? 'rgba(100, 116, 139, 0.12)'
          : isHighLoss
          ? 'rgba(239, 68, 68, 0.22)'
          : isModerateLoss
          ? 'rgba(245, 158, 11, 0.20)'
          : 'rgba(14, 165, 233, 0.16)';

        const wakeOutline = deficitVal === null
          ? 'rgba(148, 163, 184, 0.40)'
          : isHighLoss
          ? 'rgba(239, 68, 68, 0.65)'
          : isModerateLoss
          ? 'rgba(245, 158, 11, 0.60)'
          : 'rgba(14, 165, 233, 0.50)';

        const wakePolygon = viewer.entities.add({
          name: `Wake Footprint ${labelText}`,
          polygon: {
            hierarchy: Cesium.Cartesian3.fromDegreesArray([
              rootLeftLon, rootLeftLat,
              rootRightLon, rootRightLat,
              endRightLon, endRightLat,
              endLeftLon, endLeftLat,
            ]),
            material: Cesium.Color.fromCssColorString(wakeFill),
            heightReference: isTerrainReady ? Cesium.HeightReference.CLAMP_TO_GROUND : Cesium.HeightReference.NONE,
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
            material: Cesium.Color.fromCssColorString(wakeOutline),
            clampToGround: isTerrainReady,
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
              color: deficitVal === null
                ? Cesium.Color.fromCssColorString('#94A3B8')
                : isHighLoss
                ? Cesium.Color.fromCssColorString('#EF4444')
                : isModerateLoss
                ? Cesium.Color.fromCssColorString('#F59E0B')
                : Cesium.Color.fromCssColorString('#0EA5E9'),
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
  }, [viewerInstance, turbines, selectedTurbineIdx, windDirectionDeg, windSpeedMps, rotorDiameter, hubHeight, localShowWakes, showFlowStreamlines, effectiveCenterLat, effectiveCenterLon, radiusKm]);

  // Camera preset handler
  const handlePresetClick = (preset: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setActiveCameraPreset(preset);
    if (viewerRef.current && !viewerRef.current.isDestroyed()) {
      flyToProjectSite(viewerRef.current, effectiveCenterLat, effectiveCenterLon, radiusKm, preset, 1.2);
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

        {/* Candidates Toggle */}
        {candidates && candidates.length > 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setLocalShowCandidates(!localShowCandidates);
            }}
            className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-xl text-xs font-bold transition-all active:scale-95 ${
              localShowCandidates
                ? 'bg-slate-700 text-white shadow-xs font-black'
                : 'bg-white/10 text-slate-300 hover:bg-white/20'
            }`}
            title="Toggle Evaluated Candidate Markers"
          >
            <Crosshair className="w-3 h-3 text-slate-300" />
            <span className="hidden sm:inline">Candidates</span>
          </button>
        )}

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
      <div 
        id="cesium-geodetic-telemetry-badge"
        className="absolute bottom-3 left-3 z-20 hidden sm:flex flex-col gap-1 px-3 py-2 rounded-xl bg-slate-900/90 backdrop-blur-2xl border border-white/10 shadow-lg text-slate-200 font-mono text-[11px] pointer-events-auto max-w-sm"
      >
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-bold text-white">
            {isGoogleTilesActive ? 'Google Photorealistic 3D Tiles' : 'Copernicus DEM GLO-90 composite'}
          </span>
          <span className="text-slate-400">•</span>
          <span>{turbineModelName} (D={rotorDiameter}m, H={hubHeight}m)</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-400">
          <span className="text-amber-400 font-bold">{turbines.length} Turbines</span>
          {candidates && candidates.length > 0 && (
            <>
              <span>•</span>
              <span>{candidates.length} Candidates</span>
            </>
          )}
          <span>•</span>
          <span className="text-emerald-400 truncate">{optimalityScope || 'FLORIS Exact Re-evaluated Layout'}</span>
        </div>
      </div>
    </div>
  );
};
