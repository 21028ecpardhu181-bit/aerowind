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
            turbineCount: 4,
            windAngle: 270.0,
            rotorDiameter: 120.0
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

            APP_STATE.sitePolygon = L.polygon(vertices, {
                color: '#3b82f6',
                weight: 2,
                opacity: 0.9,
                fillColor: '#2563eb',
                fillOpacity: 0.18,
                smoothFactor: 1
            }).addTo(map);

            // Center Area Badge
            const badgeIcon = L.divIcon({
                className: 'badge-div-wrapper',
                html: `<div class="selected-area-badge">Selected Area<br><strong>${areaKm2.toFixed(1)} km²</strong></div>`,
                iconSize: [110, 40],
                iconAnchor: [55, 20]
            });
            APP_STATE.areaBadgeMarker = L.marker([lat, lon], { icon: badgeIcon }).addTo(map);

            // Location Label on map
            const nameIcon = L.divIcon({
                className: 'label-div-wrapper',
                html: `<div class="location-anchor-tag">${APP_STATE.selectedSite.shortName}</div>`,
                iconSize: [120, 24],
                iconAnchor: [60, -20]
            });
            APP_STATE.locationLabelMarker = L.marker([lat - latDelta * 0.75, lon - lonDelta * 0.2], { icon: nameIcon }).addTo(map);
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

        updateUIWithSite(site) {
            APP_STATE.selectedSite = site;

            // Update inputs
            const searchField = document.getElementById('search-input-field');
            if (searchField) searchField.value = site.name;
            const mapSearchField = document.getElementById('map-search-input');
            if (mapSearchField) mapSearchField.value = site.name;

            // Update Details Table
            document.getElementById('meta-location-name').innerText = site.name;
            document.getElementById('meta-latitude').innerText = `${site.lat.toFixed(4)}° N`;
            document.getElementById('meta-longitude').innerText = `${site.lon.toFixed(4)}° E`;
            document.getElementById('meta-area').innerText = `${site.areaKm2.toFixed(1)} km²`;
            document.getElementById('meta-elevation').innerText = `${site.elevationM} m`;
            document.getElementById('meta-terrain').innerText = site.terrainType;
            document.getElementById('meta-coast').innerText = `${site.distanceToCoastKm} km`;
            document.getElementById('meta-landuse').innerText = site.landUse;

            // Wind Resource
            document.getElementById('meta-wind-speed').innerText = `${site.windSpeedMps} m/s`;
            document.getElementById('meta-wind-density').innerText = `~ ${site.windPowerDensity} W/m²`;

            // Fly map & redraw polygon
            if (APP_STATE.map) {
                const isMobile = window.innerWidth <= 768;
                const targetLat = isMobile ? site.lat - 0.025 : site.lat;
                APP_STATE.map.flyTo([targetLat, site.lon], isMobile ? 11.8 : 12.5, { duration: 1.2 });
                this.drawSitePolygon(site.lat, site.lon, site.areaKm2);
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

            // If navigating to Screen 2, update Screen 2 view
            const screen1Container = document.getElementById('screen-1-container');
            const screen2Container = document.getElementById('screen-2-container');

            if (screenNum === 2) {
                if (screen1Container) screen1Container.style.display = 'none';
                if (screen2Container) {
                    screen2Container.style.display = 'flex';
                    this.initScreen2();
                }
            } else if (screenNum === 1) {
                if (screen1Container) screen1Container.style.display = 'flex';
                if (screen2Container) screen2Container.style.display = 'none';
                APP_STATE.map?.invalidateSize();
            }
        },

        // Screen 2 Placeholder initializer (preserved for Screen 2 implementation)
        initScreen2() {
            const site = APP_STATE.selectedSite;
            const screen2SiteTag = document.getElementById('screen-2-site-tag');
            if (screen2SiteTag) {
                screen2SiteTag.innerText = `${site.shortName} (${site.lat.toFixed(4)}° N, ${site.lon.toFixed(4)}° E)`;
            }
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
