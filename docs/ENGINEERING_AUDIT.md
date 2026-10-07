# AeroQuantum-Wind — Engineering Audit (Phase 0)

**Date**: 2026-10-06  
**Auditor**: Senior Wind-Farm GIS & Computational Optimization Engineer (10+ Years Experience)  
**Target Repository**: `aeroquantum-wind-hackathon-prototype`  
**Evaluation Scope**: Full-stack audit across GIS ingestion, aerodynamic wake modelling, QUBO formulation, WS-QAOA quantum execution, CesiumJS 3D digital twin rendering, API schemas, and data provenance.

---

## 1. Executive Summary

AeroQuantum-Wind is an ambitious micro-siting platform engineered to combine satellite geospatial constraints with hybrid quantum combinatorial optimization (WS-QAOA) and 3D globe visualization. 

During our engineering audit, we traced live runtime data flow from location geocoding down to Hamiltonian construction, solver execution, and WebGL rendering. We identified key architectural strengths—such as a vectorized Jensen wake model, NREL FLORIS 4.x integration, authentic Copernicus DEM GLO-30 querying, and an authentic Open-Meteo atmospheric telemetry pipeline. However, we also identified critical points where engineering fidelity degrades:

1. **Dual Routing & Endpoint Drift**: The backend contains two competing optimization endpoints: `POST /api/optimize` (in `optimize.py`, backed by Qiskit WS-QAOA and continuous relaxation) and `POST /api/qaoa-optimize` (in `layout.py`, which delegates to `geo_engine.py`'s `HybridWindFarmOptimizer`).
2. **Synthetic Data Substitution on Upstream Layers**: While DEM elevation, Overpass OSM settlements, and Open-Meteo telemetry query live services, the WorldCover land-cover client (`worldcover_client.py`) and Protected Planet client (`protected_planet_client.py`) rely on **hardcoded coordinate bounding boxes and synthetic lookups** rather than true GeoTIFF raster queries or real WDPA API calls.
3. **Corner Pushing & Candidate Dispersion**: The greedy thinning and 1-opt local exchange algorithms in `geo_engine.py` and `geometry.ts` can bias turbine placement toward polygon peripheries or cluster them near parcel vertices because perimeter setback distances are set to `0.5 * D` (60m) rather than standard physical planning setbacks ($1.5D$ to $3D$, or $180\text{--}360\,\text{m}$).
4. **Cesium 3D Wake Lines vs. 2D Leaflet Discrepancies**: While CesiumJS applies an 8.5D downwind Jensen wake trapezoid, the 2D Leaflet canvas draws dual SVG cones and synthetic wake lines with differing decay constants.
5. **Simulated Quantum Execution on Scaled Sites**: WS-QAOA circuit compilation via Qiskit Aer is limited to $N \le 12$ candidates and $K \le 8$ turbines. When $N > 12$, the solver silently branches to classical continuous relaxation with 1-opt repair, bypassing quantum simulation while reporting a "quantum" telemetry envelope.

---

## 2. Subsystem Classification Matrix

Each subsystem has been evaluated across runtime code paths, network calls, and mathematical formulations:

| # | Subsystem | Classification | Implementation Location | Provenance / Data Origin |
|---|-----------|----------------|-------------------------|--------------------------|
| 1 | Backend Architecture | **REAL** | `backend/app/main.py`, `backend/app/api/` | FastAPI asynchronous ASGI service with CORS, SQLite ORM, and background worker threads. |
| 2 | Frontend Architecture | **REAL** | `src/App.tsx`, `src/components/` | React 18 + Vite + TypeScript + Tailwind CSS state machine with URL hash synchronization. |
| 3 | Database / Schema | **REAL** | `backend/app/db.py`, `backend/app/schemas.py` | SQLite database (`aeroquantum.db`) with tables: `projects`, `users`, `sessions`, `dem_cache`, `osm_exclusion_cache`, `india_wind_hotspots`. Pydantic v2 schemas. |
| 4 | API Endpoints | **PARTIAL** | `backend/app/api/*.py` | Multiple redundant/divergent endpoints (`/api/optimize` vs `/api/qaoa-optimize`, `/api/geo/optimize`). |
| 5 | Coordinate Handling | **PARTIAL** | `backend/app/geo_engine.py`, `src/utils/geometry.ts` | Equirectangular projection relative to site origin. Accurate for small sites ($<10\,\text{km}$), but introduces metric distortion on large concessions ($>40\,\text{km}$). |
| 6 | Location Search | **REAL** | `backend/app/gis/village_boundary_client.py` | Live OpenStreetMap Nominatim reverse and forward geocoding with user-agent headers and caching. |
| 7 | Boundary Generation | **PARTIAL** | `village_boundary_client.py`, `geometry.ts` | Resolves official OSM administrative polygons when available; falls back to bounding-box rectangular envelopes or synthetic harmonic oval concessions if OSM has only point nodes. |
| 8 | Terrain Handling | **REAL** | `backend/app/gis/copernicus_dem.py` | Real Copernicus DEM GLO-30m via Open-Meteo Elevation API with local SQLite caching (`dem_cache`) and Horn's 3x3 kernel spatial slope/aspect calculation. |
| 9 | Wind Data | **PARTIAL** | `backend/app/gis/global_wind_atlas.py`, `backend/app/api/telemetry.py` | ERA5 live hourly 100m wind telemetry is **REAL** (Open-Meteo API). Climatological Global Wind Atlas 3.0 Weibull/WPD is **HARDCODED** regional formulas. |
| 10| Land-Cover Data | **HARDCODED** | `backend/app/gis/worldcover_client.py` | Claims ESA WorldCover 10m, but returns hardcoded coordinate-box heuristics. |
| 11| OSM Exclusion Logic | **REAL** | `backend/app/gis/overpass_client.py` | Queries live Overpass API for `place=*`, `building=*`, `highway=*`, `power=*`, `waterway=*` with 500m–1000m setbacks and SQLite caching. |
| 12| Protected-Area Logic | **HARDCODED** | `backend/app/gis/protected_planet_client.py` | Hardcoded list of 10 Indian national park centroids with circular radius approximation. No real WDPA vector/STAC query. |
| 13| Turbine Catalogue | **REAL** | `backend/app/engineering/floris_engine.py` | Tabulated power and thrust coefficient $C_T(u)$ curves for GE Vernova 2.5-120, Vestas V110-2.0, NREL 5-MW, IEA 15-MW, Siemens Gamesa SG 3.4-132. |
| 14| Turbine 3D Models | **REAL** | `public/assets/models/wind_turbine.glb` | Real binary glTF 3D model with rotating rotor animations, combined with procedural Cesium cylinder masts and nacelle boxes. |
| 15| Turbine Positioning | **PARTIAL** | `geo_engine.py`, `src/utils/geometry.ts` | Multi-stage filtering pipeline is mathematically implemented, but suffers from edge/corner accumulation due to low perimeter setbacks and spacing relaxation. |
| 16| Turbine Orientation | **REAL** | `src/components/gis/CesiumGlobeView.tsx` | Upwind HAWT alignment facing oncoming wind vector ($\theta_{\text{yaw}} = (\theta_{\text{wind}} - 90^\circ)$ glTF axis correction). |
| 17| Wake Calculation | **REAL** | `core/aerodynamics.py`, `backend/app/engineering/floris_engine.py` | Jensen (Park) kinematic model and Bastankhah & Porté-Agel (2014/2016) Gaussian wake deficit model with sum-of-squares deficit superposition. |
| 18| AEP Calculation | **REAL** | `core/post_processor.py`, `floris_engine.py` | Numerical integration across 16 wind rose directional sectors and Weibull wind speed distribution bins. |
| 19| Candidate Generation | **PARTIAL** | `backend/app/geo_engine.py` | Regular metric grid sampling inside boundary polygon; scale-adaptive grid step ($60\,\text{m}\text{--}400\,\text{m}$). Thinning uses spatial KD-tree. |
| 20| QUBO Formulation | **REAL** | `core/quantum_hamiltonian.py`, `floris_engine.py` | Binary quadratic cost function mapping turbine placement, pairwise wake loss penalties, and proximity penalties into Ising spin Hamiltonian $(h, J)$. |
| 21| QAOA Implementation | **REAL** | `core/wsqaoa.py` | Warm-Started QAOA with XY mixer preserving Hamming weight $K$; parameterized Qiskit quantum circuit optimized via classical COBYLA. |
| 22| Simulator / Hardware Abstraction | **PARTIAL** | `core/wsqaoa.py` | Uses Qiskit Aer `AerSamplerV2` for $N \le 12$; silently falls back to classical continuous relaxation for $N > 12$. No direct QPU quantum hardware driver configured. |
| 23| Cesium Implementation | **REAL** | `src/components/gis/CesiumGlobeView.tsx` | CesiumJS WebGL viewer rendering glTF turbines, terrain-draped satellite composite textures, Jensen wake trapezoids, and camera presets. |
| 24| Map Tile Providers | **REAL** | `backend/app/api/geo.py` | Server-side proxy and disk cache for satellite imagery, OpenTopoMap terrain tiles, and CartoDB/Google tiles (`/api/geo/tiles/...`). |
| 25| Caching Layer | **REAL** | `backend/app/db.py`, `backend/app/api/geo.py` | SQLite disk caches for DEM elevations (`dem_cache`), Overpass queries (`osm_exclusion_cache`), and stitched satellite tiles (`backend/data/tiles/`). |
| 26| Error Handling | **PARTIAL** | Across FastAPI routers and React components | Catch-all `except Exception:` blocks exist in GIS clients with silent fallbacks to synthetic models. |
| 27| Test Suite | **REAL** | `tests/` | 47 passing unit and physics tests (`test_api.py`, `test_physics.py`, `test_wsqaoa.py`, `test_floris_engine.py`, `test_environmental_stack.py`). |

---

## 3. Deep Dive: Engineering Values & Data Provenance

### A. Terrain Elevation & Slope
- **Claim**: Copernicus DEM GLO-30m surface elevation.
- **Where does it come from?**: 
  - `backend/app/gis/copernicus_dem.py` calls `https://api.open-meteo.com/v1/elevation?latitude=...&longitude=...`.
  - Open-Meteo's elevation service is backed by European Space Agency Copernicus 30m and SRTM.
  - 3x3 kernel Horn's algorithm is applied to compute spatial gradient, slope angle (degrees), aspect azimuth, and Terrain Ruggedness Index (TRI).
  - Sampled points are cached in SQLite table `dem_cache`.
- **Verdict**: **REAL**.

### B. Atmospheric Wind Telemetry vs. Long-Term Climatology
- **Claim**: Live wind telemetry and Global Wind Atlas 3.0 wind resource.
- **Where does it come from?**:
  - Live wind telemetry (`backend/app/api/telemetry.py`): Calls Open-Meteo European Centre (ECMWF) forecast API for 100m hub-height wind speed and direction. **REAL**.
  - Climatological resource (`backend/app/gis/global_wind_atlas.py`): Does **not** query DTU or World Bank GWA APIs or Rasters. Instead, it evaluates a regional `if/elif` block checking whether coordinates fall in Gujarat, Rajasthan, Tamil Nadu, etc., and returns hardcoded base values ($8.65\,\text{m/s}$, $8.25\,\text{m/s}$, etc.).
- **Verdict**: Live telemetry is **REAL**; Global Wind Atlas is **HARDCODED**.

### C. Land Cover & Environmental Suitability
- **Claim**: ESA WorldCover 10m high-resolution land classification.
- **Where does it come from?**:
  - `backend/app/gis/worldcover_client.py` evaluates `evaluate_concession_landcover()`.
  - It inspects whether OSM Overpass returned any residential buildings. If yes, it declares `dominant_code = 50 (Built-up)`. Otherwise, it uses latitude/longitude bounding-box checks (e.g., $23^\circ \le \text{lat} \le 28^\circ \implies \text{Bare/sparse}$).
  - No ESA WorldCover Cloud-Optimized GeoTIFF (COG) or Google Earth Engine STAC API is queried.
- **Verdict**: **HARDCODED HEURISTIC**.

### D. Protected Areas & Conservation Exclusions
- **Claim**: UNEP-WCMC / Protected Planet WDPA v4 dataset.
- **Where does it come from?**:
  - `backend/app/gis/protected_planet_client.py` contains a static Python list `PROTECTED_AREAS_INDIA` of 10 park coordinates with rough circular radiuses (e.g., Gir National Park, Desert National Park, Mudumalai).
  - No connection to the Protected Planet API or official MoEFCC Eco-Sensitive Zone shapefiles.
- **Verdict**: **HARDCODED MOCK**.

### E. Geotechnical Soil Bearing Capacity
- **Claim**: ISRIC SoilGrids 250m v2.0 REST API & Open-Meteo Land Surface.
- **Where does it come from?**:
  - `backend/app/gis/soil_client.py` queries `https://rest.isric.org/soilgrids/v2.0/properties/query` for `bdod` (bulk density), `clay`, `sand`, and `silt` at depth `0-5cm`.
  - Computes USDA Soil Texture Triangle classification and empirical ultimate bearing capacity $q_{\text{ult}} = 5.14 \cdot c_u \cdot (1 + \text{density factor})$.
  - Live soil moisture is fetched from Open-Meteo land-surface API.
- **Verdict**: **REAL**.

### F. Wake Modelling & Power Calculations
- **Claim**: N.O. Jensen (1983) and NREL FLORIS 4.x Bastankhah Gaussian Wake Model.
- **Where does it come from?**:
  - `core/aerodynamics.py`: Vectorized NumPy implementation of Jensen deficit $\Delta v / v_0 = (1 - \sqrt{1 - C_t}) / (1 + 2kx/D)^2$ with downstream conical expansion $R_{\text{wake}}(x) = D/2 + kx$. **REAL**.
  - `backend/app/engineering/floris_engine.py`: Bastankhah Gaussian wake velocity deficit $\Delta v / v_0 = (1 - \sqrt{1 - \frac{C_t}{8(\sigma/D)^2}}) \exp(-0.5 (r/\sigma)^2)$. **REAL**.
  - Cubic and tabulated power curves from official manufacturer reference specifications. **REAL**.

### G. QUBO & Quantum WS-QAOA Solver
- **Claim**: Warm-Started QAOA with XY Mixer preserving Hamming weight $K$.
- **Where does it come from?**:
  - `core/quantum_hamiltonian.py`: Ising Hamiltonian $H = \sum_i h_i Z_i + \sum_{i<j} J_{ij} Z_i Z_j + \text{offset}$ correctly derived from binary optimization costs:
    $$\mathcal{C}(x) = \sum_{i,j} W_{ij} x_i x_j + \lambda_{\text{turb}} \left(\sum_i x_i - K\right)^2 + \lambda_{\text{prox}} \sum_{d_{ij} < d_{\text{min}}} x_i x_j - \sum_i P_i x_i$$
  - `core/wsqaoa.py`: Computes continuous relaxation $c^* \in [0, 1]^N$ via quadratic programming, derives warm-start rotation angles $\theta_i = 2 \arcsin(\sqrt{c^*_i})$, applies $R_Y(\theta_i)$ initialization, alternating cost $R_{ZZ}$ layers, and parameterized Givens $XY$ mixers.
  - Solves via classical COBYLA loop using Qiskit Aer.
  - When $N > 12$ or $K > 8$, continuous relaxation + greedy repair is returned directly.
- **Verdict**: **REAL** algorithm implementation with **PARTIAL/CONDITIONAL** simulation scaling.

---

## 4. Root Causes of Observed System Failures

### 1. Turbines Being Pushed Toward Corners / Boundaries
- **Mechanism**: In `src/utils/geometry.ts` (`generatePolygonEnclosedTurbines` and `ensureTurbinesInsideBoundary`), candidates are sorted by distance from the boundary descending, but then subjected to aggressive spacing relaxation (multiplied by $0.72$ each pass) when requested turbine counts cannot be placed inside the core area.
- Furthermore, the settlement setback buffer enforces a $500\,\text{m}$ clearance from the centroid. Because the center is excluded and spacing between turbines is high, the algorithm pushes active positions against the parcel perimeter.
- In `backend/app/geo_engine.py`, `self.setback_m` is initialized to $\max(50.0, 0.5 \cdot D) = 60\,\text{m}$. For a 120m rotor, a 60m setback places blade tips directly over the parcel boundary.

### 2. Turbines Placed on Buildings, Roads, or Water
- **Mechanism**: In `backend/app/geo_engine.py`, when Overpass API fails, times out, or returns sparse features in rural regions, the fallback settlement detection in `overpass_client.py` only creates a single synthetic point at `(center_lat, center_lon)`. Any actual dwellings, farm structures, unclassified rural roads, or water bodies located $1\text{--}3\,\text{km}$ from the center are missed.
- On the frontend side, `src/utils/geometry.ts`'s `generatePolygonEnclosedTurbines` does **not** evaluate OSM features at all; it only evaluates polygon containment and distance to the single site centroid. If the frontend generates or relocates turbines, it bypasses OSM exclusions entirely.

### 3. Arbitrary Spacing & Spacing Violations
- **Mechanism**: The backend `geo_engine.py` pipeline Stage 3 relaxes spacing via `relax_factor in [1.0, 0.7, 0.4, 0.0]`. If `requested_turbines` is large relative to parcel area, the spatial thinning drops the threshold from $5D$ down to $0.4 \times 5D = 2D$ or even $0.0$, allowing candidates that physically infringe on wake corridors.
- In the 1-opt local exchange loop, candidates within $0.96 \cdot d_{\text{min}}$ are rejected, but if the initial set was generated with relaxed spacing, spacing violations persist.

### 4. Fake / Decorative Wake Lines
- **Mechanism**: On Leaflet Screen 3 (`src/components/workflow/Screen3Layout.tsx`), wake cones are rendered as two static SVG polygons (`coreCone` and `wakeCone`) with fixed angular spreads ($8.5^\circ$) and arbitrary opacity gradients.
- On Screen 5 Cesium 3D (`CesiumGlobeView.tsx`), wake plumes are rendered as static 4-vertex horizontal trapezoids extending 8.5D downwind. While length and direction are physically anchored, they are static geometries that do not reflect 3D atmospheric boundary layer turbulence, meandering, or ground height draping if terrain is flat.

### 5. Wind Direction & Turbine Orientation Mismatches
- **Mechanism**: In `CesiumGlobeView.tsx`, the glTF turbine asset axis required an empirical heading offset:
  `const gltfHeadingDeg = (windDirectionDeg - 90 + 360) % 360;`
  In earlier versions of the codebase, the $-90^\circ$ yaw offset was omitted or mismatched with Leaflet's compass rose ($0^\circ$ North vs Cartesian $0^\circ$ East), causing turbines to point orthogonal to the wind or directly downwind (tail into the wind).
- Furthermore, when projects are created, `wind_direction` is set to $45^\circ$, while telemetry reports $300^\circ$ or $270^\circ$, causing UI components using project state to disagree with Cesium components using telemetry state.

### 6. Quantum Optimization Operating Before Engineering Feasibility
- **Mechanism**: In `backend/app/api/optimize.py`, the endpoint `POST /api/optimize` accepts raw candidate coordinates without running the Overpass exclusion filter, slope filter, or conservation check. It constructs the Ising Hamiltonian directly from coordinates and executes QAOA.
- Only the alternate endpoint `POST /api/qaoa-optimize` in `layout.py` calls `CandidateGenerationEngine.execute_pipeline()` first. If the frontend calls `POST /api/optimize` (as configured in `api.ts:runOptimization`), quantum optimization runs on unvetted coordinates.

---

## 5. Architectural Recommendations

1. **Unify API Routers**: Retire the legacy `/api/optimize` worker in `optimize.py` in favor of a single unified pipeline that guarantees:
   `Feasibility Filter -> Pruned Candidates -> QUBO -> WS-QAOA -> FLORIS AEP`.
2. **Move Geometry Invariance to Backend**: Deprecate client-side coordinate synthesis (`generatePolygonEnclosedTurbines` in `geometry.ts`). All turbine coordinates must originate exclusively from verified backend GIS responses.
3. **Upgrade Perimeter Setbacks**: Enforce strict statutory setbacks in `geo_engine.py`:
   - Property boundary: $\ge 1.5 D$ ($180\,\text{m}$)
   - Inhabited dwellings: $\ge 500\,\text{m}$ (IEC 61400 noise/shadow setback)
   - High-voltage powerlines: $\ge 1.5 \times \text{hub height}$ ($165\,\text{m}$)
   - Roads / highways: $\ge 1.0 \times \text{hub height} + 0.5 \times \text{rotor diameter}$ ($170\,\text{m}$).
4. **Transparent Solver State**: Clearly distinguish when QAOA is simulated via statevector vs when classical relaxation is used for large $N$. Never report a classical continuous relaxation solution as a simulated quantum state.
