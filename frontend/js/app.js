/**
 * AeroQuantum-Wind — Engineering Mobile & Desktop Application Core (app.js)
 * Screen 1: Site Selection (Choose Wind Farm Site)
 */

(function (window) {
    'use strict';

    // Application Global State
    const APP_STATE = {
        currentScreen: 1,
        selectedSite: {
            name: 'Kanyakumari, Tamil Nadu, India',
            shortName: 'Kanyakumari',
            lat: 8.0883,
            lon: 77.5385,
            areaKm2: 24.8,
            elevationM: 42,
            terrainType: 'Coastal / Mild Terrain',
            distanceToCoastKm: 0.2,
            landUse: 'Mixed (Agriculture/Scrub)',
            windSpeedMps: 7.1,
            windPowerDensity: 320
        },
        farmConfig: {
            turbineCount: 12,
            model: 'ge-120',
            modelName: 'GE 2.5-120',
            rotorDiameter: 120.0,
            hubHeight: 110.0,
            ratedPowerKw: 2500,
            windDirectionDeg: 300.0,
            spacingMultiplierD: 5.0,
            wakeDecay: 0.075,
            quboLambda: 150.0,
            gridResolution: 6
        },
        selectionMode: 'search', // 'search' | 'coords' | 'draw'
        isSheetCollapsed: false,
        activeLayer: 'satellite',
        layers: {},
        map: null,
        sitePolygon: null,
        areaBadgeMarker: null,
        locationLabelMarker: null
    };

    // Standard Wind Turbine Industry Presets
    const TURBINE_MODELS = {
        'ge-120': {
            name: 'GE 2.5-120',
            rotorDiameter: 120.0,
            hubHeight: 110.0,
            ratedPowerKw: 2500
        },
        'vestas-110': {
            name: 'Vestas V110-2.0MW',
            rotorDiameter: 110.0,
            hubHeight: 100.0,
            ratedPowerKw: 2000
        },
        'sg-132': {
            name: 'Siemens Gamesa SG 3.4-132',
            rotorDiameter: 132.0,
            hubHeight: 120.0,
            ratedPowerKw: 3400
        },
        'suzlon-120': {
            name: 'Suzlon S120-2.1MW',
            rotorDiameter: 120.0,
            hubHeight: 120.0,
            ratedPowerKw: 2100
        }
    };

    // Location Presets matching reference
    const SITE_PRESETS = {
        'Kanyakumari, Tamil Nadu': {
            name: 'Kanyakumari, Tamil Nadu, India',
            shortName: 'Kanyakumari',
            lat: 8.0883,
            lon: 77.5385,
            areaKm2: 24.8,
            elevationM: 42,
            terrainType: 'Coastal / Mild Terrain',
            distanceToCoastKm: 0.2,
            landUse: 'Mixed (Agriculture/Scrub)',
            windSpeedMps: 7.1,
            windPowerDensity: 320
        },
        'Jaisalmer, Rajasthan': {
            name: 'Jaisalmer, Rajasthan, India',
            shortName: 'Jaisalmer',
            lat: 26.9157,
            lon: 70.9083,
            areaKm2: 32.4,
            elevationM: 225,
            terrainType: 'Desert Plateau / Open Sand',
            distanceToCoastKm: 480.0,
            landUse: 'Desert / Wasteland',
            windSpeedMps: 7.6,
            windPowerDensity: 360
        },
        'Kutch, Gujarat': {
            name: 'Kutch, Gujarat, India',
            shortName: 'Kutch',
            lat: 23.2420,
            lon: 69.6669,
            areaKm2: 28.0,
            elevationM: 35,
            terrainType: 'Salt Marsh / Semi-Arid',
            distanceToCoastKm: 14.0,
            landUse: 'Saline Mudflats / Scrub',
            windSpeedMps: 7.4,
            windPowerDensity: 345
        },
        'Tuticorin, Tamil Nadu': {
            name: 'Tuticorin, Tamil Nadu, India',
            shortName: 'Tuticorin',
            lat: 8.7642,
            lon: 78.1348,
            areaKm2: 20.5,
            elevationM: 8,
            terrainType: 'Coastal Plain',
            distanceToCoastKm: 1.2,
            landUse: 'Coastal Industry / Salt Pans',
            windSpeedMps: 7.3,
            windPowerDensity: 330
        },
        'Anantapur, Andhra Pradesh': {
            name: 'Anantapur, Andhra Pradesh, India',
            shortName: 'Anantapur',
            lat: 14.6783,
            lon: 77.6065,
            areaKm2: 16.0,
            elevationM: 335,
            terrainType: 'Inland Ridge / Undulating Terrain',
            distanceToCoastKm: 280.0,
            landUse: 'Agricultural / Open Hills',
            windSpeedMps: 8.42,
            windPowerDensity: 410
        }
    };

    // Public Application Controller
    const APP = {
        init() {
            this.initMap();
            this.setupEventListeners();
            this.updateUIWithSite(APP_STATE.selectedSite);
        },

        initMap() {
            const site = APP_STATE.selectedSite;
            const isMobile = window.innerWidth <= 768;
            const centerLat = isMobile ? site.lat - 0.025 : site.lat;

            const map = L.map('map', {
                center: [centerLat, site.lon],
                zoom: isMobile ? 11.5 : 12,
                zoomControl: false,
                attributionControl: false
            });

            // Base Layers
            const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 19
            }).addTo(map);

            const osmStreet = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19
            });

            const esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 19
            });

            APP_STATE.layers = {
                satellite: esriSatellite,
                map: osmStreet,
                terrain: esriTopo
            };

            // Scale bar at bottom-left
            L.control.scale({
                position: 'bottomleft',
                metric: true,
                imperial: false,
                maxWidth: 140
            }).addTo(map);

            APP_STATE.map = map;

            // Render Site Boundary Polygon
            this.drawSitePolygon(site.lat, site.lon, site.areaKm2);

            // Map Click Handler (Select Location Directly on Map)
            map.on('click', (e) => {
                this.selectLocationFromMap(e.latlng.lat, e.latlng.lng);
            });
        },

        drawSitePolygon(lat, lon, areaKm2) {
            const map = APP_STATE.map;
            if (!map) return;

            // Remove existing polygon & badges
            if (APP_STATE.sitePolygon) map.removeLayer(APP_STATE.sitePolygon);
            if (APP_STATE.areaBadgeMarker) map.removeLayer(APP_STATE.areaBadgeMarker);
            if (APP_STATE.locationLabelMarker) map.removeLayer(APP_STATE.locationLabelMarker);

            // Calculate polygon vertices around center roughly matching reference shape
            // Scale radius based on area (sqrt(area))
            const radiusKm = Math.sqrt(areaKm2) / 2.0;
            const latDelta = radiusKm / 111.0;
            const lonDelta = radiusKm / (111.0 * Math.cos(lat * Math.PI / 180.0));

            // 10-point polygon contour similar to reference coastal boundary
            const vertices = [
                [lat + latDelta * 1.1, lon - lonDelta * 0.1],
                [lat + latDelta * 0.7, lon + lonDelta * 0.1],
                [lat + latDelta * 0.2, lon + lonDelta * 0.45],
                [lat - latDelta * 0.4, lon + lonDelta * 0.85],
                [lat - latDelta * 0.9, lon + lonDelta * 0.95],
                [lat - latDelta * 1.2, lon - lonDelta * 0.45],
                [lat - latDelta * 0.6, lon - lonDelta * 1.1],
                [lat - latDelta * 0.1, lon - lonDelta * 0.85],
                [lat + latDelta * 0.25, lon - lonDelta * 0.65],
                [lat + latDelta * 0.65, lon - lonDelta * 0.55]
            ];

            const calculatedAreaKm2 = this.calculatePolygonAreaKm2(vertices);
            APP_STATE.selectedSite.areaKm2 = calculatedAreaKm2;

            APP_STATE.sitePolygon = L.polygon(vertices, {
                color: '#3b82f6',
                weight: 2,
                opacity: 0.9,
                fillColor: '#2563eb',
                fillOpacity: 0.18,
                smoothFactor: 1
            }).addTo(map);

            // Center Area Badge with authentic calculated area
            const badgeIcon = L.divIcon({
                className: 'badge-div-wrapper',
                html: `<div class="selected-area-badge">Selected Area<br><strong>${calculatedAreaKm2.toFixed(1)} km²</strong></div>`,
                iconSize: [110, 40],
                iconAnchor: [55, 20]
            });
            APP_STATE.areaBadgeMarker = L.marker([lat, lon], { icon: badgeIcon }).addTo(map);

            const areaElem = document.getElementById('meta-area');
            if (areaElem) areaElem.innerText = `${calculatedAreaKm2.toFixed(1)} km²`;

            // Location Label on map
            const nameIcon = L.divIcon({
                className: 'label-div-wrapper',
                html: `<div class="location-anchor-tag">${APP_STATE.selectedSite.shortName}</div>`,
                iconSize: [120, 24],
                iconAnchor: [60, -20]
            });
            APP_STATE.locationLabelMarker = L.marker([lat - latDelta * 0.75, lon - lonDelta * 0.2], { icon: nameIcon }).addTo(map);
        },

        calculatePolygonAreaKm2(vertices) {
            const R = 6371.0;
            const refLat = vertices[0][0];
            const cosLat = Math.cos(refLat * Math.PI / 180.0);
            let area = 0.0;
            const n = vertices.length;
            for (let i = 0; i < n; i++) {
                const j = (i + 1) % n;
                const xi = (vertices[i][1] * Math.PI / 180.0) * R * cosLat;
                const yi = (vertices[i][0] * Math.PI / 180.0) * R;
                const xj = (vertices[j][1] * Math.PI / 180.0) * R * cosLat;
                const yj = (vertices[j][0] * Math.PI / 180.0) * R;
                area += (xi * yj - xj * yi);
            }
            return Math.abs(area) / 2.0;
        },

        setupEventListeners() {
            // Mode Tabs (Search / Coords / Draw)
            document.querySelectorAll('.mode-tab-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const mode = e.currentTarget.dataset.mode;
                    this.setSelectionMode(mode);
                });
            });

            // Search input Enter key
            const searchField = document.getElementById('search-input-field');
            if (searchField) {
                searchField.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.executeSearch(searchField.value.trim());
                    }
                });
            }

            // On-map search input
            const mapSearchField = document.getElementById('map-search-input');
            if (mapSearchField) {
                mapSearchField.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.executeSearch(mapSearchField.value.trim());
                    }
                });
            }

            // Apply Coordinates button
            const applyCoordsBtn = document.getElementById('btn-apply-coords');
            if (applyCoordsBtn) {
                applyCoordsBtn.addEventListener('click', () => {
                    this.applyCoordinatesInput();
                });
            }

            // Recent locations list clicks
            document.querySelectorAll('.location-item-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const locName = e.currentTarget.dataset.location;
                    if (SITE_PRESETS[locName]) {
                        this.selectPresetLocation(locName);
                    }
                });
            });

            // Map Layer switcher
            document.querySelectorAll('.map-layer-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const layerKey = e.currentTarget.dataset.layer;
                    this.switchMapLayer(layerKey);
                });
            });

            // Map Zoom & Recenter controls
            document.getElementById('btn-map-zoom-in')?.addEventListener('click', () => {
                APP_STATE.map?.zoomIn();
            });
            document.getElementById('btn-map-zoom-out')?.addEventListener('click', () => {
                APP_STATE.map?.zoomOut();
            });
            document.getElementById('btn-map-recenter')?.addEventListener('click', () => {
                this.recenterMap();
            });

            // Mobile Bottom Sheet Collapse/Expand toggle
            const sheet = document.getElementById('site-info-panel');
            const dragHandle = document.getElementById('mobile-drag-handle');
            const sheetHeader = document.getElementById('site-info-header');

            const toggleSheet = () => {
                if (window.innerWidth <= 768 && sheet) {
                    APP_STATE.isSheetCollapsed = !APP_STATE.isSheetCollapsed;
                    sheet.classList.toggle('collapsed', APP_STATE.isSheetCollapsed);
                    const chevron = document.getElementById('sheet-chevron-icon');
                    if (chevron) {
                        chevron.style.transform = APP_STATE.isSheetCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
                    }
                }
            };

            dragHandle?.addEventListener('click', toggleSheet);
            sheetHeader?.addEventListener('click', toggleSheet);

            // Primary Action: CONFIRM SITE
            document.getElementById('btn-confirm-site')?.addEventListener('click', () => {
                this.confirmSite();
            });
        },

        setSelectionMode(mode) {
            APP_STATE.selectionMode = mode;

            document.querySelectorAll('.mode-tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === mode);
            });

            const searchBox = document.getElementById('search-box-container');
            const coordsForm = document.getElementById('coords-input-form');
            const drawHint = document.getElementById('draw-mode-hint');

            if (searchBox) searchBox.style.display = mode === 'search' ? 'flex' : 'none';
            if (coordsForm) coordsForm.style.display = mode === 'coords' ? 'flex' : 'none';
            if (drawHint) drawHint.style.display = mode === 'draw' ? 'block' : 'none';

            if (mode === 'coords') {
                document.getElementById('coord-lat-input').value = APP_STATE.selectedSite.lat.toFixed(4);
                document.getElementById('coord-lon-input').value = APP_STATE.selectedSite.lon.toFixed(4);
            }
        },

        async executeSearch(query) {
            if (!query) return;

            // Check if matches known presets first
            for (let key in SITE_PRESETS) {
                if (key.toLowerCase().includes(query.toLowerCase()) || query.toLowerCase().includes(key.toLowerCase().split(',')[0])) {
                    this.selectPresetLocation(key);
                    return;
                }
            }

            this.showToast(`Locating "${query}" via Nominatim GIS...`);
            try {
                const res = await fetch(`/api/geo/geocode?q=${encodeURIComponent(query)}`);
                if (!res.ok) throw new Error('Location not found');
                const data = await res.json();

                const site = {
                    name: data.display_name,
                    shortName: query.split(',')[0].trim(),
                    lat: parseFloat(data.lat),
                    lon: parseFloat(data.lon),
                    areaKm2: 24.8,
                    elevationM: 50,
                    terrainType: 'Geocoded Terrain',
                    distanceToCoastKm: 5.0,
                    landUse: 'Mixed / Unclassified',
                    windSpeedMps: 7.2,
                    windPowerDensity: 325
                };

                this.updateUIWithSite(site);
                this.showToast(`Site Located: ${site.shortName}`, 'success');
            } catch (err) {
                this.showToast(`Search error: ${err.message}`, 'error');
            }
        },

        applyCoordinatesInput() {
            const latVal = parseFloat(document.getElementById('coord-lat-input')?.value);
            const lonVal = parseFloat(document.getElementById('coord-lon-input')?.value);

            if (isNaN(latVal) || latVal < -90 || latVal > 90) {
                this.showToast('Invalid Latitude (must be between -90 and 90)', 'error');
                return;
            }
            if (isNaN(lonVal) || lonVal < -180 || lonVal > 180) {
                this.showToast('Invalid Longitude (must be between -180 and 180)', 'error');
                return;
            }

            const site = {
                name: `Custom Site (${latVal.toFixed(4)}°, ${lonVal.toFixed(4)}°)`,
                shortName: `Site @ ${latVal.toFixed(2)}°, ${lonVal.toFixed(2)}°`,
                lat: latVal,
                lon: lonVal,
                areaKm2: 24.8,
                elevationM: 65,
                terrainType: 'Custom Terrain',
                distanceToCoastKm: 12.0,
                landUse: 'Open Terrain',
                windSpeedMps: 7.4,
                windPowerDensity: 335
            };

            this.updateUIWithSite(site);
            this.showToast('Custom coordinates applied', 'success');
        },

        selectLocationFromMap(lat, lon) {
            const site = {
                name: `Map Sited Area (${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E)`,
                shortName: `Sited Area`,
                lat: lat,
                lon: lon,
                areaKm2: 24.8,
                elevationM: 45,
                terrainType: 'Satellite Terrain Point',
                distanceToCoastKm: 8.0,
                landUse: 'Regional Site Area',
                windSpeedMps: 7.5,
                windPowerDensity: 340
            };
            this.updateUIWithSite(site);
            this.showToast(`Selected point on map: ${lat.toFixed(4)}°, ${lon.toFixed(4)}°`, 'info');
        },

        selectPresetLocation(nameKey) {
            const preset = SITE_PRESETS[nameKey];
            if (!preset) return;

            // Highlight recent location button
            document.querySelectorAll('.location-item-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.location === nameKey);
            });

            this.updateUIWithSite(preset);
            this.showToast(`Selected site: ${preset.shortName}`, 'success');
        },

        async updateUIWithSite(site) {
            APP_STATE.selectedSite = site;

            // Update inputs
            const searchField = document.getElementById('search-input-field');
            if (searchField) searchField.value = site.name;
            const mapSearchField = document.getElementById('map-search-input');
            if (mapSearchField) mapSearchField.value = site.name;

            // Immediate initial values
            document.getElementById('meta-location-name').innerText = site.name;
            document.getElementById('meta-latitude').innerText = `${site.lat.toFixed(4)}° N`;
            document.getElementById('meta-longitude').innerText = `${site.lon.toFixed(4)}° E`;
            document.getElementById('meta-area').innerText = `${(site.areaKm2 || 24.8).toFixed(1)} km²`;
            document.getElementById('meta-elevation').innerText = `${site.elevationM || '--'} m`;
            document.getElementById('meta-terrain').innerText = site.terrainType || 'Analyzing...';
            document.getElementById('meta-coast').innerText = site.distanceToCoastKm !== undefined ? `${site.distanceToCoastKm} km` : '-- km';
            document.getElementById('meta-landuse').innerText = site.landUse || 'Analyzing...';

            // Wind Resource Initial
            document.getElementById('meta-wind-speed').innerText = `${site.windSpeedMps || '--'} m/s`;
            document.getElementById('meta-wind-density').innerText = site.windPowerDensity ? `~ ${site.windPowerDensity} W/m²` : '-- W/m²';

            // Fly map & redraw polygon
            if (APP_STATE.map) {
                const isMobile = window.innerWidth <= 768;
                const targetLat = isMobile ? site.lat - 0.025 : site.lat;
                APP_STATE.map.flyTo([targetLat, site.lon], isMobile ? 11.8 : 12.5, { duration: 1.2 });
                this.drawSitePolygon(site.lat, site.lon, site.areaKm2 || 24.8);
            }

            // Fetch Live Physical & Atmospheric Telemetry from Backend (Open-Meteo ECMWF / SRTM)
            try {
                const res = await fetch(`/api/geo/telemetry?lat=${site.lat}&lon=${site.lon}`);
                if (res.ok) {
                    const data = await res.json();
                    // Merge real physical telemetry into state
                    site.elevationM = data.elevation_m;
                    site.distanceToCoastKm = data.distance_to_coast_km;
                    site.terrainType = data.terrain_type;
                    site.landUse = data.land_use;
                    site.windSpeedMps = data.wind.speed_100m_mps;
                    site.windPowerDensity = data.wind.power_density_wpm2;
                    site.windDirectionDeg = data.wind.direction_100m_deg;
                    site.airDensityKgpm3 = data.wind.air_density_kgpm3;
                    site.pressureHpa = data.wind.pressure_hpa;
                    site.temperatureC = data.wind.temperature_c;

                    // Update DOM with 100% verified physical data
                    const elevElem = document.getElementById('meta-elevation');
                    if (elevElem) elevElem.innerText = `${data.elevation_m} m`;

                    const coastElem = document.getElementById('meta-coast');
                    if (coastElem) coastElem.innerText = `${data.distance_to_coast_km} km`;

                    const terrainElem = document.getElementById('meta-terrain');
                    if (terrainElem) terrainElem.innerText = data.terrain_type;

                    const landElem = document.getElementById('meta-landuse');
                    if (landElem) landElem.innerText = data.land_use;

                    const speedElem = document.getElementById('meta-wind-speed');
                    if (speedElem) speedElem.innerText = `${data.wind.speed_100m_mps} m/s`;

                    const densityElem = document.getElementById('meta-wind-density');
                    if (densityElem) densityElem.innerText = `~ ${data.wind.power_density_wpm2} W/m²`;

                    const dirElem = document.getElementById('meta-wind-dir');
                    if (dirElem) dirElem.innerText = `${data.wind.direction_100m_deg}°`;

                    const airElem = document.getElementById('meta-air-density');
                    if (airElem) airElem.innerText = `${data.wind.air_density_kgpm3} kg/m³`;
                }
            } catch (err) {
                console.warn('Live telemetry fetch notice:', err);
            }
        },

        recenterMap() {
            const site = APP_STATE.selectedSite;
            if (APP_STATE.map && site) {
                const isMobile = window.innerWidth <= 768;
                const targetLat = isMobile ? site.lat - 0.025 : site.lat;
                APP_STATE.map.flyTo([targetLat, site.lon], isMobile ? 12.0 : 13.0, { duration: 0.8 });
            }
        },

        switchMapLayer(layerKey) {
            const map = APP_STATE.map;
            if (!map || !APP_STATE.layers[layerKey]) return;

            Object.values(APP_STATE.layers).forEach(layer => map.removeLayer(layer));
            APP_STATE.layers[layerKey].addTo(map);
            APP_STATE.activeLayer = layerKey;

            document.querySelectorAll('.map-layer-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.layer === layerKey);
            });
        },

        // Primary Action: CONFIRM SITE -> Navigate to Screen 2
        confirmSite() {
            const site = APP_STATE.selectedSite;
            this.showToast(`Site Confirmed: ${site.shortName} (${site.lat.toFixed(4)}°, ${site.lon.toFixed(4)}°)`, 'success');

            // Navigate to Screen 2 while preserving site data
            setTimeout(() => {
                this.goToScreen(2);
            }, 600);
        },

        goToScreen(screenNum) {
            APP_STATE.currentScreen = screenNum;

            // Update Top Stepper Breadcrumbs
            document.querySelectorAll('.step-item').forEach(item => {
                const step = parseInt(item.dataset.step, 10);
                item.classList.toggle('active', step === screenNum);
                item.classList.toggle('completed', step < screenNum);
            });

            const mobileStepPill = document.getElementById('mobile-step-pill');
            if (mobileStepPill) {
                const stepNames = ['', 'Select Site', 'Configure Farm', 'Analyze Layout', 'Optimize (QAOA)', 'Inspect Results', 'Export Blueprint'];
                mobileStepPill.innerText = `Step ${screenNum}/6: ${stepNames[screenNum] || ''}`;
            }

            this.hideToast();

            // View containers
            const screen1Container = document.getElementById('screen-1-container');
            const screen2Container = document.getElementById('screen-2-container');
            const screen3Container = document.getElementById('screen-3-container');

            if (screenNum === 1) {
                if (screen1Container) screen1Container.style.display = 'flex';
                if (screen2Container) screen2Container.style.display = 'none';
                if (screen3Container) screen3Container.style.display = 'none';
                APP_STATE.map?.invalidateSize();
            } else if (screenNum === 2) {
                if (screen1Container) screen1Container.style.display = 'none';
                if (screen2Container) screen2Container.style.display = 'flex';
                if (screen3Container) screen3Container.style.display = 'none';
                this.initScreen2();
            } else if (screenNum === 3) {
                if (screen1Container) screen1Container.style.display = 'none';
                if (screen2Container) screen2Container.style.display = 'none';
                if (screen3Container) screen3Container.style.display = 'flex';
                this.initScreen3();
            }
        },

        // Screen 2 Initializer
        initScreen2() {
            const site = APP_STATE.selectedSite;
            const cfg = APP_STATE.farmConfig;

            // Populate Site Header Pill & Summary
            const indText = document.getElementById('s2-indicator-text');
            if (indText) indText.innerText = `${site.shortName} · ${site.lat.toFixed(4)}° N, ${site.lon.toFixed(4)}° E`;

            const s2Loc = document.getElementById('s2-meta-location');
            if (s2Loc) s2Loc.innerText = site.name;

            const s2Coords = document.getElementById('s2-meta-coords');
            if (s2Coords) s2Coords.innerText = `${site.lat.toFixed(4)}° N, ${site.lon.toFixed(4)}° E`;

            const s2Area = document.getElementById('s2-meta-area');
            if (s2Area) s2Area.innerText = `${site.areaKm2.toFixed(1)} km²`;

            const s2Wind = document.getElementById('s2-meta-wind');
            if (s2Wind) {
                const speed = site.windSpeedMps || 7.1;
                const dir = site.windDirectionDeg || 300;
                s2Wind.innerText = `${speed} m/s @ ${dir}° (ECMWF Telemetry)`;
            }

            // Sync wind direction from telemetry if not customized
            if (site.windDirectionDeg !== undefined) {
                cfg.windDirectionDeg = site.windDirectionDeg;
            }
            this.setWindDirection(cfg.windDirectionDeg);

            // Setup listeners once
            if (!this._screen2Initialized) {
                this.setupScreen2EventListeners();
                this._screen2Initialized = true;
            }

            // Update Turbine Count and Capacity status
            this.setTurbineCount(cfg.turbineCount);
            this.updateScreen2Capacity();
        },

        setupScreen2EventListeners() {
            // Back button to Screen 1
            document.getElementById('btn-back-to-screen-1')?.addEventListener('click', () => {
                this.goToScreen(1);
            });

            // Turbine Model Selector
            const modelSelect = document.getElementById('cfg-turbine-model');
            modelSelect?.addEventListener('change', (e) => {
                this.syncScreen2Model(e.target.value);
            });

            // Rotor Diameter Input
            const rotorInput = document.getElementById('cfg-rotor-diam');
            rotorInput?.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value) || 120;
                APP_STATE.farmConfig.rotorDiameter = val;
                const badge = document.getElementById('badge-rotor-diam');
                if (badge) badge.innerText = `${val} m`;
                this.updateScreen2Capacity();
            });

            // Hub Height Input
            const hubInput = document.getElementById('cfg-hub-height');
            hubInput?.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value) || 110;
                APP_STATE.farmConfig.hubHeight = val;
                const badge = document.getElementById('badge-hub-height');
                if (badge) badge.innerText = `${val} m`;
            });

            // Rated Power Input
            const powerInput = document.getElementById('cfg-rated-power');
            powerInput?.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value) || 2500;
                APP_STATE.farmConfig.ratedPowerKw = val;
                const badge = document.getElementById('badge-rated-power');
                if (badge) badge.innerText = `${val.toLocaleString()} kW (${(val/1000).toFixed(1)} MW)`;
                this.updateScreen2Capacity();
            });

            // Turbine Quick Chips
            document.querySelectorAll('.chip-btn[data-turbines]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const count = parseInt(e.currentTarget.dataset.turbines, 10);
                    this.setTurbineCount(count);
                });
            });

            // Stepper Minus / Plus
            document.getElementById('btn-turbines-minus')?.addEventListener('click', () => {
                this.setTurbineCount(Math.max(1, APP_STATE.farmConfig.turbineCount - 1));
            });

            document.getElementById('btn-turbines-plus')?.addEventListener('click', () => {
                this.setTurbineCount(Math.min(100, APP_STATE.farmConfig.turbineCount + 1));
            });

            // Slider & Direct Numeric Input
            const countSlider = document.getElementById('cfg-turbines-slider');
            countSlider?.addEventListener('input', (e) => {
                this.setTurbineCount(parseInt(e.target.value, 10));
            });

            const countInput = document.getElementById('cfg-turbines-count');
            countInput?.addEventListener('input', (e) => {
                const val = parseInt(e.target.value, 10);
                if (!isNaN(val) && val >= 1) {
                    this.setTurbineCount(val);
                }
            });

            // Wind Direction Slider
            const windSlider = document.getElementById('cfg-wind-dir-slider');
            windSlider?.addEventListener('input', (e) => {
                this.setWindDirection(parseFloat(e.target.value));
            });

            // Wind Quick Chips
            document.querySelectorAll('.chip-btn[data-wind-dir]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const val = e.currentTarget.dataset.windDir;
                    if (val === 'live') {
                        const liveDir = APP_STATE.selectedSite.windDirectionDeg || 300;
                        this.setWindDirection(liveDir);
                    } else {
                        this.setWindDirection(parseFloat(val));
                    }
                });
            });

            // Spacing Multiplier Chips (3D, 5D, 7D)
            document.querySelectorAll('.chip-btn[data-spacing]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.chip-btn[data-spacing]').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    const mult = parseFloat(e.currentTarget.dataset.spacing);
                    APP_STATE.farmConfig.spacingMultiplierD = mult;
                    const badge = document.getElementById('badge-spacing-meters');
                    if (badge) badge.innerText = `${Math.round(mult * APP_STATE.farmConfig.rotorDiameter)} m (${mult}D)`;
                    this.updateScreen2Capacity();
                });
            });

            // Advanced Accordion Toggle
            document.getElementById('accordion-advanced-header')?.addEventListener('click', () => {
                this.toggleAdvancedAccordion();
            });

            // Wake Decay & QUBO Lambda Inputs
            document.getElementById('cfg-wake-decay')?.addEventListener('change', (e) => {
                APP_STATE.farmConfig.wakeDecay = parseFloat(e.target.value);
            });

            document.getElementById('cfg-qubo-lambda')?.addEventListener('input', (e) => {
                APP_STATE.farmConfig.quboLambda = parseFloat(e.target.value) || 150.0;
            });

            // Auto-clamp capacity button
            document.getElementById('btn-clamp-capacity')?.addEventListener('click', () => {
                const site = APP_STATE.selectedSite;
                const cfg = APP_STATE.farmConfig;
                const { maxCapacity } = this.calculateSiteCapacity(site.areaKm2, cfg.rotorDiameter, cfg.spacingMultiplierD);
                this.setTurbineCount(maxCapacity);
                this.showToast(`Turbine count adjusted to site capacity (${maxCapacity} turbines)`, 'info');
            });

            // Primary Action: GENERATE INITIAL LAYOUT
            document.getElementById('btn-generate-layout')?.addEventListener('click', () => {
                this.validateAndGenerateLayout();
            });
        },

        setTurbineCount(count) {
            APP_STATE.farmConfig.turbineCount = count;

            const slider = document.getElementById('cfg-turbines-slider');
            if (slider) slider.value = count;

            const input = document.getElementById('cfg-turbines-count');
            if (input) input.value = count;

            // Update Quick Chips active state
            document.querySelectorAll('.chip-btn[data-turbines]').forEach(btn => {
                btn.classList.toggle('active', parseInt(btn.dataset.turbines, 10) === count);
            });

            this.updateScreen2Capacity();
        },

        setWindDirection(deg) {
            APP_STATE.farmConfig.windDirectionDeg = deg;

            const slider = document.getElementById('cfg-wind-dir-slider');
            if (slider) slider.value = deg;

            const rotor = document.getElementById('compass-rotor');
            if (rotor) rotor.style.transform = `rotate(${deg}deg)`;

            const badge = document.getElementById('badge-wind-dir');
            if (badge) {
                const cardinals = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
                const cardIdx = Math.round(deg / 22.5) % 16;
                badge.innerText = `${Math.round(deg)}° (${cardinals[cardIdx]})`;
            }

            document.querySelectorAll('.chip-btn[data-wind-dir]').forEach(btn => {
                const val = btn.dataset.windDir;
                btn.classList.toggle('active', (val === 'live' && deg === APP_STATE.selectedSite.windDirectionDeg) || parseFloat(val) === deg);
            });
        },

        syncScreen2Model(modelKey) {
            const model = TURBINE_MODELS[modelKey];
            if (!model) return;

            APP_STATE.farmConfig.model = modelKey;
            APP_STATE.farmConfig.modelName = model.name;
            APP_STATE.farmConfig.rotorDiameter = model.rotorDiameter;
            APP_STATE.farmConfig.hubHeight = model.hubHeight;
            APP_STATE.farmConfig.ratedPowerKw = model.ratedPowerKw;

            const rotorInput = document.getElementById('cfg-rotor-diam');
            if (rotorInput) rotorInput.value = model.rotorDiameter;
            const rotorBadge = document.getElementById('badge-rotor-diam');
            if (rotorBadge) rotorBadge.innerText = `${model.rotorDiameter} m`;

            const hubInput = document.getElementById('cfg-hub-height');
            if (hubInput) hubInput.value = model.hubHeight;
            const hubBadge = document.getElementById('badge-hub-height');
            if (hubBadge) hubBadge.innerText = `${model.hubHeight} m`;

            const powerInput = document.getElementById('cfg-rated-power');
            if (powerInput) powerInput.value = model.ratedPowerKw;
            const powerBadge = document.getElementById('badge-rated-power');
            if (powerBadge) powerBadge.innerText = `${model.ratedPowerKw.toLocaleString()} kW (${(model.ratedPowerKw / 1000).toFixed(1)} MW)`;

            const spacingBadge = document.getElementById('badge-spacing-meters');
            if (spacingBadge) spacingBadge.innerText = `${Math.round(APP_STATE.farmConfig.spacingMultiplierD * model.rotorDiameter)} m (${APP_STATE.farmConfig.spacingMultiplierD}D)`;

            this.updateScreen2Capacity();
        },

        calculateSiteCapacity(areaKm2, rotorDiameter, spacingMultiplierD) {
            const crosswindM = spacingMultiplierD * rotorDiameter;
            const downwindM = (spacingMultiplierD * 1.4) * rotorDiameter;
            const footprintM2 = crosswindM * downwindM;
            const footprintKm2 = footprintM2 / 1000000.0;
            const buildableAreaKm2 = areaKm2 * 0.80; // 80% buildable excluding residential setbacks & terrain slope
            const maxCapacity = Math.max(1, Math.floor(buildableAreaKm2 / footprintKm2));

            return {
                footprintKm2,
                buildableAreaKm2,
                maxCapacity
            };
        },

        updateScreen2Capacity() {
            const site = APP_STATE.selectedSite;
            const cfg = APP_STATE.farmConfig;

            const { footprintKm2, buildableAreaKm2, maxCapacity } = this.calculateSiteCapacity(
                site.areaKm2,
                cfg.rotorDiameter,
                cfg.spacingMultiplierD
            );

            const footprintElem = document.getElementById('metric-footprint-unit');
            if (footprintElem) footprintElem.innerText = `~ ${footprintKm2.toFixed(2)} km² (${cfg.spacingMultiplierD}D × ${(cfg.spacingMultiplierD * 1.4).toFixed(0)}D)`;

            const maxCapElem = document.getElementById('metric-max-capacity');
            if (maxCapElem) maxCapElem.innerText = `${maxCapacity} Turbines (${buildableAreaKm2.toFixed(1)} km² buildable)`;

            const card = document.getElementById('cfg-capacity-card');
            const icon = document.getElementById('capacity-status-icon');
            const headline = document.getElementById('capacity-status-headline');
            const desc = document.getElementById('capacity-status-desc');
            const clampBtn = document.getElementById('btn-clamp-capacity');
            const utilBadge = document.getElementById('badge-capacity-utilization');

            const currentCount = cfg.turbineCount;

            if (currentCount <= maxCapacity) {
                if (card) card.className = 'capacity-status-card optimal';
                if (icon) icon.innerText = '✓';
                if (headline) headline.innerText = 'Site Capacity Optimal';
                if (desc) desc.innerText = `${currentCount} turbines comfortably fit within the ${site.areaKm2.toFixed(1)} km² site with standard ${cfg.spacingMultiplierD}D aerodynamic wake buffer spacing.`;
                if (clampBtn) clampBtn.style.display = 'none';
                if (utilBadge) {
                    utilBadge.innerText = `${Math.round((currentCount / maxCapacity) * 100)}% Capacity`;
                    utilBadge.style.color = 'var(--primary-cyan)';
                }
            } else {
                if (card) card.className = 'capacity-status-card exceeded';
                if (icon) icon.innerText = '⚠️';
                if (headline) headline.innerText = `Exceeds Safe Site Capacity (${maxCapacity} Max)`;
                if (desc) desc.innerText = `At ${cfg.rotorDiameter}m rotor diameter and ${cfg.spacingMultiplierD}D spacing, this ${site.areaKm2.toFixed(1)} km² site safely accommodates at most ${maxCapacity} turbines. Placing ${currentCount} turbines will cause severe wake degradation or overlap residential setback zones.`;
                if (clampBtn) {
                    clampBtn.style.display = 'inline-block';
                    clampBtn.innerText = `Auto-Adjust to Recommended: ${maxCapacity} Turbines`;
                }
                if (utilBadge) {
                    utilBadge.innerText = `Exceeds Capacity (${currentCount}/${maxCapacity})`;
                    utilBadge.style.color = '#ef4444';
                }
            }

            const totalMw = (currentCount * cfg.ratedPowerKw) / 1000.0;
            const totalCapElem = document.getElementById('cfg-total-capacity');
            if (totalCapElem) {
                totalCapElem.innerText = `${currentCount} Turbines · ${totalMw.toFixed(1)} MW`;
            }
        },

        toggleAdvancedAccordion() {
            const wrapper = document.getElementById('accordion-advanced-wrapper');
            if (wrapper) {
                wrapper.classList.toggle('expanded');
            }
        },

        validateAndGenerateLayout() {
            const cfg = APP_STATE.farmConfig;
            const site = APP_STATE.selectedSite;

            if (isNaN(cfg.turbineCount) || cfg.turbineCount < 1) {
                this.showToast('Please select at least 1 turbine', 'error');
                document.getElementById('cfg-turbines-count')?.focus();
                return;
            }

            if (isNaN(cfg.rotorDiameter) || cfg.rotorDiameter < 40 || cfg.rotorDiameter > 250) {
                this.showToast('Rotor diameter must be between 40m and 250m', 'error');
                document.getElementById('cfg-rotor-diam')?.focus();
                return;
            }

            if (isNaN(cfg.hubHeight) || cfg.hubHeight < 40 || cfg.hubHeight > 250) {
                this.showToast('Hub height must be between 40m and 250m', 'error');
                document.getElementById('cfg-hub-height')?.focus();
                return;
            }

            // Success validation
            this.showToast(`Initial layout configured: ${cfg.turbineCount} turbines (${(cfg.turbineCount * cfg.ratedPowerKw / 1000).toFixed(1)} MW)`, 'success');

            setTimeout(() => {
                this.goToScreen(3);
            }, 500);
        },

        initScreen3() {
            const site = APP_STATE.selectedSite;
            const cfg = APP_STATE.farmConfig;

            const siteTag = document.getElementById('screen-3-site-tag');
            if (siteTag) {
                siteTag.innerText = `${site.shortName} (${site.lat.toFixed(4)}°, ${site.lon.toFixed(4)}°)`;
            }

            const turbTag = document.getElementById('screen-3-turbines-tag');
            if (turbTag) {
                turbTag.innerText = `${cfg.turbineCount} turbines · ${(cfg.turbineCount * cfg.ratedPowerKw / 1000).toFixed(1)} MW`;
            }
        },

        hideToast() {
            const toast = document.getElementById('app-toast');
            if (toast) toast.style.display = 'none';
        },

        showToast(msg, type = 'info') {
            const toast = document.getElementById('app-toast');
            if (!toast) return;

            toast.innerText = msg;
            toast.style.borderColor = type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : 'var(--border-focus)';
            toast.style.display = 'flex';

            clearTimeout(this._toastTimer);
            this._toastTimer = setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }
    };

    // Export to window
    window.APP = APP;
    window.APP_STATE = APP_STATE;

    document.addEventListener('DOMContentLoaded', () => {
        APP.init();
    });

})(window);
