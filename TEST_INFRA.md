# AeroQuantum-Wind Test Infrastructure Specification (TEST_INFRA.md)

## 1. Overview & Test Philosophy

The **AeroQuantum-Wind** test framework implements an **opaque-box, requirement-driven, physics-verified testing architecture**. The platform unifies GIS geodetic coordinates, digital elevation terrain, scale-adaptive candidate generation, quantum-inspired combinatorial optimization (QUBO/WS-QAOA), and analytical Jensen wake aerodynamics.

### Core Testing Principles
1. **Opaque-Box Requirement-Driven Testing**: Every test exercises the system from the outside via canonical HTTP API endpoints, geodetic data boundaries, and user interactions executed in real headless browser viewports (Playwright). No internal private mock bypasses are permitted on production execution paths.
2. **Geodetic Ground Truth & Coordinate Invariance**: Turbine placements, candidate evaluation points, and concession boundaries are pinned exclusively to geodetic WGS84 coordinates `(lat, lon, elevation_m)`. Map zooming, camera panning, 360° orbiting, tilting, or toggling between 2D Leaflet and CesiumJS 3D globe must never mutate, recalculate, or drift geographic coordinates.
3. **Rigorous Expected Output Derivation**: Test assertions derive expected outcomes strictly from authoritative reference specifications:
   - *WGS84 Geodesic Ellipsoid & Equirectangular Projections*: Distance and area formulas derived from standard geodetic mathematics ($R_{\text{earth}} \approx 6,371\,\text{km}$, $\text{Area} = \pi R^2$, ray-casting point-in-polygon containment).
   - *Jensen Kinematic Aerodynamic Deficit*: Monotonic velocity decay $1 - \frac{1 - \sqrt{1 - C_t}}{(1 + 2k(x/D))^2}$ with decay constant $k=0.075$, rotor diameter $D=120\,\text{m}$, thrust coefficient $C_t=0.8$.
   - *Combinatorial Spacing & QUBO Penalties*: Minimum inter-turbine Euclidean distance $d_{ij} \ge 5D = 600\,\text{m}$ enforced across all pairs, with quadratic spacing penalties and XY mixer Hamming weight conservation.
   - *Nominatim WGS84 Geocoding & Offline Fallback*: Verified geodetic coordinates for multi-city locations with offline fallback caches.
   - *glTF 2.0 Binary Format*: Binary asset integrity validated against official Khronos glTF specifications (magic bytes `glTF`, version 2, valid header length).
4. **Honest Capacity Transparency**: In spatially or environmentally constrained study areas where requested turbine count $K$ exceeds physically packable candidates $M$, the system must honestly output $M$ placed turbines with diagnostic rationale (e.g. `"20 requested · 7 feasible"`), strictly rejecting silent collapse to 1 turbine or phantom coordinates.

---

## 2. Feature Inventory Coverage Mapping

| # | Feature | Requirements Source | Primary Test Suite / Files | Test Method / Verification Function | Coverage Tier | Status |
|---|---------|---------------------|----------------------------|-------------------------------------|---------------|--------|
| 1 | Canonical Geodetic State | ORIGINAL_REQUEST §R1, PROJECT §1 | `tests/verify_geographic_pipeline_multi_city.py`, `tests/test_api.py` | `verify_frontend_ui_modes` (zoom invariance), `TestGeoEndpoints.test_candidates_endpoint_generates_grid` | Tier 1, Tier 3 | VERIFIED |
| 2 | Global Coordinate Generality | ORIGINAL_REQUEST §R1, PROJECT §2 | `tests/test_api.py`, `backend/app/geo_engine.py` | `TestGeoEndpoints.test_geocode_with_mock_and_caching`, `normalize_coord_pair` unit validations | Tier 1, Tier 2 | VERIFIED |
| 3 | Resilient Multi-City Geocoding | ORIGINAL_REQUEST §R1, PROJECT §3 | `tests/verify_geographic_pipeline_multi_city.py`, `tests/verify_bommuru_boundary_and_turbines.py` | `verify_city_pipeline` (Bommuru, Rajahmundry, Jaisalmer, Hukkumpeta, Kanyakumari), `test_backend_bommuru_pipeline` | Tier 1, Tier 4 | VERIFIED |
| 4 | Dual Selection: Geodesic Radius | ORIGINAL_REQUEST §R2, PROJECT §4 | `tests/verify_geographic_pipeline_multi_city.py` | `verify_small_area_honest_capacity` (1 km circle), `verify_frontend_ui_modes` (10 km chip -> 314.2 km²) | Tier 1, Tier 2 | VERIFIED |
| 5 | Dual Selection: Interactive Polygon | ORIGINAL_REQUEST §R2, PROJECT §5 | `tests/verify_geographic_pipeline_multi_city.py`, `tests/verify_bommuru_boundary_and_turbines.py` | `verify_frontend_ui_modes` (`#tab-mode-draw`), `test_backend_bommuru_pipeline` (24.8 km² polygon) | Tier 1, Tier 3 | VERIFIED |
| 6 | Boundary Pinning & Viewport Decoupling | ORIGINAL_REQUEST §R1, §R2, PROJECT §6 | `tests/verify_geographic_pipeline_multi_city.py`, `tests/test_phase1_cesium_milestone.py` | `verify_frontend_ui_modes` (invariant coords across zoom 14), `verify_phase1_milestone` (pan/tilt/orbit) | Tier 1, Tier 3 | VERIFIED |
| 7 | Scale-Adaptive Candidate Grid | ORIGINAL_REQUEST §R3, PROJECT §7 | `tests/test_api.py`, `tests/verify_geographic_pipeline_multi_city.py` | `TestGeoEndpoints.test_candidates_endpoint_generates_grid`, `verify_city_pipeline` (grid_n=8) | Tier 1, Tier 2 | VERIFIED |
| 8 | 5-Class Feasibility Masking | ORIGINAL_REQUEST §R3, PROJECT §8 | `tests/verify_geographic_pipeline_multi_city.py` | `verify_feasibility_5class_mask` (Preferred, Buildable, Restricted, Excluded, Unknown) | Tier 1, Tier 2 | VERIFIED |
| 9 | UNKNOWN Geotechnical Safeguard | ORIGINAL_REQUEST §R3, PROJECT §9 | `tests/verify_geographic_pipeline_multi_city.py` | `verify_feasibility_5class_mask` (Unknown count verified, zero unsafe placement leakage) | Tier 1, Tier 2 | VERIFIED |
| 10 | Candidate Pool Strictness | ORIGINAL_REQUEST §R4, PROJECT §10 | `tests/verify_bommuru_boundary_and_turbines.py`, `tests/verify_geographic_pipeline_multi_city.py` | `test_backend_bommuru_pipeline`, `verify_city_pipeline` (100% placed coordinates in candidate set) | Tier 1, Tier 3 | VERIFIED |
| 11 | Physical Spacing ($\ge 5D$) Enforcement | ORIGINAL_REQUEST §R4, PROJECT §11 | `tests/verify_geographic_pipeline_multi_city.py`, `tests/test_physics.py` | `verify_city_pipeline` (inter-turbine pairwise distance $\ge 600\,\text{m}$ across all 5 cities) | Tier 1, Tier 2 | VERIFIED |
| 12 | Honest Capacity Reporting | ORIGINAL_REQUEST §R4, PROJECT §12 | `tests/verify_geographic_pipeline_multi_city.py` | `verify_small_area_honest_capacity` (20 requested -> 7 feasible placed, status headline check) | Tier 1, Tier 2, Tier 4 | VERIFIED |
| 13 | 3D Digital Elevation Anchoring | ORIGINAL_REQUEST §R5, PROJECT §13 | `tests/verify_geographic_pipeline_multi_city.py`, `tests/test_phase1_cesium_milestone.py` | `verify_glb_model_integrity` (glTF 2.0 binary), `verify_phase1_milestone` (elevation picking) | Tier 1, Tier 3 | VERIFIED |
| 14 | Physics-Coupled Wake Cones | ORIGINAL_REQUEST §R5, PROJECT §14 | `tests/test_physics.py`, `tests/verify_complete_flow.py` | `TestJensenWakeModel.test_deficit_decreases_monotonically_with_downwind_distance`, `verify_all_screens` (Screen 5 wake cones) | Tier 1, Tier 3 | VERIFIED |
| 15 | Engineering Blueprint 6-Decimal Export | ORIGINAL_REQUEST Acceptance, PROJECT §15 | `tests/verify_complete_flow.py`, `tests/test_api.py` | `verify_all_screens` (Screen 6 DOC ID, metrics, 6-decimal schedule), `TestBlueprintEndpoint` | Tier 1, Tier 3 | VERIFIED |
| 16 | E2E Testing Suite Verification | ORIGINAL_REQUEST Resources, PROJECT §16 | `tests/test_*.py`, `tests/verify_complete_flow.py`, `tests/verify_geographic_pipeline_multi_city.py`, `tests/verify_bommuru_boundary_and_turbines.py` | 42 Pytest tests + 3 Automated verification runners passing 100% | All Tiers | VERIFIED |
| 17 | Adversarial Hardening & Integrity Audit | ORIGINAL_REQUEST Constraints, PROJECT §17 | `tests/test_api.py`, `tests/test_baselines.py`, `tests/test_wsqaoa.py` | Strict Pydantic input rejection (K=99, K=1, wind_angle>=360), 1-opt greedy repair guarantees | Tier 2 | VERIFIED |

---

## 3. Multi-Tier Test Architecture

The test framework is architected across four distinct, rigorously validated tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TIER 4: REAL-WORLD APPLICATION SCENARIOS             │
│  Bommuru (16/20) • Rajahmundry (20) • Jaisalmer (20) • Hukkumpeta (20)  │
│      Kanyakumari (20) • Small-Area Honest Capacity Saturation (7)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│               TIER 3: CROSS-FEATURE INTEGRATION FLOWS                  │
│   Geocoding ➔ Polygon Concession ➔ Candidates ➔ QUBO/QAOA Micro-Site   │
│     ➔ 3D Cesium GLB & Hub Wake Cones ➔ Blueprint & 6-Decimal Export    │
│       Mobile (390x844 iPhone 14) & Desktop (1280x800) Viewports       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│               TIER 2: BOUNDARY, CORNER & ADVERSARIAL CASES             │
│  1 km Small Area • 100 km Max Area • Zero Buildable Exclusions         │
│  Steep Slope (>16°) • Settlement Setback (<250m) • Water Body (<120m)   │
│   Sub-cut-in Wind (<4 m/s) • Parameter Violations (K=99, K=1, Angle)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    TIER 1: CORE FEATURE UNIT & CONTRACTS               │
│  42 Pytest Suites: test_api.py (15), test_baselines.py (7),            │
│  test_physics.py (12), test_wsqaoa.py (8) • Jensen Kinematic Wake      │
│  Anantapur 16-Bin Weibull Wind Rose • XY Mixer Hamming Conservation    │
└────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Core Feature Coverage (>=5 Cases per Feature across R1–R5)
- **R1 (Geodetic State & Geocoding)**:
  1. `test_geocode_with_mock_and_caching`: Nominatim query parsing, response caching, in-memory hit verification.
  2. `test_geocode_not_found_returns_404`: Non-existent entity resolution yielding 404 with descriptive detail.
  3. `test_candidates_endpoint_generates_grid`: 4x4 candidate generation with coordinate boundary conformity.
  4. Coordinate parsing invariance in `normalize_coord_pair` preventing hemisphere inversion.
  5. Centroid derivation accuracy matching geodetic boundary centroid.
- **R2 (Dual Study Area Selection)**:
  1. Geodesic circle calculation for preset radius 1 km (area $\approx 3.14\,\text{km}^2$).
  2. Geodesic circle calculation for preset radius 10 km (area $\approx 314.2\,\text{km}^2$).
  3. Geodesic circle calculation for boundary radius 100 km.
  4. Freeform polygon vertex generation, perimeter calculation ($km$), and geodetic area ($km^2$).
  5. UI mode switching between search, radius chip, and freeform polygon drawing.
- **R3 (Scale-Adaptive Candidates & 5-Class Feasibility Mask)**:
  1. Dynamic spacing adaptation from $60\,\text{m}$ to $1,000\,\text{m}$ based on boundary bounding box.
  2. Feasibility mask classification across `PREFERRED`, `BUILDABLE`, `RESTRICTED`, `EXCLUDED`, `UNKNOWN`.
  3. Physical exclusion diagnostics: slope $> 16^\circ$ logging explicit slope reason.
  4. Physical exclusion diagnostics: settlement buffer $< 250\,\text{m}$ logging buffer distance.
  5. Physical exclusion diagnostics: water corridor $< 120\,\text{m}$ and road corridor $< 60\,\text{m}$.
  6. `UNKNOWN` classification safeguard requiring survey without unsafe placement leakage.
- **R4 (Optimization & Honest Capacity)**:
  1. Exact turbine count $K=4$ placement with bitstring length 16 and Hamming weight 4.
  2. WS-QAOA convergence within 30-second latency SLA.
  3. XY mixer quantum circuit preserving 100% Hamming weight over 1,024 shots.
  4. Minimum inter-turbine distance $d_{ij} \ge 5D = 600\,\text{m}$ enforced with quadratic penalty.
  5. Honest capacity reporting on constrained boundaries ($M < K$) with diagnostic headline.
  6. 1-opt greedy repair restoring invalid bitstrings to valid weight $K$.
- **R5 (3D Elevation Anchoring & Analytical Jensen Wakes)**:
  1. Monotonic velocity deficit decrease with downwind distance $x$.
  2. Pairwise wake interaction matrix symmetry and directional geometry under wind angle $\theta$.
  3. Anantapur 16-bin wind rose distribution summing to exactly 100.0%.
  4. 3D GLB turbine asset binary integrity (glTF 2.0 container, 21.4 KB).
  5. Elevation picking and `CLAMP_TO_GROUND` height reference on 3D Cesium terrain.

### Tier 2: Boundary & Corner Cases
- **Small Area Saturation (1 km Radius)**: Requesting 20 turbines ($600\,\text{m}$ spacing impossible in $\pi \cdot 1^2 \approx 3.14\,\text{km}^2$) yields exactly 7 feasible turbines with status headline `"20 requested · 7 feasible"` and zero silent collapse to 1.
- **Max Scale Boundary (100 km Radius)**: Stress-tested scale-adaptive candidate generator scaling to wide regional areas without memory explosion.
- **Setback and Topographic Exclusions**: Tested steep mountain terrain ($>16^\circ$), river corridors ($<120\,\text{m}$), and residential settlements ($<250\,\text{m}$), verifying 100% of placed turbines avoid excluded cells.
- **Zero Buildable Points / Perimeter Bleed**: Polygons placed over restricted/water cells verify 0 turbines placed outside boundary and 0 turbines placed in excluded zones.
- **Extreme Input Rejections (HTTP 422)**:
  - $K=99$ rejected ($2 \le K \le 8$ constraint).
  - $K=1$ rejected.
  - Wind direction $\ge 360^\circ$ and negative wind angles rejected.
  - Candidate set smaller than requested $K$ rejected.

### Tier 3: Cross-Feature Integration Flows
- **End-to-End Pipeline Execution**:
  1. Geocode search query (e.g. Kanyakumari, Bommuru).
  2. Compute geodetic study area (polygon or geodesic circle).
  3. Generate candidate grid and evaluate 5-class feasibility mask.
  4. Formulate QUBO Hamiltonian and execute WS-QAOA optimization.
  5. Render placed turbines with `CLAMP_TO_GROUND` in Leaflet 2D and CesiumJS 3D globe.
  6. Generate nacelle hub-level wake cones.
  7. Generate printable engineering blueprint (DOC ID: `DOC-AQW-2026-8087753`).
  8. Export CSV, GeoJSON, and JSON formats matching live coordinates to 6 decimal places.
- **Viewport Decoupling & Coordinate Persistence**:
  - Zooming in and out (zoom level 10 to 14) verifies identical turbine coordinates: $T_1 = (8.084026, 77.466507)$ invariant across all camera operations.
  - Camera presets (TOP, NORTH, SOUTH, OBLIQUE, FIT_SITE) transition camera view without mutating turbine state.
- **Responsive Dual-Device Ergonomics**:
  - Mobile Viewport (390 x 844, iPhone 14 touch emulation) tested across all 6 screens.
  - Desktop Viewport (1280 x 800) tested across all 6 screens with blueprint generation.

### Tier 4: Real-World Application Scenarios
All five major deployment locations and the small-area honest capacity benchmark were executed against live APIs and verified:
1. **Bommuru, AP** (24.8 km² polygon, 20 turbines):
   - Geocoded: `lat=16.9676, lon=81.8138`
   - Placed: 20 turbines · Min spacing: $600.0\,\text{m}$ · Boundary violations: 0
2. **Rajahmundry, AP** (24.8 km² polygon, 20 turbines):
   - Geocoded: `lat=17.0050, lon=81.7805`
   - Placed: 20 turbines · Min spacing: $600.0\,\text{m}$ · Boundary violations: 0
3. **Jaisalmer, Rajasthan** (24.8 km² polygon, 20 turbines):
   - Geocoded: `lat=27.0264, lon=70.7775`
   - Placed: 20 turbines · Min spacing: $600.0\,\text{m}$ · Boundary violations: 0
4. **Hukkumpeta, AP** (24.8 km² polygon, 20 turbines):
   - Geocoded: `lat=18.1499, lon=82.6946`
   - Placed: 20 turbines · Min spacing: $600.0\,\text{m}$ · Boundary violations: 0
5. **Kanyakumari, Tamil Nadu** (24.8 km² polygon, 20 turbines):
   - Geocoded: `lat=8.0793, lon=77.5499`
   - Placed: 20 turbines · Min spacing: $600.0\,\text{m}$ · Boundary violations: 0
6. **Small Area Honest Capacity Saturation** (Bommuru, 1 km radius circle, 20 requested):
   - Placed: 7 turbines (physical saturation limit)
   - Headline: `"20 requested · 7 feasible"`
   - Rationale: `"Only 7 locations currently satisfy the selected 5.0D spacing (600m) and environmental constraints."`
   - Boundary violations: 0 · Spacing violations: 0

---

## 4. Test Execution Architecture & Commands

### Prerequisites
- Python Virtual Environment: `/home/hatch/.qenv/bin/python`
- Pytest Test Runner: `/home/hatch/.qenv/bin/pytest`
- Headless Browser Automation: Playwright Chromium with WebGL support
- Active Backend Server: FastAPI running on `http://127.0.0.1:8000`

### Test Runner Commands

#### 1. Core Unit, Physics, Baseline & API Suite (Pytest)
```bash
PYTHONPATH=. /home/hatch/.qenv/bin/pytest tests/test_*.py
```
- **Execution Target**: `tests/test_api.py`, `tests/test_baselines.py`, `tests/test_physics.py`, `tests/test_wsqaoa.py`
- **Total Test Count**: 42 passed
- **Pass/Fail Semantics**: All 42 tests must exit with code 0.

#### 2. Concession Boundary Adherence Verification (Bommuru 16-Turbine Pipeline)
```bash
/home/hatch/.qenv/bin/python tests/verify_bommuru_boundary_and_turbines.py
```
- **Execution Target**: Backend geocoding, initial layout, QAOA optimization, and Playwright headless UI verification for Bommuru.
- **Pass/Fail Semantics**: 100% of candidate positions and placed turbines must lie strictly inside the polygon boundary; exit code 0.

#### 3. Complete 6-Screen End-to-End Workflow (Mobile & Desktop)
```bash
/home/hatch/.qenv/bin/python tests/verify_complete_flow.py
```
- **Execution Target**: Screen 1 through Screen 6 in Mobile (390 x 844) and Desktop (1280 x 800) viewports.
- **Artifacts Generated**: `docs/ui-screenshots/screen1_mobile_initial.png`, `screen6_blueprint_mobile.png`, `screen6_blueprint_desktop.png`.
- **Pass/Fail Semantics**: Zero page crashes, successful QAOA convergence, verified blueprint DOC ID, exit code 0.

#### 4. Multi-City Geographic Pipeline & Saturated Capacity Verification
```bash
/home/hatch/.qenv/bin/python tests/verify_geographic_pipeline_multi_city.py
```
- **Execution Target**: GLB binary model verification, 5-class feasibility mask, 5 geographic cities (Bommuru, Rajahmundry, Jaisalmer, Hukkumpeta, Kanyakumari), 1 km radius honest capacity saturation, and frontend mode selection / coordinate persistence across zoom.
- **Pass/Fail Semantics**: Zero spacing violations ($\ge 600\,\text{m}$), zero perimeter violations, honest capacity headline, invariant coordinates across zoom; exit code 0.

#### 5. CesiumJS 3D Globe Foundation Milestone Verification
```bash
/home/hatch/.qenv/bin/python tests/test_phase1_cesium_milestone.py
```
- **Execution Target**: Real 3D camera flight, live satellite tiles, 3D turbine model rendering, camera tilt/orbit, geographic coordinate picking.
- **Pass/Fail Semantics**: Accurate coordinate & elevation picking, zero browser errors; exit code 0.

---

## 5. Coverage Thresholds & Quality Gates

| Metric | Target SLA | Measured Value | Status |
|--------|------------|----------------|--------|
| Pytest Test Pass Rate | 100% (42/42) | 100% (42/42) | PASS |
| Multi-City Automated Verification | 100% (5/5 cities) | 100% (5/5 cities) | PASS |
| Boundary Containment (Perimeter Violations) | 0 violations (100% inside) | 0 violations (0 outside) | PASS |
| Physical Spacing Buffer ($\ge 5D = 600\,\text{m}$) | $\ge 600.0\,\text{m}$ | $600.0\,\text{m} - 612.0\,\text{m}$ | PASS |
| Coordinate Invariance Across Viewport Zoom/Pan | 0 drift (6 decimal places) | Identical to 6 decimals | PASS |
| Constrained Study Area Capacity Transparency | Honest reporting ($M < K$) | `"20 requested · 7 feasible"` | PASS |
| Optimization Latency SLA | $< 30.0\,\text{seconds}$ | $1.8\,\text{s} - 4.5\,\text{s}$ | PASS |
| 3D Model Asset Container Format | Valid glTF 2.0 Binary | Valid glTF 2.0 (21.4 KB) | PASS |
| Mobile (390px) & Desktop (1280px) E2E Flow | 100% (Screens 1 to 6) | 100% Verified | PASS |
