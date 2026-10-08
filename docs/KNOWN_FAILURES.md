# AeroQuantum-Wind — Known System Failures & Vulnerabilities

**Date**: 2026-10-06  
**Auditor**: Senior Wind-Farm GIS / Software Engineer  
**Document**: Failure Analysis, Edge Cases, & Engineering Remediation

---

## 1. High-Priority Engineering Failures

### Failure 1: Unreliable Village Boundaries & Geometry Degradation
- **Symptom**: When searching for certain villages, the boundary collapses to a tiny rectangular bounding box, a multi-harmonic oval concession, or fails to snap to authentic village cadastres.
- **Root Cause**:
  - OpenStreetMap Nominatim treats many rural villages as single dimensionless nodes (`place=village`) without an enclosing boundary polygon.
  - When no polygon is returned, `backend/app/gis/village_boundary_client.py` attempts a secondary query on the enclosing county/mandal. If that fails or times out, it falls back to:
    1. A rigid rectangle derived from `item.boundingbox` (which is often just a default $0.01^\circ$ box around the node).
    2. A synthetic multi-harmonic trigonometric envelope:
       `var = 1.0 + 0.12 * math.cos(2 * th) - 0.08 * math.sin(4 * th)`.
- **Engineering Risk**: The platform displays a mathematically synthetic boundary to the engineer while claiming it originates from the official OpenStreetMap Cadastre.

---

### Failure 2: Turbines Appearing on Buildings, Roads, Water, or Unsuitable Land
- **Symptom**: Turbines occasionally generate directly on structures, within residential yards, or intersecting rural roads.
- **Root Cause**:
  - **Overpass Incompleteness**: Rural villages in India and developing nations have incomplete building footprint mapping in OpenStreetMap. Overpass queries for `building=*` frequently return zero features in farmland surrounding villages.
  - **Fallback Center Bias**: When Overpass returns zero buildings, `overpass_client.py` inserts a single synthetic settlement point at `(center_lat, center_lon)` with an $800\,\text{m}$ buffer. It does **not** detect actual dwellings $1.5\,\text{km}$ from the center.
  - **Frontend Bypass**: In `src/utils/geometry.ts`, the function `generatePolygonEnclosedTurbines()` places turbines based solely on distance from the parcel boundary and distance from the single center point. It has **no access to OSM vector layers**. Whenever the frontend runs this fallback, all physical exclusions are ignored.

---

### Failure 3: Turbines Being Pushed Toward Parcel Corners & Perimeters
- **Symptom**: Layouts show turbines clustered along parcel perimeter edges or forced into acute corners.
- **Root Cause**:
  - **Setback Undersizing**: In `backend/app/geo_engine.py`, the boundary setback is defined as:
    `self.setback_m = max(50.0, self.rotor_diameter * 0.5)`
    For a 120m rotor, this is only $60\,\text{m}$ ($0.5D$). In physical wind farm engineering, statutory property boundary setbacks are $1.5D$ to $3.0D$ ($180\,\text{m}\text{--}360\,\text{m}$) or $1.0 \times (\text{hub height} + \text{rotor radius}) + 10\,\text{m}$ ($180\,\text{m}$). Setting it to $60\,\text{m}$ permits placement right against perimeter edges.
  - **Center Exclusion Repulsion**: Both backend and frontend enforce a $500\,\text{m}\text{--}800\,\text{m}$ exclusion around the concession centroid (to protect the village core). In compact parcels ($2\text{--}4\,\text{km}^2$), excluding the center while demanding 12–20 turbines forces the placement algorithm outward against the perimeter fence.
  - **Greedy Spacing Relaxation**: When $K$ turbines cannot fit at $5D$ spacing, `geometry.ts` multiplies inter-turbine spacing by $0.72$ until they fit, packing turbines tightly along polygon vertices.

---

### Failure 4: Fake / Decorative Wake Visualizations
- **Symptom**: Wake plumes appear as static graphic overlays rather than physical CFD or dynamic flow fields.
- **Root Cause**:
  - In `Screen3Layout.tsx`, wake plumes are rendered as two static 2D Leaflet polygons (`coreCone` and `wakeCone`) with fixed angular spreads of $8.5^\circ$ downwind.
  - In `CesiumGlobeView.tsx`, wake footprints are drawn as static flat 4-vertex trapezoids extending 8.5D downwind.
  - These geometric shapes do not calculate actual velocity deficit contours, turbulent mixing, ground boundary layer shear, or wake deflection from yaw misalignment. If wind speed changes from $4\,\text{m/s}$ to $18\,\text{m/s}$, the visual geometry does not change.

---

### Failure 5: Wind Direction and Turbine Orientation Disagreements
- **Symptom**: Turbine rotors point in directions conflicting with the wind compass badge or flow streamlines.
- **Root Cause**:
  - **Coordinate Space Discrepancy**:
    - Meteorological wind direction is defined clockwise from North ($0^\circ = \text{North}$, $90^\circ = \text{East}$, $270^\circ = \text{West}$). Wind blowing **from** $270^\circ$ travels **towards** $90^\circ$ (East).
    - 3D glTF models in CesiumJS are oriented relative to local East-North-Up (ENU) coordinates.
    - Depending on which tool generated `wind_turbine.glb`, the rotor face may point along $+Y$, $+Z$, or $-X$. In `CesiumGlobeView.tsx`, a manual $-90^\circ$ offset was patched:
      `const gltfHeadingDeg = (windDirectionDeg - 90 + 360) % 360;`
    - In `Screen3Layout.tsx`, 2D SVG turbine markers used `angleDeg` without the $-90^\circ$ correction, causing 2D Leaflet markers and 3D Cesium models to display conflicting yaw headings under identical wind conditions.

---

### Failure 6: Turbine Models Not Matching Physical Scale
- **Symptom**: Visual 3D turbines appear oversized, undersized, or detached from foundations on certain terrain zooms.
- **Root Cause**:
  - `CesiumGlobeView.tsx` uses `scale: modelScale` where:
    `const modelScale = Math.max(0.8, Math.min(1.8, rotorDiameter / 120.0));`
    This assumes the raw `wind_turbine.glb` asset is modeled exactly with $D=120\,\text{m}$ at scale `1.0`.
  - In reality, the imported GLB model has arbitrary internal bounding boxes. To compensate, procedural cylinders for towers and concrete pads were manually layered underneath the GLB model. On high zoom, the procedural mast and the GLB mast can z-fight or exhibit visual clipping.
  - Minimum pixel size is set to `64` (`minimumPixelSize: 64`), which deliberately forces the turbine to render unnaturally large when viewing from regional altitudes ($>10\,\text{km}$) so it does not disappear.

---

### Failure 7: Quantum Optimization Operating on Unchecked Coordinates
- **Symptom**: Quantum optimization runs and returns solutions on sites that violate slope, infrastructure, or conservation rules.
- **Root Cause**:
  - In `backend/app/api/optimize.py`, the endpoint `POST /api/optimize` takes a list of `sites` from the request body and passes them directly to `_sync_optimize_worker`.
  - It does **not** invoke `overpass_client`, `copernicus_dem`, or `protected_planet_client` during optimization.
  - If the frontend passes unpruned candidates (or if `Screen1Site` failed to prune candidates), QAOA will happily place turbines on steep cliffs or inside residential settlements because those penalties were omitted from the Ising cost Hamiltonian.

---

### Failure 8: Silent Fallback to Classical Solver on Realistic Problems
- **Symptom**: The UI reports "Quantum WS-QAOA Optimization" converged in $0.05\,\text{s}$ with 100 iterations on a 20-turbine farm.
- **Root Cause**:
  - In `core/wsqaoa.py`:
    ```python
    if not _QISKIT_AVAILABLE or N > 12 or K > 8:
        c_star = continuous_relaxation(h_arr, J_arr, K)
        top_k = set(np.argsort(c_star)[-K:].tolist())
        bs = "".join("1" if i in top_k else "0" for i in range(N))
        bs = repair(bs, K=K, W=W)
        return bs, energy, {bs: 1024}, float(time.time() - start_time)
    ```
  - Statevector quantum simulation on $N > 12$ qubits is computationally expensive in an HTTP request cycle. The code silently bypasses QAOA entirely and runs classical continuous relaxation ($c^* \in [0, 1]^N$) with greedy repair.
  - The frontend displays quantum circuit depth ($p=2$), Hadamard initialization, and mixer unitary steps (`γ1`, `β1`, `γ2`, `β2`), creating a completely synthetic narrative of quantum execution.

---

## 2. Comprehensive Inventory: What Is Working, Broken, and Fake

### A. What Is Working (REAL & Verified)
1. **Copernicus DEM 30m Elevation & Slope**: Queries Open-Meteo elevation service, computes spatial gradients with Horn's 3x3 algorithm, and caches samples in SQLite.
2. **Open-Meteo 100m Atmospheric Telemetry**: Fetches real hub-height wind speeds, wind directions, air densities, and surface pressures globally.
3. **ISRIC SoilGrids Geotechnical Bearing Telemetry**: Queries bulk density and soil texture fractions, calculates empirical bearing capacity, and recommends foundation types.
4. **Vectorized Jensen Wake Model & NREL FLORIS 4.x Engine**: Accurate aerodynamic equations, quadratic deficit superposition, and Weibull AEP integration.
5. **FastAPI & SQLite Persistence**: Robust CRUD operations for project saving, loading, editing, and deletion.
6. **Local Map Tile Proxy & Satellite Imagery Caching**: High-speed tile proxy and composite stitching for Cesium globe draping.
7. **Ising Hamiltonian Formulation**: Valid mathematical transformation from binary quadratic micro-siting objectives into spin matrices $(h, J)$.

---

### B. What Is Broken (Requires Engineering Fix)
1. **Perimeter Setbacks & Corner Clumping**: Setback is set to $0.5D$ ($60\,\text{m}$), causing turbines to sit right on parcel borders.
2. **Dual Conflicting Optimization Endpoints**: Redundant endpoints in `optimize.py` vs `layout.py` with diverging schemas and preprocessing.
3. **Client-Side Candidate Fallback (`geometry.ts`)**: Generates candidates in browser when API is slow, completely bypassing GIS exclusion masks.
4. **Yaw Angle Convention Inconsistencies**: 2D Leaflet SVG markers vs 3D Cesium GLTF assets have conflicting heading reference offsets.
5. **Overpass Settlement Fallbacks**: Single center-point fallback fails to protect rural habitations outside village centers.

---

### C. What Is Fake (Simulated / Hardcoded / Decorative)
1. **Global Wind Atlas 3.0 Client (`global_wind_atlas.py`)**: Hardcoded regional `if/elif` blocks; does not query DTU/World Bank raster data.
2. **ESA WorldCover 10m Client (`worldcover_client.py`)**: Hardcoded coordinate bounding-box heuristics; does not query ESA land cover rasters.
3. **Protected Planet WDPA Client (`protected_planet_client.py`)**: Static list of 10 Indian parks; does not query UNEP-WCMC or state eco-sensitive zones.
4. **Quantum QAOA Execution for $N > 12$**: Displays simulated quantum convergence while executing classical continuous relaxation.
5. **Leaflet & Cesium Wake Lines**: Decorative static trapezoids and SVG arcs rather than physical velocity deficit contour fields.

---

## 3. Engineering Action Plan: Keep, Delete, Rebuild

### D. What Should Be Deleted
1. **Client-Side Turbine Synthesizer**: Remove `generatePolygonEnclosedTurbines()` in `src/utils/geometry.ts`. The frontend must never manufacture engineering coordinates.
2. **Legacy Optimize Endpoint**: Delete `_sync_optimize_worker` and `/api/optimize` in `backend/app/api/optimize.py` to eliminate dual-path routing.
3. **Synthetic Harmonic Boundary Generator**: Delete `_generate_engineering_parcel_boundary()` in `village_boundary_client.py`. If official cadastre is missing, return a verified convex hull of surveyed points or report cadastral unavailability.
4. **Hardcoded Protected Planet Array**: Delete static `PROTECTED_AREAS_INDIA` in `protected_planet_client.py`.

---

### E. What Should Be Preserved
1. **FastAPI Architecture & SQLite Cache**: Clean asynchronous design, fast tile proxying, and reliable SQLite caching.
2. **NREL FLORIS 4.x Engine & Turbine Catalogue**: Accurate physical power and thrust curves for industrial turbines.
3. **Vectorized Jensen Aerodynamics**: High-speed, robust NumPy matrix calculations.
4. **ISRIC SoilGrids & Copernicus DEM Client Pipelines**: Authentic external REST integrations with local caching.
5. **Ising Hamiltonian & WS-QAOA Algorithm**: Mathematically sound quantum algorithm.
6. **CesiumJS Digital Twin Infrastructure**: Smooth 3D WebGL rendering with satellite draping and responsive camera controls.

---

### F. What Must Be Rebuilt
1. **Unified Engineering Feasibility Pipeline**: A single authoritative backend endpoint that executes the complete sequence:
   `Boundary Ingestion -> Terrain & Slope Mask -> OSM Setback Mask -> Buildable Candidate Grid -> QUBO -> Solver -> FLORIS AEP`.
2. **True Land Cover & Conservation Integration**: Connect real Cloud-Optimized GeoTIFFs (COG) or STAC APIs for ESA WorldCover and Protected Planet.
3. **Physical Setback Standards**: Rebuild boundary setback logic to enforce $\ge 1.5D$ ($180\,\text{m}$) property setbacks and $\ge 500\,\text{m}$ dwelling setbacks.
4. **Physical Dynamic 2D/3D Wake Plumes**: Render wake contours based on actual FLORIS velocity deficit decay fields.
5. **Honest Quantum Simulation & QPU Abstraction**: Clearly separate true statevector simulation ($N \le 12$) from classical relaxation or Qiskit Runtime quantum hardware backends.

---

## 4. Recommended Implementation Order (Phased Roadmap)

```
Phase 1: Pipeline Unification & Setback Enforcement
└── Consolidate API endpoints into a single pipeline.
└── Enforce 1.5D parcel setbacks and 500m residential setbacks in geo_engine.py.
└── Remove frontend coordinate synthesis in geometry.ts.

Phase 2: True Environmental & Cadastral Ingestion
└── Connect real raster/STAC queries for ESA WorldCover 10m and WDPA.
└── Implement robust fallback for village boundaries using cadastral survey records.
└── Ensure Overpass API comprehensively queries rural structures.

Phase 3: Aerodynamic Wake & Visualization Realism
└── Synchronize 2D and 3D turbine yaw angles to standard meteorological upwind orientation.
└── Generate dynamic FLORIS velocity deficit contours in Leaflet and Cesium.
└── Ensure 3D turbine GLTF scales match exact physical tower and rotor dimensions.

Phase 4: Quantum Optimization & Scaling Transparency
└── Separate quantum statevector simulation from classical relaxation in UI telemetry.
└── Provide transparent solver selection (QAOA Simulator vs SLSQP Relaxed vs Simulated Annealing).
└── Calibrate QUBO penalty multipliers to prevent spacing violations under high turbine densities.
```
