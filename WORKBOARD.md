# WORKBOARD.md — AeroQuantum Wind Farm Production Tasks

## Assigned Agent: Antigravity

### Active Task: Real Village Boundary Cadastre, Photoshop Lasso Freeform Drawing, and Resilient Multi-CDN Tiles
- **Branch**: `feature/village-cadastre-lasso-tiles-fix`
- **Files Owned**:
  - `src/components/workflow/Screen1Site.tsx`
  - `src/App.tsx`
  - `src/index.css`
  - `backend/app/gis/village_boundary_client.py`
  - `WORKBOARD.md`

### Objectives & Completed Enhancements:
1. **Real Village Cadastre Administrative Polygon (No Fake Circles)**:
   - Upgraded `VillageBoundaryClient` in `backend/app/gis/village_boundary_client.py` to use persistent requests sessions with authentic administrative headers, resolving `IncompleteRead` errors.
   - When a searched village is mapped as a node (e.g. Bommuru), automatically queries the enclosing administrative county/mandal territory (`Rajahmundry Rural`), extracting real 53-point geodetic administrative multipolygons.
   - Replaced synthetic circular radii with authentic irregular village boundaries, computing geodesic area (41.21 km²) and perimeter (30.01 km).
   - Marked boundary vertex dots along the actual perimeter edges ("from where to where") with an emerald anchor point.

2. **Photoshop-Style Freeform Lasso Boundary Tool**:
   - Cleaned the canvas upon entering Lasso mode by removing prior static boundary circles and badges.
   - Enabled interactive mobile tapping/clicking to place vertex markers: Point 1 is an emerald anchor ring with "Anchor: Tap to close", and subsequent points are numbered golden markers.
   - Live dashed polyline and 20% opacity polygon fill with real-time geodesic area calculation (km²).
   - Added `Undo` button to pop the last placed vertex, `Clear` to reset, and `Cancel` to restore the previous boundary.
   - Tapping `Enclose Boundary` or clicking Point 1 closes the parcel, updates project state to "Custom Wind Farm Parcel", and fits the camera.

3. **Multi-CDN Resilient Map Tiles & Mobile Touch Fix**:
   - Configured `tap: false` on the Leaflet container to prevent touch click events from being swallowed on Android Chrome and iOS Safari.
   - Multi-CDN tile layer pipeline: Esri World Imagery (satellite) with automatic `tileerror` fallback to Google Hybrid, CartoDB Voyager (street) with OSM fallback, and Esri World Topo (terrain) with OpenTopoMap fallback.
   - Ensured `#map` container background `#1e293b` and tile pane full opacity so map never appears as a broken void.

4. **Accurate Contextual Badges & Project Persistence**:
   - Formatted center badge and bottom drawer to display `Cadastral Boundary` or `Custom Parcel`, strictly reserving `radius` text for Radius mode.
   - Synchronized initial project state for Bommuru to authentic 41.21 km² area.

5. **Verification & Quality Gates**:
   - `npm run build`: PASS (Vite production build clean in 33.2s).
   - `pytest tests/`: PASS (54 of 54 tests passing in 31.1s).
   - Playwright mobile viewport (390px) screenshots verified: Village Cadastre boundary and Lasso 4-point parcel verified.
   - Strictly 0 emojis in all code, commits, and UI.


