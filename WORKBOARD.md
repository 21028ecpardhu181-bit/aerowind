# WORKBOARD.md — AeroQuantum Wind Farm Production Tasks

## Assigned Agent: Antigravity

### Active Task: Real vs Mockup Data Audit, 3D Globe Yellow Lights Fix, Atmospheric Wind & Telemetry Streamlines, Non-Overlapping 3D Controls, and Arbitrary Turbine Capacity (up to 50)
- **Branch**: `feature/real-data-3d-globe-turbine-fix`
- **Files Owned**:
  - `src/components/gis/CesiumGlobeView.tsx`
  - `src/utils/geometry.ts`
  - `src/services/api.ts`
  - `src/App.tsx`
  - `backend/app/schemas.py`
  - `core/wsqaoa.py`
  - `backend/app/geo_engine.py`
  - `backend/app/api/geo.py`

### Objectives & Completed Fixes:
1. **Real vs Mockup Data Audit Conducted**:
   - Live external APIs confirmed active: Copernicus DEM GLO-30 / SRTM (via Open-Meteo elevation), Open-Meteo 100m/80m/10m atmospheric weather, ISRIC SoilGrids v2.0 (bulk density, pH, clay/sand/silt), OpenStreetMap Overpass (physical buildings, powerlines, roads, waterways setbacks), OpenStreetMap Nominatim (cadastral village polygons), and NREL FLORIS 4.x / Jensen kinematic wake engine.
   - Replaced mathematical sine formula in `/api/geo/wind-resource` with real downscaled 100m hub-height wind telemetry.
2. **3D Globe "Yellow Lights Going Up" Bug Fixed**:
   - Root cause: Cesium `cylinder` entities instantiated without orientation quaternion defaulted along the normal/Z-axis (straight up into the sky).
   - Solution: Replaced cylinders with horizontal aerodynamic wake footprints draped onto the terrain surface (`HeightReference.CLAMP_TO_GROUND`) expanding downwind at $(windDirectionDeg + 180)^\circ$ with realistic deficit gradients.
3. **Wind & SCADA Telemetry Data Flow Streamlines**:
   - Implemented dynamic atmospheric wind flow streamlines traversing across the wind farm aligned with the wind direction vector using `PolylineGlowMaterialProperty`.
   - Implemented inter-turbine electrical and SCADA telemetry collection grid lines pulsing with golden energy toward collector nodes.
   - Added interactive toggle buttons for both streamlines and wake footprints in the 3D dock.
4. **3D Globe Controls Alignment & Click Conflicts Fixed**:
   - Relocated 3D controls to `top-3 right-3 md:top-4 md:right-4 z-30` in an Apple Liquid Glass dock with `e.stopPropagation()` on all click handlers, completely eliminating collision with Screen 1 search bar and Screen 5 headers.
5. **Turbine Clamping Fixed (Up to 50 Turbines)**:
   - Root cause: Pydantic schemas hard-clamped `K <= 8`, and geometry generators had restrictive spacing that dropped turbines.
   - Fix: Expanded `K` up to 50 in `backend/app/schemas.py`, `src/services/api.ts`, and `src/App.tsx`. Added continuous QP relaxation in `core/wsqaoa.py` for $K > 8$. Upgraded `src/utils/geometry.ts` and `backend/app/geo_engine.py` with multi-scale interior sampling and progressive spacing relaxation so 100% of requested turbines are always placed strictly within boundary.
6. **Verification**:
   - `npm run build`: PASS (clean build, 0 TypeScript errors).
   - `tests/verify_project_dashboards_accuracy.py`: PASS (exit code 0).
   - `tests/verify_liquid_soil_village.py`: PASS (exit code 0).
   - Zero emojis verified across all modified files.

