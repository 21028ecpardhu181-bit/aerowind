# PHASE 7 ENGINEERING REPORT: CESIUM 3D TRUTHFUL VISUALIZATION & OPTIMIZED LAYOUT

**System**: AeroQuantum-Wind Engine  
**Module**: Phase 7 — Engineering-Truthful Cesium 3D Visualization & Layout Engine  
**Date**: October 2026  
**Status**: VERIFIED & PRODUCTION READY  
**Branch**: `feature/phase-7-cesium-truthful-visualization`  

---

## 1. Executive Summary

Phase 7 establishes complete geometric and physical fidelity between the backend engineering engines (Phase 2 site boundaries, Phase 3 buildability masks, Phase 4 engineering candidates, Phase 5 FLORIS wake physics, and Phase 6 QAOA optimization) and the frontend 3D globe visualization in CesiumJS.

Prior to Phase 7, frontend visualizations carried latent risks of visual fabrication: fallback circular boundaries, arbitrary 5% wake expansion rates, unscaled generic turbine geometries, and disconnected camera projections. Phase 7 eliminates all visual fabrication and enforces a strict architectural invariant:

> **Core Principle**: The frontend must visualize backend engineering truth. It must never independently generate, move, optimize, validate, or invent turbine coordinates, boundaries, suitability, wake geometry, wind resource, or optimization results.

All visual entities—concession perimeters, interior exclusion holes, candidate pads, rejected candidate markers, monopile towers, rotor swept disks, and aerodynamic wake cones—are anchored directly to geodetic WGS84 coordinates and authenticated Copernicus DEM elevations.

---

## 2. Real Geographic Coordinates & Camera Invariance

### 2.1 Backend Geodetic Coordinate Anchoring
Every turbine and candidate rendered in Cesium is parameterized strictly by:
- `lat` (WGS84 latitude, 6-decimal precision)
- `lon` (WGS84 longitude, 6-decimal precision)
- `elevation_m` (Ground elevation ASL from Copernicus DEM GLO-90 composite)
- `utm_easting_m`, `utm_northing_m` (Projected metric coordinates in EPSG:32644)

In `src/components/gis/CesiumGlobeView.tsx`:
```typescript
const cartographic = Cesium.Cartographic.fromDegrees(t.lon, t.lat, groundHeight);
const surfacePos = viewer.scene.globe.ellipsoid.cartographicToCartesian(cartographic);
```
Turbines remain rigidly anchored to Earth ground coordinates during all camera maneuvers:
- Orbital rotation (heading: 0 deg to 360 deg)
- Camera pitch (-90 deg nadir to 0 deg horizon)
- Deep zoom (10 m close-up inspection to 50 km regional synoptic view)
- Viewport resize (mobile 390px to desktop 1280px+)

### 2.2 Rejection of Screen and Viewport Synthetics
- **Zero Screen Coordinates**: No turbine or polygon uses 2D pixel coordinates `(x, y)` or normalized device coordinates.
- **Zero Synthetic Offsets**: No random jitter, spiraling, or camera-relative billboard displacement.
- **Zero Fallback Geometry**: If turbine coordinates are missing or empty, the viewer displays a dedicated constrained site status banner rather than generating placeholder positions.

---

## 3. Real Terrain & Elevation Anchoring

### 3.1 Copernicus DEM GLO-90 Composite
In Phase 3 and Phase 4, the engineering backend establishes site elevation via the Open-Meteo Copernicus DEM GLO-90 composite (30m/90m resolution). The frontend Cesium engine consumes this exact ground elevation:
1. `t.elevation_m`: Primary elevation per turbine returned by the engineering candidate generator.
2. `siteElevationM`: Verified concession baseline elevation fallback (40.0 m ASL for Bommuru).
3. `Cesium.sampleTerrainMostDetailed`: Terrain sampling across the Cesium World Terrain asset pipeline.

### 3.2 Vertical Tower Alignment & Clamping
The turbine structure is vertically stacked from ground level:
- **Foundation Pad**: Clamped to `groundHeight` (`heightReference: Cesium.HeightReference.CLAMP_TO_GROUND`).
- **Tower Monopile**: Extends from `groundHeight` to `groundHeight + hubHeight` ($H$).
- **Nacelle**: Anchored at `groundHeight + hubHeight`.
- **Rotor Center**: Positioned at hub height with rotor diameter $D$.
- **Rotor Tip Clearance**: Swept lowest blade tip clears ground at `groundHeight + (H - 0.5 * D)` ($110 - 60 = 50\text{ m}$ for GE 2.5-120).

---

## 4. Authoritative Site Boundaries & Hole Handling

### 4.1 Boundary Geometry Ingestion
The boundary rendered on the globe is parsed dynamically from the authoritative backend search envelope (`site.boundary`). The parser handles:
- Standard GeoJSON `Polygon` and `MultiPolygon`
- GeoJSON `FeatureCollection` and `Feature`
- Raw coordinate coordinate arrays `[lon, lat]` or `[lat, lon]` with geodetic latitude bounds detection ($-90 \le \text{lat} \le 90$)

### 4.2 Polygon Interior Donut Holes
Real wind concession boundaries contain interior exclusion areas: residential settlements (500m setback), water bodies (50m riparian margin), and steep slopes ($>15^\circ$). Cesium renders these using `Cesium.PolygonHierarchy`:
- **Outer Shell**: Gold/amber outline (`#FFD21F`, alpha 0.9, dashed polyline) with translucent gold fill (alpha 0.08).
- **Interior Holes**: Crimson exclusion borders (`#EF4444`, alpha 0.8) with translucent red fill (alpha 0.15) and yellow hazard warning icon badges.

### 4.3 Elimination of Synthetic Circular Fallbacks
All fallback 32-point circular boundary loops were permanently excised from `CesiumGlobeView.tsx`. When boundary data is not provided, the renderer displays an explicit `BOUNDARY_UNAVAILABLE` advisory badge and omits perimeter extrusion.

---

## 5. Candidate Pool vs Final Optimized Layout Distinction

The Cesium globe visually differentiates three distinct classes of positions:

| Entity Class | Visual Representation | Telemetry / Interaction |
| :--- | :--- | :--- |
| **Selected QAOA Layout** | Full 3D structural turbine (monopile tower, nacelle, rotor disk, wake cone) | Green active badge, net AEP, effective wind speed, wake deficit |
| **Feasible Candidates (Unselected)** | Slate-500 concentric ring pad with center locator pip | Gray circle, candidate ID, indicates viable alternative positions |
| **Rejected / Excluded Candidates** | Crimson warning ring with exclamation glyph | Red marker, hover tooltip displaying exact rejection reason (e.g. slope, setback) |

Toggling the **Candidates** dock button allows engineers to inspect the full candidate search space and verify why QAOA selected specific nodes over others.

---

## 6. Authentic Turbine Specifications & Aerodynamic Wake Cones

### 6.1 Real Turbine Catalogue Fidelity
Frontend dimensional scaling uses authentic specifications directly from `TURBINE_CATALOG`:

| Parameter | GE 2.5-120 | Vestas V110-2.0 | NREL 5MW | IEA 15MW | SG 3.4-132 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Rotor Diameter ($D$)** | 120.0 m | 110.0 m | 126.0 m | 240.0 m | 132.0 m |
| **Hub Height ($H$)** | 110.0 m | 95.0 m | 90.0 m | 150.0 m | 114.0 m |
| **Rated Power ($P_{\text{rated}}$)** | 2,500 kW | 2,000 kW | 5,000 kW | 15,000 kW | 3,400 kW |
| **Tower Top Radius** | 2.1 m | 1.9 m | 2.2 m | 4.0 m | 2.3 m |
| **Tower Base Radius** | 3.2 m | 2.9 m | 3.3 m | 6.0 m | 3.5 m |
| **Tip Ground Clearance** | 50.0 m | 40.0 m | 27.0 m | 30.0 m | 48.0 m |

All monopile cylinders, foundation pads, and glTF models scale proportionally to $H$ and $D$. Zero generic or unscaled assets are rendered.

### 6.2 Directional & Yaw Alignment Conventions
The single backend source of truth (`geometry_conventions.py`) dictates all spatial orientations:
1. `wind_from_deg`: Direction wind arrives FROM (meteorological convention, e.g. 245 deg).
2. `wind_to_deg`: Downwind propagation direction:
   $$\text{wind\_to\_deg} = (\text{wind\_from\_deg} + 180) \pmod{360}$$
3. `turbine_yaw_deg`: Upwind HAWT alignment facing directly into incoming flow:
   $$\text{turbine\_yaw\_deg} = \text{wind\_from\_deg} \pmod{360}$$
4. `cesium_heading_deg`: GlTF asset rotation with Cesium eastward origin:
   $$\text{cesium\_heading\_deg} = (\text{wind\_from\_deg} - 90 + 360) \pmod{360}$$

### 6.3 FLORIS Bastankhah Wake Geometry
Aerodynamic wake envelopes rendered downwind use the validated NREL FLORIS Bastankhah & Porte-Agel Gaussian wake expansion parameter:
$$k^* = 0.04$$
$$r(x) = \frac{D}{2} + k^* \cdot x = \frac{120}{2} + 0.04 \cdot x$$

At downstream distance $x = 5D = 600\text{ m}$:
$$r(600) = 60 + 0.04 \times 600 = 84.0\text{ m} \quad (\text{diameter } 168.0\text{ m})$$

At downstream distance $x = 10D = 1200\text{ m}$:
$$r(1200) = 60 + 0.04 \times 1200 = 108.0\text{ m} \quad (\text{diameter } 216.0\text{ m})$$

The wake cone extends from hub height downwind along `wind_to_deg` to a distance of $10D$. Previous hardcoded $k^* = 0.05$ approximations have been removed and replaced with $k^* = 0.04$.

### 6.4 Truthful Wake Deficit Coloring
Wake cones are shaded strictly according to backend-computed `wake_deficit_pct`:
- Deficit $< 3.0\%$: Cyan / emerald translucent gradient (`#06B6D4` / `#10B981`)
- Deficit $3.0\% - 8.0\%$: Amber warning gradient (`#F59E0B`)
- Deficit $> 8.0\%$: Crimson heavy loss gradient (`#EF4444`)
- Missing / Null: Slate neutral outline labeled `Deficit: UNCOMPUTED` (zero visual fabrication).

---

## 7. Before / After Comparison Contract

Screen 5 incorporates an interactive Before/After segmented control:
- **Baseline Layout (Before)**: Renders the un-optimized initial layout (`initial_turbines`) generated by Phase 4 candidate generation.
- **QAOA Layout (After)**: Renders the winning layout (`optimized_turbines`) selected by the QAOA variational optimizer and validated by exact FLORIS physics.
- **Synchronized Telemetry**: The inspector card, comparison table, and telemetry badge update dynamically:
  - Net AEP (e.g. 44.5 GWh baseline vs 48.3 GWh optimized)
  - Wake Loss (e.g. 8.8% baseline vs 3.7% optimized)
  - Net Gain (e.g. +8.5% improvement)
- **Zero Coordinate Interpolation**: Toggling switches between the exact discrete geodetic schedules; turbines do not glide, interpolate, or invent intermediate coordinates.

---

## 8. Verification & Test Suite Evidence

### 8.1 Unit & Integration Test Suite (`tests/test_cesium_visualization_truth.py`)
All 6 tests passed in 27.97s:
1. `test_wind_and_gltf_yaw_conventions`: Validates upwind yaw, downwind wake vector, and glTF heading formulas across all cardinal directions.
2. `test_wake_expansion_geometry_parameter`: Enforces $k^* = 0.04$ FLORIS expansion rate in TypeScript and Python.
3. `test_authentic_turbine_catalogue_dimensions`: Verifies all 5 catalogue models match authentic rotor diameters, hub heights, and rated power.
4. `test_no_synthetic_circle_boundary_or_fallback`: Confirms absence of synthetic circular fallback geometry in codebase.
5. `test_qaoa_physical_winner_pipeline_integration`: Validates end-to-end pipeline wiring from QAOA winner coordinates to Cesium visualization.
6. `test_zero_emojis_in_phase7_files`: Confirms strictly zero Unicode emoji symbols across all Phase 7 files.

### 8.2 Playwright UI End-to-End Test (`tests/verify_complete_flow.py`)
Full 6-screen workflow verified at both mobile (390 x 844) and desktop (1280 x 800):
- Screen 1: Site confirmed (Bommuru 3D Globe + 2D satellite)
- Screen 2: Configuration set (6 turbines, GE 2.5-120, gravity base)
- Screen 3: Initial layout generated (12 candidate positions, 8.8% wake loss)
- Screen 4: QAOA simulation converged (Aer simulator, best AEP: 48.3 GWh/yr)
- Screen 5: 3D Cesium globe loaded, 3D turbines rendered, wake cones displayed, Before/After toggled, inspector stepped
- Screen 6: Blueprint generated with 6 geodetic records, GeoJSON/CSV/JSON export triggers verified
- Result: **ALL 6 SCREENS VERIFIED SUCCESSFULLY! END-TO-END PIPELINE READY.**

### 8.3 Screen 5 Dedicated Playwright Suite (`tests/verify_screen5_ui.py`)
Mobile (390px) and desktop (1280px) test passed:
- Saved mobile map screenshot: `docs/ui-screenshots/screen5-mobile-390px.png`
- Saved mobile inspector screenshot: `docs/ui-screenshots/screen5-mobile-inspector-390px.png`
- Saved desktop screenshot: `docs/ui-screenshots/screen5-desktop-1280px.png`

### 8.4 Full Repository Regression Suite
- Full test suite: **190 of 190 tests passed** in 3m 37s (`pytest tests/ -v`).
- Frontend production build: Clean compile in 1m 8s (`npm run build`).

---

## 9. Conclusion

Phase 7 successfully delivers engineering-truthful 3D visualization. The Cesium globe now acts as an authentic visual twin of the backend simulation and optimization models, ensuring that developers, wind engineers, and stakeholders inspect the true physical performance of the optimized layout.
