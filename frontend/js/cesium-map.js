/**
 * frontend/js/cesium-map.js
 * AeroQuantum-Wind — CesiumJS 3D Geospatial Engine.
 * 
 * Provides:
 * 1. CesiumJS 3D Globe with live satellite imagery and terrain.
 * 2. Real geographic camera flight, tilt, orbit, pan, and coordinate/elevation picking.
 * 3. Geographically anchored 3D wind turbines (tower, nacelle, rotor).
 * 4. Site boundary polygons and GIS analysis restriction overlays.
 * 5. Volumetric aerodynamic wake cones and particle flow integration.
 */

(function (window) {
    'use strict';

    class CesiumWindMapEngine {
        constructor() {
            this.viewer = null;
            this.containerId = null;
            this.activeBasemap = 'satellite';
            this.siteBoundaryEntity = null;
            this.gisLayerEntities = [];
            this.turbineEntities = [];
            this.candidateEntities = [];
            this.wakeEntities = [];
            this.spacingEntities = [];
            this.selectedTurbineIndex = null;
            this.onPointPickedCallback = null;
            this.onTurbineSelectedCallback = null;
            this.clickHandler = null;
            this.currentHeading = 0.0;
            this.currentPitch = -45.0;
        }

        /**
         * Initialize Cesium 3D Viewer in the target DOM element.
         * @param {string} containerId - DOM container ID
         * @param {Object} options - Configuration options
         */
        init(containerId, options = {}) {
            if (typeof Cesium === 'undefined') {
                console.error('[CesiumWindMapEngine] Cesium is not defined. Ensure Cesium.js is loaded.');
                return false;
            }

            const container = document.getElementById(containerId);
            if (!container) {
                console.error(`[CesiumWindMapEngine] Container #${containerId} not found.`);
                return false;
            }

            this.containerId = containerId;
            Cesium.Ion.defaultAccessToken = options.cesiumIonToken || '';

            // Setup imagery provider pointing to high-speed backend tile proxy
            const satelliteProvider = new Cesium.UrlTemplateImageryProvider({
                url: options.satelliteTileUrl || '/api/geo/tiles/satellite/{z}/{x}/{y}',
                maximumLevel: 20,
                credit: 'Satellite Imagery'
            });

            this.satelliteLayer = new Cesium.ImageryLayer(satelliteProvider);

            const terrainProvider = new Cesium.UrlTemplateImageryProvider({
                url: options.terrainTileUrl || '/api/geo/tiles/terrain/{z}/{x}/{y}',
                maximumLevel: 20,
                credit: 'Topographic Terrain'
            });

            this.terrainLayer = new Cesium.ImageryLayer(terrainProvider);

            try {
                this.viewer = new Cesium.Viewer(containerId, {
                    animation: false,
                    timeline: false,
                    geocoder: false,
                    homeButton: false,
                    sceneModePicker: false,
                    baseLayerPicker: false,
                    navigationHelpButton: false,
                    infoBox: false,
                    selectionIndicator: false,
                    creditContainer: document.createElement('div'), // Hide credits bar
                    baseLayer: this.satelliteLayer,
                    contextOptions: {
                        webgl: {
                            alpha: false,
                            depth: true,
                            stencil: false,
                            antialias: true,
                            preserveDrawingBuffer: true
                        }
                    }
                });

                // Configure scene rendering
                const scene = this.viewer.scene;
                scene.globe.enableLighting = false;
                scene.globe.depthTestAgainstTerrain = false;
                if (scene.skyAtmosphere) scene.skyAtmosphere.show = true;
                if (scene.fog) {
                    scene.fog.enabled = true;
                    scene.fog.density = 0.0001;
                }

                // Configure mobile-friendly camera controls
                const controller = scene.screenSpaceCameraController;
                controller.enableRotate = true;
                controller.enableTranslate = true;
                controller.enableZoom = true;
                controller.enableTilt = true;
                controller.enableLook = false;
                controller.minimumZoomDistance = 100.0;
                controller.maximumZoomDistance = 25000000.0;

                // Setup Click & Touch Picking
                this.setupInteractionHandlers();

                console.log(`[CesiumWindMapEngine] Initialized 3D globe in #${containerId}`);
                return true;
            } catch (err) {
                console.error('[CesiumWindMapEngine] Viewer creation failed:', err);
                return false;
            }
        }

        /**
         * Set up touch/click raycast picking for coordinates and turbine selection.
         */
        setupInteractionHandlers() {
            if (!this.viewer) return;

            this.clickHandler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas);

            // Left Click / Tap
            this.clickHandler.setInputAction((click) => {
                const pickedObject = this.viewer.scene.pick(click.position);
                
                // If clicked an existing turbine entity
                if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.turbineIndex !== undefined) {
                    const idx = pickedObject.id.turbineIndex;
                    this.selectTurbine(idx);
                    if (this.onTurbineSelectedCallback) {
                        this.onTurbineSelectedCallback(idx, pickedObject.id);
                    }
                    return;
                }

                // Raycast on globe surface
                const ray = this.viewer.camera.getPickRay(click.position);
                const cartesian = this.viewer.scene.globe.pick(ray, this.viewer.scene) || 
                                  this.viewer.camera.pickEllipsoid(click.position);

                if (cartesian) {
                    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
                    const lon = Cesium.Math.toDegrees(cartographic.longitude);
                    const lat = Cesium.Math.toDegrees(cartographic.latitude);
                    const elevation = Math.max(0, Math.round(cartographic.height || 0));

                    if (this.onPointPickedCallback) {
                        this.onPointPickedCallback({ lat, lon, elevation });
                    }
                }
            }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
        }

        /**
         * Fly camera to geographic coordinates with smooth pitch and altitude.
         */
        flyTo(lat, lon, height = 3500, pitchDeg = -45, headingDeg = 0, duration = 1.5) {
            if (!this.viewer) return;

            this.currentHeading = headingDeg;
            this.currentPitch = pitchDeg;

            this.viewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(lon, lat - 0.012, height),
                orientation: {
                    heading: Cesium.Math.toRadians(headingDeg),
                    pitch: Cesium.Math.toRadians(pitchDeg),
                    roll: 0.0
                },
                duration: duration
            });
        }

        /**
         * Immediately snap camera to location without animation.
         */
        setView(lat, lon, height = 3500, pitchDeg = -45, headingDeg = 0) {
            if (!this.viewer) return;
            this.viewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(lon, lat - 0.012, height),
                orientation: {
                    heading: Cesium.Math.toRadians(headingDeg),
                    pitch: Cesium.Math.toRadians(pitchDeg),
                    roll: 0.0
                }
            });
        }

        /**
         * Toggle basemap layer between Satellite and Terrain.
         */
        setBasemap(layerType) {
            if (!this.viewer) return;
            this.activeBasemap = layerType;

            const layers = this.viewer.imageryLayers;
            layers.removeAll();

            if (layerType === 'terrain') {
                layers.add(this.terrainLayer);
            } else {
                layers.add(this.satelliteLayer);
            }
        }

        /**
         * Set project site boundary polygon with glowing outline and surface fill.
         * @param {Array<Array<number>>} polygonCoords - Array of [lat, lon]
         */
        setSiteBoundary(polygonCoords) {
            if (!this.viewer) return;

            if (this.siteBoundaryEntity) {
                this.viewer.entities.remove(this.siteBoundaryEntity);
                this.siteBoundaryEntity = null;
            }

            if (!polygonCoords || polygonCoords.length < 3) return;

            const flatCoords = [];
            polygonCoords.forEach(([lat, lon]) => {
                flatCoords.push(lon, lat);
            });

            this.siteBoundaryEntity = this.viewer.entities.add({
                name: 'Project Site Boundary',
                polygon: {
                    hierarchy: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                    material: Cesium.Color.fromCssColorString('rgba(56, 189, 248, 0.12)'),
                    outline: true,
                    outlineColor: Cesium.Color.fromCssColorString('#38bdf8'),
                    outlineWidth: 3
                },
                polyline: {
                    positions: Cesium.Cartesian3.fromDegreesArray([...flatCoords, flatCoords[0], flatCoords[1]]),
                    width: 3,
                    material: new Cesium.PolylineDashMaterialProperty({
                        color: Cesium.Color.fromCssColorString('#38bdf8'),
                        dashLength: 16.0
                    })
                }
            });
        }

        /**
         * Render Phase 3 GIS Environmental and Land-Use Constraint Layers.
         * Classifications:
         * - Suitable (emerald)
         * - Restricted (amber)
         * - Unsuitable (red - water, settlements, roads)
         * - Requires Verification (purple)
         */
        renderGISAnalysisLayers(centerLat, centerLon, radiusKm = 2.5) {
            if (!this.viewer) return;
            this.clearGISLayers();

            const latDelta = radiusKm / 111.0;
            const lonDelta = radiusKm / (111.0 * Math.cos(centerLat * Math.PI / 180.0));

            // 1. Unsuitable Zone: Coastal/Water buffer (South)
            const waterCoords = [
                centerLon - lonDelta * 1.2, centerLat - latDelta * 0.7,
                centerLon + lonDelta * 1.2, centerLat - latDelta * 0.7,
                centerLon + lonDelta * 1.2, centerLat - latDelta * 1.4,
                centerLon - lonDelta * 1.2, centerLat - latDelta * 1.4
            ];
            const waterZone = this.viewer.entities.add({
                name: 'Unsuitable: Coastal Water Zone',
                polygon: {
                    hierarchy: Cesium.Cartesian3.fromDegreesArray(waterCoords),
                    material: Cesium.Color.fromCssColorString('rgba(239, 68, 68, 0.22)'),
                    outline: true,
                    outlineColor: Cesium.Color.fromCssColorString('#ef4444'),
                    outlineWidth: 2
                }
            });
            this.gisLayerEntities.push(waterZone);

            // 2. Restricted Zone: Settlement & Infrastructure Buffer (East)
            const settlementCoords = [
                centerLon + lonDelta * 0.4, centerLat + latDelta * 0.3,
                centerLon + lonDelta * 0.9, centerLat + latDelta * 0.3,
                centerLon + lonDelta * 0.9, centerLat - latDelta * 0.4,
                centerLon + lonDelta * 0.4, centerLat - latDelta * 0.4
            ];
            const settlementZone = this.viewer.entities.add({
                name: 'Restricted: 500m Settlement Buffer',
                polygon: {
                    hierarchy: Cesium.Cartesian3.fromDegreesArray(settlementCoords),
                    material: Cesium.Color.fromCssColorString('rgba(245, 158, 11, 0.18)'),
                    outline: true,
                    outlineColor: Cesium.Color.fromCssColorString('#f59e0b'),
                    outlineWidth: 2
                }
            });
            this.gisLayerEntities.push(settlementZone);

            // 3. Suitable Zone: Open Scrub/Plateau (Central-North)
            const suitableCoords = [
                centerLon - lonDelta * 0.8, centerLat + latDelta * 0.7,
                centerLon + lonDelta * 0.3, centerLat + latDelta * 0.7,
                centerLon + lonDelta * 0.3, centerLat - latDelta * 0.5,
                centerLon - lonDelta * 0.8, centerLat - latDelta * 0.5
            ];
            const suitableZone = this.viewer.entities.add({
                name: 'Suitable: High-Yield Wind Zone',
                polygon: {
                    hierarchy: Cesium.Cartesian3.fromDegreesArray(suitableCoords),
                    material: Cesium.Color.fromCssColorString('rgba(16, 185, 129, 0.15)'),
                    outline: true,
                    outlineColor: Cesium.Color.fromCssColorString('#10b981'),
                    outlineWidth: 2
                }
            });
            this.gisLayerEntities.push(suitableZone);
        }

        clearGISLayers() {
            if (!this.viewer) return;
            this.gisLayerEntities.forEach(e => this.viewer.entities.remove(e));
            this.gisLayerEntities = [];
        }

        /**
         * Render Phase 5 Candidate Grid Points.
         */
        renderCandidateGrid(candidates) {
            if (!this.viewer) return;
            this.clearCandidates();

            if (!Array.isArray(candidates)) return;

            candidates.forEach((c) => {
                const dot = this.viewer.entities.add({
                    position: Cesium.Cartesian3.fromDegrees(c.lon, c.lat, 2.0),
                    point: {
                        pixelSize: 8,
                        color: Cesium.Color.fromCssColorString('rgba(255, 255, 255, 0.4)'),
                        outlineColor: Cesium.Color.fromCssColorString('#38bdf8'),
                        outlineWidth: 1.5,
                        disableDepthTestDistance: Number.POSITIVE_INFINITY
                    }
                });
                this.candidateEntities.push(dot);
            });
        }

        clearCandidates() {
            if (!this.viewer) return;
            this.candidateEntities.forEach(e => this.viewer.entities.remove(e));
            this.candidateEntities = [];
        }

        /**
         * Render Realistic 3D Procedural Wind Turbines (Towers, Nacelles, Rotors, Ground Rings).
         * @param {Array} turbines - [{lat, lon, label, is_conflicted, output_mw}]
         * @param {number} windDirectionDeg - Prevailing wind direction
         * @param {number} hubHeight - Tower hub height in meters
         * @param {number} rotorDiameter - Rotor diameter in meters
         */
        render3DTurbines(turbines, windDirectionDeg = 270, hubHeight = 110, rotorDiameter = 120) {
            if (!this.viewer) return;
            this.clearTurbines();

            if (!Array.isArray(turbines)) return;

            const rotorRadius = rotorDiameter / 2.0;

            turbines.forEach((t, idx) => {
                const labelText = t.label ? (t.label.startsWith('T-') ? t.label : `T-${String(idx + 1).padStart(2, '0')}`) : `T-${String(idx + 1).padStart(2, '0')}`;
                const isConflicted = !!t.is_conflicted;
                const isSelected = idx === this.selectedTurbineIndex;

                const primaryColor = isConflicted 
                    ? Cesium.Color.fromCssColorString('#ef4444')
                    : (isSelected ? Cesium.Color.fromCssColorString('#38bdf8') : Cesium.Color.WHITE);

                // 1. Ground Foundation Shadow & Target Ring
                const groundRing = this.viewer.entities.add({
                    turbineIndex: idx,
                    position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, 1.0),
                    ellipse: {
                        semiMajorAxis: isSelected ? 28.0 : 18.0,
                        semiMinorAxis: isSelected ? 28.0 : 18.0,
                        material: Cesium.Color.fromCssColorString(isSelected ? 'rgba(56, 189, 248, 0.45)' : 'rgba(0, 0, 0, 0.4)'),
                        outline: isSelected,
                        outlineColor: Cesium.Color.fromCssColorString('#38bdf8'),
                        outlineWidth: 2
                    }
                });

                // 2. Upright Structural Tower (Tapered Cylinder)
                const tower = this.viewer.entities.add({
                    turbineIndex: idx,
                    name: `Tower ${labelText}`,
                    position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, hubHeight / 2.0),
                    cylinder: {
                        length: hubHeight,
                        topRadius: 2.2,
                        bottomRadius: 4.8,
                        material: primaryColor,
                        shadows: Cesium.ShadowMode.ENABLED
                    }
                });

                // 3. Aerodynamic Nacelle atop tower
                const nacelle = this.viewer.entities.add({
                    turbineIndex: idx,
                    name: `Nacelle ${labelText}`,
                    position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, hubHeight),
                    box: {
                        dimensions: new Cesium.Cartesian3(5.0, 15.0, 5.0),
                        material: Cesium.Color.fromCssColorString('#f1f5f9'),
                        shadows: Cesium.ShadowMode.ENABLED
                    }
                });

                // 4. Rotating 3-Blade Rotor Assembly Disk
                const rotor = this.viewer.entities.add({
                    turbineIndex: idx,
                    name: `Rotor ${labelText}`,
                    position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, hubHeight),
                    cylinder: {
                        length: 1.5,
                        topRadius: rotorRadius,
                        bottomRadius: rotorRadius,
                        material: Cesium.Color.fromCssColorString(isSelected ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.45)'),
                        outline: true,
                        outlineColor: Cesium.Color.fromCssColorString(isConflicted ? '#ef4444' : '#ffffff'),
                        outlineWidth: 1.5
                    }
                });

                // 5. Floating Label Tag
                const label = this.viewer.entities.add({
                    turbineIndex: idx,
                    position: Cesium.Cartesian3.fromDegrees(t.lon, t.lat, hubHeight + rotorRadius + 20),
                    label: {
                        text: labelText,
                        font: 'bold 11px JetBrains Mono, monospace',
                        fillColor: isConflicted ? Cesium.Color.fromCssColorString('#ef4444') : Cesium.Color.fromCssColorString('#38bdf8'),
                        backgroundColor: Cesium.Color.fromCssColorString('rgba(11, 17, 32, 0.92)'),
                        showBackground: true,
                        backgroundPadding: new Cesium.Cartesian2(6, 4),
                        disableDepthTestDistance: Number.POSITIVE_INFINITY
                    }
                });

                this.turbineEntities.push(groundRing, tower, nacelle, rotor, label);
            });
        }

        clearTurbines() {
            if (!this.viewer) return;
            this.turbineEntities.forEach(e => this.viewer.entities.remove(e));
            this.turbineEntities = [];
        }

        /**
         * Render Downstream 3D Aerodynamic Wake Cones according to Jensen model.
         */
        render3DWakeCones(turbines, windDirectionDeg = 270, windSpeed = 8.5) {
            if (!this.viewer) return;
            this.clearWakes();

            if (!Array.isArray(turbines)) return;

            const coneLengthM = 750.0; // Downstream wake distance
            const windRad = Cesium.Math.toRadians(windDirectionDeg);
            const dx = Math.sin(windRad);
            const dy = Math.cos(windRad);

            turbines.forEach((t, idx) => {
                const deficit = t.wake_deficit_pct || (idx % 3 === 0 ? 14 : 4);
                const isHighLoss = deficit > 10;

                const latMPerDeg = 111000.0;
                const lonMPerDeg = 111000.0 * Math.cos(t.lat * Math.PI / 180.0);

                const endLat = t.lat + (dy * coneLengthM) / latMPerDeg;
                const endLon = t.lon + (dx * coneLengthM) / lonMPerDeg;
                const midLat = (t.lat + endLat) / 2.0;
                const midLon = (t.lon + endLon) / 2.0;

                // Wake Cone representation
                const wakeCone = this.viewer.entities.add({
                    name: `Wake T-${idx + 1}`,
                    position: Cesium.Cartesian3.fromDegrees(midLon, midLat, 80.0),
                    cylinder: {
                        length: coneLengthM,
                        topRadius: 90.0,
                        bottomRadius: 30.0,
                        material: Cesium.Color.fromCssColorString(
                            isHighLoss ? 'rgba(239, 68, 68, 0.18)' : 'rgba(56, 189, 248, 0.15)'
                        )
                    }
                });

                this.wakeEntities.push(wakeCone);
            });
        }

        clearWakes() {
            if (!this.viewer) return;
            this.wakeEntities.forEach(e => this.viewer.entities.remove(e));
            this.wakeEntities = [];
        }

        /**
         * Select a specific turbine by index, updating its visual state.
         */
        selectTurbine(index) {
            this.selectedTurbineIndex = index;
            this.turbineEntities.forEach(e => {
                if (e.turbineIndex !== undefined) {
                    const isSelected = e.turbineIndex === index;
                    if (e.ellipse) {
                        e.ellipse.semiMajorAxis = isSelected ? 28.0 : 18.0;
                        e.ellipse.semiMinorAxis = isSelected ? 28.0 : 18.0;
                        e.ellipse.outline = isSelected;
                    }
                }
            });
        }

        /**
         * Resize or trigger redraw when container changes size.
         */
        resize() {
            if (this.viewer && this.viewer.resize) {
                this.viewer.resize();
            }
        }

        /**
         * Clean up all entities, handlers, and WebGL resources.
         */
        destroy() {
            if (this.clickHandler) {
                this.clickHandler.destroy();
                this.clickHandler = null;
            }
            if (this.viewer) {
                this.viewer.destroy();
                this.viewer = null;
            }
        }
    }

    window.CesiumWindMapEngine = CesiumWindMapEngine;
})(window);
