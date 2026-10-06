# WORKBOARD.md — AeroQuantum Wind Farm Production Tasks

## Assigned Agent: Antigravity

### Status: Completed (Verified with Playwright & Pytest)
- **Branch**: `feature/real-boundaries-setbacks-turbine-yaw`
- **Files Owned**:
  - `src/services/api.ts`
  - `backend/app/gis/village_boundary_client.py`
  - `backend/app/gis/overpass_client.py`
  - `backend/app/geo_engine.py`
  - `src/utils/geometry.ts`
  - `src/components/gis/CesiumGlobeView.tsx`
  - `src/components/workflow/Screen5Inspect.tsx`
  - `WORKBOARD.md`

### Completed Objectives:
1. Authentic Administrative Boundaries for Every Village & City:
   - Purged hardcoded static cadastre mock (`BOMMURU_AUTHENTIC_CADASTRE`) and static radius hijacking in `api.ts`.
   - Implemented MultiPolygon sector resolution: when resolving administrative relations/counties, the algorithm ray-casts into individual polygon rings to select the exact ring enclosing the query coordinates (e.g., Bommuru resolves the southern sector of 45.67 km², Torredu resolves the northern sector of 49.84 km², Kovvur resolves its authentic 119.38 km² boundary).
   - Parent administrative hierarchy resolution: when a village/town node is queried, resolves its enclosing mandal/taluk administrative relation via Nominatim.
   - Verified across Bommuru (45.7 km²), Torredu (49.8 km²), Kovvur (119.4 km²), Kayathar (16.2 km²), and Jaisalmer (38,417 km²).

2. Strict Settlement & House Setback Enforcement (>= 500m - 800m):
   - Overpass client optimized with lightweight settlement queries (`node["place"~"city|town|suburb|village|hamlet|isolated_dwelling"]` and `way/relation["landuse"~"residential|commercial|industrial|construction"]`), eliminating server timeouts.
   - Enforced mandatory 500m-800m setback around village centers, settlement cores, and residential houses across candidate generation (`geo_engine.py`) and client candidate placement (`geometry.ts`).
   - Zero turbines placed in village settlements or among houses.

3. Wind Turbine Yaw Orientation & Engineering Telemetry in 3D Cesium:
   - Calibrated mathematical heading formula: accounting for Cesium glTF axis correction (`glTF Z -> Cesium East / +X`), heading is set to `(windDirectionDeg - 90 + 360) % 360`, guaranteeing that 3D glTF turbine rotor discs face strictly UPWIND into the oncoming meteorological wind vector.
   - Removed duplicate overlapping procedural nacelle box entity to eliminate visual clipping and z-fighting with the authentic 3D glTF nacelle and spinner cone.
   - Added floating Apple Liquid Glass Wind Telemetry and Turbine Yaw Compass badge directly on the Cesium 3D canvas (`#cesium-wind-telemetry-badge`) displaying:
     - Real-time 360-degree animated compass rose with North reference
     - Meteorological wind speed (m/s) and bearing (deg)
     - Active turbine yaw alignment status (`Rotor Yaw: X deg · Upwind Aligned · IEC 61400`)
     - Responsive mobile layout at `top-36` with zero overlap against camera controls.

4. Verification & Quality Gates:
   - `npm run build`: PASS (Vite production build clean, 1,621 modules transformed, 44.14s).
   - `pytest tests/`: PASS (54 of 54 tests passing in 9.01s).
   - Playwright end-to-end tests: PASS across Desktop (1280px) and Mobile (390px).
   - Strictly 0 emojis in all code, UI, and commits.


