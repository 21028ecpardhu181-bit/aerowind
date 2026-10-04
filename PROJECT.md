# Project: AeroQuantum-Wind Engineering Engine Rebuild

## Architecture
The AeroQuantum-Wind platform couples GIS geodetic truth with quantum-inspired combinatorial optimization and industrial analytical wake aerodynamics.

```
[ User Search / GIS Input ]
            │
            ▼
[ Geocoding Service (Nominatim + Offline Cache) ]
            │ (Canonical Center Lat/Lon)
            ▼
[ Study Area Model (Geodesic Radius / GIS Drawn Polygon) ]
            │ (Geodetic Boundary WGS84, Area km², Perimeter km)
            ▼
[ Candidate Generation Engine (Grid + 5-Class Feasibility Mask) ]
            │ (Terrain Elevation, Slope, Wind Speedup, Setbacks, Exclusions)
            ▼
[ Layout Optimization Engine (Ising / QUBO / QAOA / 1-Opt Exchange) ]
            │ (Strict Candidate Index Selection, >= 5D Spacing, Honest Capacity)
            ▼
[ Visualization & Export Engine (CesiumJS 3D Globe + Blueprint Export) ]
            │ (CLAMP_TO_GROUND 3D GLB, Jensen Hub Wake Cones, 6-Decimal Export)
```

- **Frontend / Client (`frontend/js/app.js`, `frontend/js/cesium-map.js`)**:
  - Single source of geodetic truth in `APP_STATE`.
  - Leaflet 2D GIS and CesiumJS 3D globe visualization.
  - Dual study area selection: Geodesic circles (1 km to 100 km) and interactive polygon drawing (add, drag, delete vertex, close, clear, geodetic area & perimeter).
  - 3D terrain elevation mesh, `CLAMP_TO_GROUND` GLB turbine models, nacelle hub-level Jensen wake cones.
  - Export handlers for CSV, GeoJSON, and JSON matching live coordinates to 6 decimal places.
- **Backend Geospatial Service (`backend/app/geo_engine.py`, `backend/app/geo_utils.py`, `backend/app/api/`)**:
  - Equirectangular local metric projection anchored at geodetic center.
  - Scale-adaptive raw candidate grid generator ($1,500$ to $4,000$ points).
  - 5-Tier physical feasibility mask: `PREFERRED`, `BUILDABLE`, `RESTRICTED`, `EXCLUDED`, `UNKNOWN`.
  - Exclusion diagnostic reasons: slope $> 16^\circ$, water $< 120$ m, settlements $< 250$ m, roads $< 60$ m, sub-cut-in wind $< 4.0$ m/s.
  - Topographic elevation, slope, aspect, and terrain-aware wind speedup calculation.
- **Physics & Optimization Kernels (`core/aerodynamics.py`, `core/quantum_hamiltonian.py`, `core/wsqaoa.py`, `core/post_processor.py`)**:
  - Jensen analytical kinematic wake model with decay $k=0.075$, hub altitude $Z = \text{elevation} + \text{hub\_height}$.
  - QUBO formulation with quadratic spacing penalty for $d_{ij} < 5D = 600$ m and boundary containment penalty.
  - Warm-started QAOA with continuous QP relaxation and XY mixer preserving Hamming weight $K$.
  - `HybridWindFarmOptimizer` with candidate subspace selection and greedy 1-opt local search.
  - Honest capacity reporting when $M < K$ without silent collapse to 1 turbine.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Canonical Geodetic State | Single source-of-truth project state model; coordinates stored exclusively as (lat, lon, elevation); zero mutation on pan/zoom/tilt/orbit. | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Global Coordinate Generality | Remove India-specific latitude/longitude swap heuristic in `normalize_coord_pair` so global coordinates (Europe, Americas, etc.) work without corruption. | M1 | ORIGINAL_REQUEST §R1, Survey |
| 3 | Resilient Multi-City Geocoding | Ensure complete offline fallback entries for Rajahmundry, Bommuru, Hukkumpeta, Jaisalmer, Kanyakumari, and regex coordinate parsing. | M1 | ORIGINAL_REQUEST §R1, Survey |
| 4 | Dual Selection: Geodesic Radius | Compute geodesic circular boundary across preset (1, 5, 10, 25, 50, 100 km) and custom scales with exact geodetic area. | M1 | ORIGINAL_REQUEST §R2 |
| 5 | Dual Selection: Interactive Polygon | Full GIS drawing with add vertex, drag/edit vertex, right-click delete vertex, close, and clear; tracks geodetic area ($km^2$), perimeter ($km$), and centroid. | M1 | ORIGINAL_REQUEST §R2, Survey |
| 6 | Boundary Pinning & Viewport Decoupling | Study boundaries and placed turbines remain geographically pinned during map movement, zoom, and 2D/3D mode switches. | M1 | ORIGINAL_REQUEST §R1, §R2 |
| 7 | Scale-Adaptive Candidate Grid | Dynamic grid spacing ($60$m to $1000$m) based on boundary span, generating evaluation points strictly inside boundary and setbacks. | M1 | ORIGINAL_REQUEST §R3 |
| 8 | 5-Class Feasibility Masking | Classify candidates into PREFERRED, BUILDABLE, RESTRICTED, EXCLUDED, UNKNOWN with explicit diagnostic failure reasons for EXCLUDED. | M1 | ORIGINAL_REQUEST §R3 |
| 9 | UNKNOWN Geotechnical Safeguard | Ensure UNKNOWN candidates require field survey and are never silently converted to safe or placed. | M1 | ORIGINAL_REQUEST §R3 |
| 10 | Candidate Pool Strictness | Optimization selects turbine indices strictly from filtered candidate pool; zero coordinates synthesized outside candidates. | M1 | ORIGINAL_REQUEST §R4 |
| 11 | Physical Spacing ($\ge 5D$) Enforcement | Pairwise distance between all placed turbines meets or exceeds $5D$ ($600$m for $120$m rotor). | M1 | ORIGINAL_REQUEST §R4 |
| 12 | Honest Capacity Reporting | When requested $K >$ feasible $M$ in constrained areas (e.g. 1 km circle), honestly place $M$ with diagnostic message (e.g. "20 requested · 7 feasible") and never collapse to 1. | M1 | ORIGINAL_REQUEST §R4 |
| 13 | 3D Digital Elevation Anchoring | Anchor turbine bases onto terrain mesh using `CLAMP_TO_GROUND` with high-fidelity 3D GLB model and LOD scaling. | M1 | ORIGINAL_REQUEST §R5 |
| 14 | Physics-Coupled Wake Cones | Cones originate at nacelle hub altitude ($Z = \text{elevation} + \text{hub\_height}$), expand downstream with $k=0.075$, and reflect Jensen velocity deficits. | M1 | ORIGINAL_REQUEST §R5 |
| 15 | Engineering Blueprint 6-Decimal Export | Micro-siting schedule and CSV, GeoJSON, and JSON exports match displayed coordinates to 6 decimal places. | M1 | ORIGINAL_REQUEST Acceptance Criteria |
| 16 | E2E Testing Suite Verification | Verify multi-city test, Bommuru boundary adherence, full 6-screen Playwright E2E flow across mobile (390px) and desktop (1280px), and 42 pytest tests. | M2 | ORIGINAL_REQUEST Verification Resources |
| 17 | Adversarial Hardening & Forensic Audit | Zero tolerance integrity verification, edge case testing on extreme coordinates, empty areas, and high-density constraints. | M3 | System Prompt & Acceptance Criteria |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Geospatial Engine, Geocoding Generality & Interactive GIS Perimeter | Fix `normalize_coord_pair` global generality bug; complete offline geocoding fallbacks for Rajahmundry, Bommuru, Hukkumpeta; guard empty candidate fallback; implement and display geodetic perimeter in km in polygon draw UI; verify coordinate persistence across viewport changes. | none | IN_PROGRESS |
| M2 | E2E Testing Track & Opaque-Box Suite Verification | Author and publish `TEST_INFRA.md` and `TEST_READY.md`; verify all 4 tiers of test cases (pytest 42 tests, multi-city pipeline across 5 cities, Bommuru boundary adherence, and complete flow E2E on mobile 390px and desktop 1280px). | M1 | PLANNED |
| M3 | Final Milestone: 100% E2E Pass, Adversarial Hardening (Tier 5) & Forensic Integrity Audit | Pass 100% E2E test suite; run adversarial challenger verification (white-box stress testing); run forensic integrity auditor (zero hardcoding, genuine QUBO/QAOA and Jensen wake models, clean audit verdict). | M2 | PLANNED |

---

## Interface Contracts

### Backend GeoEngine ↔ API (`backend/app/geo_engine.py` ↔ `backend/app/api/`)
- `normalize_coord_pair(p: Union[List[float], Tuple[float, float]]) -> Tuple[float, float]`:
  - Input: Coordinate pair `[lat, lon]` or `[lon, lat]`.
  - Contract: If $|p_0| > 90.0$ and $|p_1| \le 90.0$, return `(p1, p0)`. Must NOT perform regional threshold assumptions that invert valid Northern/Southern hemisphere latitudes.
- `CandidateGenerationEngine.execute_pipeline() -> List[Dict[str, Any]]`:
  - Returns list of candidate dicts with keys: `id`, `latitude`, `longitude`, `x_m`, `y_m`, `terrain_elevation`, `slope_deg`, `wind_resource_mps`, `feasibility`, `exclusion_reasons`.
  - Feasibility enum: `"FEASIBLE"`, `"RESTRICTED"`, `"EXCLUDED"`, `"UNKNOWN"`.
  - When feasible candidates are 0, must return empty list with zero excluded/unknown leakage.
- `HybridWindFarmOptimizer.solve_hybrid_optimization() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]`:
  - Returns `(placed_turbines, metadata)`.
  - Every turbine in `placed_turbines` has `lat`, `lon`, `x_m`, `y_m`, `elevation_m` strictly sourced from a candidate in `self.candidates`.
  - When feasible count $M < K$, `len(placed_turbines) == M`, `metadata["is_capacity_constrained"] == True`, headline formatted as `"{requested_count} requested · {actual_placed} feasible"`.

### Frontend State ↔ Cesium 3D Engine (`frontend/js/app.js` ↔ `frontend/js/cesium-map.js`)
- `window.CesiumWindMapEngine.setSiteBoundary(vertices: Array<[lat, lon]>)`:
  - Renders red dashed boundary corridor pinned to geodetic WGS84 coordinates on globe terrain.
- `window.CesiumWindMapEngine.render3DTurbines(turbines: Array<{lat, lon, elevation_m, id}>, windDir: number)`:
  - Renders 3D GLB models with `heightReference: Cesium.HeightReference.CLAMP_TO_GROUND`.
- `window.CesiumWindMapEngine.render3DWakeCones(turbines, windDir, windSpeed)`:
  - Renders wake cylinders at hub altitude $Z = \text{baseElev} + \text{hubHeight}$.

---

## Code Layout
- `backend/app/main.py`: FastAPI server configuration & route mounting.
- `backend/app/geo_engine.py`: Core geospatial math, candidate generation, 5-class feasibility, hybrid optimizer.
- `backend/app/geo_utils.py`: Nominatim client, geocoding fallback dictionary, geodesic distance utils.
- `backend/app/api/geo.py`: `/api/geo/geocode`, `/api/geo/candidates`, `/api/geo/feasibility`.
- `backend/app/api/layout.py`: `/api/geo/initial-layout`, `/api/geo/qaoa-optimize`.
- `backend/app/api/optimize.py`: `/api/optimize`, `/api/blueprint`.
- `core/aerodynamics.py`: Analytical Jensen wake model, pairwise wake matrix, wind rose fixture.
- `core/quantum_hamiltonian.py`: Ising Hamiltonian, distance matrix penalties, brute-force ground state solver.
- `core/wsqaoa.py`: Warm-started QAOA optimizer, continuous relaxation, XY mixer.
- `core/post_processor.py`: Greedy 1-opt repair and AEP calculation.
- `frontend/js/app.js`: Application state management, UI controllers, dual study area selection, export handlers.
- `frontend/js/cesium-map.js`: Cesium 3D globe visualization engine.
- `tests/`: Pytest suite (`test_*.py`) and verification scripts (`verify_*.py`).
