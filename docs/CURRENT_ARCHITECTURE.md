# AeroQuantum-Wind — Current System Architecture

**Date**: 2026-10-06  
**Auditor**: Senior Wind-Farm GIS / Software Engineer  
**Document**: Architecture Decomposition & Component Inventory

---

## 1. High-Level Architecture Overview

AeroQuantum-Wind is structured as a decoupled client-server web application with a specialized Python scientific/geospatial backend and a modern React/CesiumJS frontend:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND CLIENT (React 18 + TS)                  │
│  ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Workflow Controller │  │ 2D Leaflet Maps  │  │ 3D Cesium Globe  │  │
│  │     (App.tsx)        │  │ (Screens 1 & 3)  │  │    (Screen 5)    │  │
│  └──────────┬───────────┘  └─────────┬────────┘  └────────┬─────────┘  │
│             │                        │                    │            │
│  ┌──────────▼────────────────────────▼────────────────────▼─────────┐  │
│  │                    API Service (src/services/api.ts)              │  │
└─────────────┬──────────────────────────────────────────────────────────┘
              │ JSON / HTTP REST
┌─────────────▼──────────────────────────────────────────────────────────┐
│                      BACKEND SERVER (FastAPI 0.115+)                   │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       API Routers                                │  │
│  │  /api/geo      /api/optimize      /api/layout      /api/projects │  │
│  └──────────┬────────────────────────────┬──────────────────────────┘  │
│             │                            │                             │
│  ┌──────────▼──────────────┐  ┌──────────▼──────────────────────────┐  │
│  │   GIS & Land Engine     │  │    Quantum & Wake Engines           │  │
│  │  - Copernicus DEM       │  │    - Jensen Analytical (core)       │  │
│  │  - OSM Overpass         │  │    - NREL FLORIS 4.x (Gaussian)     │  │
│  │  - ISRIC SoilGrids      │  │    - WS-QAOA & Ising (core/wsqaoa)  │  │
│  │  - Candidate Gen Engine │  │    - 1-Opt Repair (post_processor)  │  │
│  └──────────┬──────────────┘  └──────────┬──────────────────────────┘  │
│             │                            │                             │
│  ┌──────────▼────────────────────────────▼──────────────────────────┐  │
│  │             Persistence & Local Tile/Elevation Cache             │  │
│  │       SQLite (aeroquantum.db) + Raw JPEG Tile Proxy Storage       │  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend Component Architecture

### A. Core Routing Layer (`backend/app/api/`)
1. **`geo.py`**:
   - `GET /api/geo/geocode`: Proxy to Nominatim with rate limiting and in-memory LRU caching.
   - `GET /api/geo/village-boundary`: Calls `village_boundary_client.py` to retrieve official administrative borders and compute geodesic area.
   - `GET /api/geo/telemetry`: Calls `telemetry.py` for atmospheric wind speed ($100\,\text{m}$), direction, temperature, and pressure via Open-Meteo.
   - `GET /api/geo/soil-telemetry`: Calls `soil_client.py` for ISRIC SoilGrids geotechnical properties.
   - `POST /api/geo/candidates`: Basic equirectangular grid generator (legacy candidate builder).
   - `POST /api/geo/feasibility`: Calls `CandidateGenerationEngine` to evaluate terrain slope, residential buffers, powerline setbacks, and waterway exclusions.
   - `GET /api/geo/tiles/{layer}/{z}/{x}/{y}`: Reverse tile proxy caching Esri satellite, OpenTopoMap, and CartoDB imagery to local disk (`backend/data/tiles/`).
   - `GET /api/geo/site-imagery`: Stitches $5 \times 5$ satellite tiles into a single high-resolution texture for Cesium 3D drape.
   - `GET /api/geo/site-imagery-meta`: Returns exact geodetic bounding box `[west, south, east, north]` for the stitched satellite texture.

2. **`optimize.py`**:
   - `POST /api/optimize`: Primary solver endpoint invoked by `src/services/api.ts`.
   - Computes Jensen wake matrix $W_{ij}$, builds Ising Hamiltonian $(h, J)$, executes WS-QAOA (or continuous relaxation), runs greedy repair, and returns optimal turbine coordinates, AEP (GWh), wake loss %, and printable blueprint HTML.
   - Maintains an in-memory `JOB_STORE` dictionary for retrieving job blueprints.

3. **`layout.py`**:
   - `POST /api/initial-layout`: Computes candidate grid, evaluates exclusions, runs preliminary FLORIS wake simulation, and returns initial layout telemetry.
   - `POST /api/qaoa-optimize`: Alternative solver endpoint invoking `HybridWindFarmOptimizer` in `geo_engine.py`. Produces rich convergence step history, decision variable states, and constraint breakdown.

4. **`projects.py`**:
   - Complete CRUD interface for wind farm projects stored in SQLite (`backend/data/aeroquantum.db`).
   - Supports user ownership (`user_id`), turbine placement JSON serialization, boundary polygon storage, and geotechnical soil metadata.

5. **`auth.py`**:
   - Lightweight user authentication using PBKDF2-HMAC-SHA256 password hashing and token-based session persistence in SQLite.

---

### B. Engineering & Aerodynamics Modules (`core/` & `backend/app/engineering/`)
1. **`core/aerodynamics.py`**:
   - Vectorized implementation of the Katic-Højstrup-Jensen (1986) kinematic wake model.
   - Implements `pairwise_wake_matrix()` computing pairwise velocity deficits:
     $$\frac{\Delta v}{v_0} = \frac{1 - \sqrt{1 - C_t}}{\left(1 + \frac{2kx}{D}\right)^2}$$
     for downstream points within the expanding conical wake zone $R_{\text{wake}}(x) = \frac{D}{2} + kx$.
   - Includes unit vector directional decomposition supporting both compass meteorological ($0^\circ$ North) and Cartesian polar angles.

2. **`backend/app/engineering/floris_engine.py`**:
   - Implements Bastankhah & Porté-Agel (2014, 2016) Gaussian wake deficit model.
   - Contains manufacturer-certified power $P(u)$ and thrust coefficient $C_T(u)$ performance tables for:
     - **GE Vernova 2.5-120** ($D=120\,\text{m}$, $H=110\,\text{m}$, $2500\,\text{kW}$)
     - **Vestas V110-2.0** ($D=110\,\text{m}$, $H=95\,\text{m}$, $2000\,\text{kW}$)
     - **NREL 5-MW Reference** ($D=126\,\text{m}$, $H=90\,\text{m}$, $5000\,\text{kW}$)
     - **IEA 15-MW Offshore** ($D=240\,\text{m}$, $H=150\,\text{m}$, $15000\,\text{kW}$)
     - **Siemens Gamesa SG 3.4-132** ($D=132\,\text{m}$, $H=114\,\text{m}$, $3465\,\text{kW}$)
   - Integrates Annual Energy Production (AEP in GWh) numerically over 16 wind rose directional sectors and Weibull wind speed distributions.
   - Builds pairwise quadratic wake interference matrix $Q_{ij}$ for QAOA.

3. **`core/quantum_hamiltonian.py`**:
   - Constructs the Ising Cost Hamiltonian $H = \sum_i h_i Z_i + \sum_{i<j} J_{ij} Z_i Z_j + \text{offset}$.
   - Auto-calibrates penalty weights:
     - Turbine count penalty: $\lambda_{\text{turb}} = 1.5 \cdot \max_{i,j} |W_{ij}|$
     - Proximity exclusion penalty: $\lambda_{\text{prox}} = 2.0 \cdot \lambda_{\text{turb}} + 0.5$
   - Maps binary optimization variables $x_i \in \{0, 1\}$ to quantum spins $Z_i \in \{+1, -1\}$ via $x_i = \frac{I - Z_i}{2}$.

4. **`core/wsqaoa.py`**:
   - Implements Warm-Started QAOA with $XY$ mixer preserving Hamming weight $\sum x_i = K$.
   - Initializes qubits in product state $| \psi_0 \rangle = \bigotimes_{i=1}^N R_Y(\theta_i) |0\rangle$ using continuous relaxation angles $\theta_i = 2 \arcsin(\sqrt{c^*_i})$.
   - Implements alternating $R_{ZZ}(2\gamma J_{ij})$ cost unitaries and Givens rotation $XY$ mixers.
   - Optimizes circuit parameters using SciPy COBYLA over Qiskit Aer statevector simulation.
   - Provides automatic branch to classical continuous relaxation when $N > 12$ or $K > 8$.

5. **`core/post_processor.py`**:
   - Implements greedy 1-opt repair ensuring exact target turbine count $K$ while minimizing marginal wake penalties.
   - Computes net and gross AEP in kWh/GWh and calculates wake deficit percentage.

---

### C. GIS & External Services (`backend/app/gis/`)
1. **`village_boundary_client.py`**:
   - Queries OSM Nominatim API with `polygon_geojson=1`. Resolves administrative polygons or enclosing mandal/district boundaries. Computes spherical polygon surface area and perimeter.
2. **`copernicus_dem.py`**:
   - Queries Open-Meteo Elevation API (backed by Copernicus DEM GLO-30m and SRTM). Caches points in SQLite table `dem_cache`. Computes 2D spatial elevation gradients, slope angles, and aspect azimuths via Horn's 3x3 kernel.
3. **`overpass_client.py`**:
   - Queries OpenStreetMap Overpass API for infrastructure: buildings, residential settlements, high-voltage powerlines, highways, and waterways. Caches query envelopes in `osm_exclusion_cache`.
4. **`soil_client.py`**:
   - Queries ISRIC SoilGrids 250m v2.0 REST API for geotechnical fractions and calculates ultimate bearing capacity ($q_{\text{ult}}$ in kPa) and required foundation type (Gravity Base vs Deep Piled).
5. **`global_wind_atlas.py`**:
   - Provides long-term 10-year climatological baseline wind parameters and 16-sector wind rose distributions. (Uses regional mathematical heuristics).
6. **`protected_planet_client.py`**:
   - Evaluates proximity to major statutory conservation zones. (Uses static list of 10 Indian national park centroids).

---

## 3. Frontend Component Architecture

### A. Application State Machine (`src/App.tsx`)
Manages global workflow navigation across 8 discrete screens synchronized with browser history and URL hash:
- `home`: Opening "Create New Project" Hero Screen.
- `dashboard`: Dedicated multi-project dashboard with key performance indicators and draft purge.
- `s1_site`: Screen 1 — Interactive GIS site map with geocoding search and radius/boundary selection.
- `s2_config`: Screen 2 — Turbine model selection, hub height, rotor diameter, and farm sizing.
- `s3_analysis`: Screen 3 — Baseline layout analysis with candidate grid and wake interaction preview.
- `s4_optimize`: Screen 4 — Quantum WS-QAOA convergence visualization and decision variable state.
- `s5_inspect`: Screen 5 — Final micro-sited layout inspection with 2D Leaflet and 3D Cesium globe.
- `s6_blueprint`: Screen 6 — Engineering blueprint export (HTML, GeoJSON, CSV, JSON).

### B. 3D Digital Twin (`src/components/gis/CesiumGlobeView.tsx`)
- High-performance CesiumJS WebGL viewer.
- Fetches and drapes high-resolution composite satellite imagery over the concession boundary.
- Renders 3D wind turbines using `/assets/models/wind_turbine.glb`, procedural structural monopile cylinders, concrete foundation pads, and nacelle housing boxes.
- Enforces strict upwind yaw orientation aligned with atmospheric wind vectors.
- Renders draped downwind aerodynamic Jensen wake trapezoid footprints on terrain.

### C. Client-Side Geometry Utilities (`src/utils/geometry.ts`)
- Contains ray-casting point-in-polygon testing, distance-to-segment algorithms, and geodesic area/perimeter calculators.
- **Architectural Risk**: Contains `generatePolygonEnclosedTurbines()`, an aggressive client-side candidate generator and spacing relaxation loop that can bypass backend GIS checks if called as a fallback.

---

## 4. Database Schema Definition

The SQLite database (`backend/data/aeroquantum.db`) maintains 6 primary tables:

1. **`projects`**:
   - `id` (TEXT PRIMARY KEY), `user_id` (INTEGER), `name` (TEXT), `location_name` (TEXT), `latitude` (REAL), `longitude` (REAL), `area_km2` (REAL), `turbine_count` (INTEGER), `turbine_model` (TEXT), `rotor_diameter` (REAL), `hub_height` (REAL), `spacing_d` (REAL), `wind_speed` (REAL), `wind_direction` (REAL), `suitability` (TEXT), `gross_aep` (REAL), `net_aep` (REAL), `wake_loss_percent` (REAL), `turbines_json` (TEXT), `boundary_json` (TEXT), `soil_bearing_capacity_kpa` (REAL), `usda_texture_class` (TEXT), `foundation_type` (TEXT), `soil_hazard_level` (TEXT), `status` (TEXT).
2. **`users`**:
   - `id` (INTEGER PRIMARY KEY), `username` (TEXT UNIQUE), `email` (TEXT UNIQUE), `password_hash` (TEXT), `created_at` (TIMESTAMP).
3. **`sessions`**:
   - `token` (TEXT PRIMARY KEY), `user_id` (INTEGER), `expires_at` (REAL), `created_at` (TIMESTAMP).
4. **`dem_cache`**:
   - `lat_round` (REAL), `lon_round` (REAL), `elevation_m` (REAL), `source` (TEXT), `updated_at` (TIMESTAMP). PRIMARY KEY (`lat_round`, `lon_round`).
5. **`osm_exclusion_cache`**:
   - `cache_key` (TEXT UNIQUE PRIMARY KEY), `center_lat` (REAL), `center_lon` (REAL), `radius_km` (REAL), `features_json` (TEXT), `created_at` (TIMESTAMP).
6. **`india_wind_hotspots`**:
   - `id` (TEXT PRIMARY KEY), `state` (TEXT), `district` (TEXT), `location_name` (TEXT), `latitude` (REAL), `longitude` (REAL), `annual_mean_wind_mps` (REAL), `wind_direction_deg` (REAL), `weibull_a` (REAL), `weibull_k` (REAL), `capacity_factor_est` (REAL), `terrain_type` (TEXT), `elevation_m` (REAL), `grid_proximity_km` (REAL), `niwe_wind_class` (TEXT), `description` (TEXT).
