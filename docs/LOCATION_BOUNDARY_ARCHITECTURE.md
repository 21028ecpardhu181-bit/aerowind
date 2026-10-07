# AeroQuantum-Wind — Location Resolution & Authoritative Boundary Architecture

**Phase**: Phase 2 — Location Resolution + Authoritative Village Boundary Engine  
**Author**: Senior Geospatial / Renewable-Energy GIS Engineer  
**Date**: 2026-10-06  
**Status**: APPROVED & OPERATIONAL (100% Tests Passing)

---

## 1. Core Engineering Principle

> **Critical Axiom**: A village boundary is **NOT** the wind-farm development area. It is strictly the initial geographic **SEARCH ENVELOPE**.
> 
> The system must never assume:
> $$\text{inside village boundary} \implies \text{suitable}$$
> $$\text{inside village boundary} \implies \text{buildable}$$
> 
> The actual buildable area is determined downstream by Phase 3 (Site Screening, Hard Exclusions, and Buildable Mask).

```mermaid
flowchart TD
    In[User Input: Text / GPS / Admin / Manual] --> LocRes[Location Resolver]
    LocRes --> AdminID[Administrative Identity & State/District Hierarchy]
    AdminID --> SOI_Check{Survey of India Ingested?}
    SOI_Check -->|Yes| SOI_Match[Hierarchical Cadastral Match]
    SOI_Check -->|No| OSM_Check{OSM Admin Polygon Available?}
    OSM_Check -->|Yes| OSM_Fall[OSM Fallback Polygon: ADVISORY_ONLY]
    OSM_Check -->|No| Unavail[Status: UNAVAILABLE | geometry: null]
    SOI_Match --> GeomVal[Geometry Validation & Topology Repair]
    OSM_Fall --> GeomVal
    GeomVal --> ProjEngine[Local UTM Projection: EPSG:32642-46]
    ProjEngine --> GPS_Check{GPS Coordinates Supplied?}
    GPS_Check -->|Inside| Envelope[Search Envelope for Phase 3]
    GPS_Check -->|Outside| Mismatch[Status: LOCATION_BOUNDARY_MISMATCH]
    Envelope --> Phase3[Downstream Phase 3 Screening]
```

---

## 2. Input Modes Supported

The location and boundary subsystem supports five distinct input modes:

| Mode | Input Parameters | Processing Flow | Authority Classification |
| :--- | :--- | :--- | :--- |
| **A. Text Search** | `query="Batlapalem, Amalapuram, Andhra Pradesh"` | Nominatim geocoding with multi-match ambiguity detection $\to$ hierarchy extraction $\to$ SOI boundary query. | Dependent on boundary match (`Survey of India` or `OpenStreetMap`) |
| **B. Coordinate Input** | `latitude=16.9676, longitude=81.8138` | WGS84 range validation $\to$ reverse geocoding $\to$ administrative hierarchy $\to$ boundary lookup $\to$ point-in-polygon containment test. | `Survey of India` / `OpenStreetMap` |
| **C. Device GPS** | Browser / mobile GPS coordinates | Same as Mode B, tagged with source `Device GPS Telemetry / Nominatim Reverse`. | `Survey of India` / `OpenStreetMap` |
| **D. Structured Administrative** | `{"state": "...", "district": "...", "subdistrict": "...", "village": "..."}` | Exact hierarchy matching against SOI registry; avoids geocoding ambiguity. | `Survey of India` |
| **E. Manual Analysis Area** | GeoJSON `Polygon` or `MultiPolygon` | Geometry validation $\to$ local UTM projection $\to$ metric area calculation. Strictly tagged as `MANUAL_ANALYSIS_AREA`. | `USER_DEFINED` (**Never labelled as official**) |

---

## 3. Strict Separation: Geocoder vs. Boundary Authority

AeroQuantum-Wind enforces strict separation of responsibilities between geocoding services and boundary cadastre:

- **Geocoder (OpenStreetMap Nominatim)**:
  - Answers: *"Where is this place approximately?"*
  - Provides approximate centroid coordinates and parent administrative hierarchy (`state`, `district`, `subdistrict`).
  - **Never** dictates the authoritative boundary polygon for statutory engineering screening.
- **Authoritative Boundary (Survey of India)**:
  - Answers: *"What is the statutory administrative cadastral polygon?"*
  - Primary reference: Survey of India Village Boundary Database (1:50,000 scale).
  - Mode of access: `MANUAL_REQUIRED` via official SOI portal downloads and offline shapefile/GeoJSON ingestion.
- **Fallback Boundary (OpenStreetMap Admin Polygons)**:
  - Answers: *"Is there an advisory community polygon when SOI is unindexed?"*
  - Strictly labelled: `authority = "OpenStreetMap"`, `source_status = "PARTIAL"`, `engineering_status = "ADVISORY_ONLY"`.
  - Never silently replaces or masquerades as an official Survey of India boundary.
- **Visualization (Satellite / Google 3D Tiles)**:
  - Answers: *"How does the site appear visually?"*
  - Visualization only; never provides engineering boundary polygons.

---

## 4. Search Result Ambiguity Resolution

The location resolver **never** silently selects the first result when a query is ambiguous.

### Ambiguity Axiom:
If a search query (e.g., *"Rampur"*) yields multiple results belonging to different states, different districts, or separated by $> 25\,\text{km}$, the system returns:
```json
{
  "status": "AMBIGUOUS_LOCATION",
  "candidates": [
    {
      "display_name": "Rampur, Uttar Pradesh, India",
      "latitude": 28.8,
      "longitude": 79.02,
      "state": "Uttar Pradesh",
      "district": "Rampur"
    },
    {
      "display_name": "Rampur, Gaya, Bihar, India",
      "latitude": 24.79,
      "longitude": 85.0,
      "state": "Bihar",
      "district": "Gaya"
    }
  ],
  "error_detail": "Query 'Rampur' matches multiple distinct locations across different districts/states."
}
```
The caller or frontend user must select the desired candidate before boundary retrieval proceeds.

---

## 5. Survey of India Ingestion & Administrative Matching Pipeline

### Ingestion Interface (`POST /api/geo/boundary/ingest`)
Accepts GeoJSON FeatureCollections, Shapefile GeoJSON exports, or administrative dictionaries.
- Preserves statutory fields: `village_id`, `village_name`, `state`, `district`, `subdistrict`, `geometry`, `source`, `dataset`, `version`, `retrieved_at`, `crs`.
- **Non-fabrication invariant**: If an attribute is missing in the source dataset, it is preserved as `None` / `UNKNOWN`. Missing data is never invented.
- Validates geometry and computes projected UTM metrics before saving to SQLite `authoritative_boundary_cache`.

### 4-Tier Matching Priority
1. **Tier 1 (Stable ID)**: Exact match on `village_id` (Census 2011 code or LGD code).
2. **Tier 2 (Full Hierarchy)**: Exact match on `state` + `district` + `subdistrict` + `village_name`.
3. **Tier 3 (State + District + Village)**: Exact match on `state` + `district` + `village_name`.
4. **Tier 4 (Controlled Fuzzy)**: Levenshtein similarity ($\ge 0.82$) strictly confined **within the parent state/district**.
- **Global fuzzy matching on village name alone is strictly forbidden.**
- If multiple candidates match within the hierarchy, the system returns `AMBIGUOUS_BOUNDARY_MATCH` with candidates.

---

## 6. Boundary Status Model

The boundary engine returns one of the following explicit states:

| Status Code | Meaning | Downstream Action |
| :--- | :--- | :--- |
| `BOUNDARY_FOUND` | Valid authoritative SOI or advisory OSM boundary loaded | Proceed to Phase 3 search envelope |
| `BOUNDARY_NOT_FOUND` | Locality resolved, but no boundary exists in registry or OSM | Siting blocked; prompt for manual area |
| `AMBIGUOUS_LOCATION` | Geocoder returned multiple geographically distant places | User must select specific candidate |
| `AMBIGUOUS_BOUNDARY_MATCH` | Multiple boundary polygons match within district/state | User must select specific village polygon |
| `LOCATION_BOUNDARY_MISMATCH` | Supplied GPS coordinate lies outside matched polygon | Block siting or prompt to adjust point |
| `SOURCE_UNAVAILABLE` | External boundary source unreachable or timed out | Fail safely; do not fabricate |
| `INVALID_GEOMETRY` | Boundary geometry fails topology validation and cannot be repaired | Reject boundary |
| `MANUAL_AREA` | User provided explicit manual analysis polygon | Proceed as `MANUAL_ANALYSIS_AREA` |
| `UNAVAILABLE` | Neither authoritative nor fallback boundary exists | Siting blocked |

---

## 7. Geometry Validation & Topology Repair

Implemented in [`backend/app/gis/geometry_validation.py`](file:///home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/backend/app/gis/geometry_validation.py):

1. **RFC 7946 Standard**: Standard GeoJSON `[longitude, latitude]` format. Inverted `[lat, lon]` inputs are detected and normalized.
2. **Closed Rings**: Rings missing identical start/end vertices are closed by appending the start vertex.
3. **Duplicate Vertices**: Adjacent duplicate coordinates within $10^{-9}$ degrees are deduplicated.
4. **Winding Order**: Exterior rings are verified as counter-clockwise (CCW); interior holes are verified as clockwise (CW).
5. **Bowtie / Self-Intersection Repair**: Non-adjacent segment crossings are detected via 2D cross-product line intersection tests. Bowtie/figure-eight crossings are decomposed into simple loops, retaining the dominant component, and recording `geometry_repaired = True`.
6. **MultiPolygon & Hole Preservation**:
   - MultiPolygons with disconnected parcels (e.g. Bommuru's upland enclave) are preserved intact.
   - Interior holes (donut polygons) are preserved. Ray-casting point-in-polygon logic tests:
     $$\text{Inside Polygon} \iff (\text{Inside Exterior Ring}) \land \neg(\text{Inside Any Interior Hole})$$
   - A point located inside an interior hole returns `False`.

---

## 8. CRS Management & Projected Engineering Geodesy

Implemented in [`backend/app/gis/projection.py`](file:///home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/backend/app/gis/projection.py):

### Invariants:
- Interchange CRS is strictly **WGS84 (EPSG:4326)**.
- **Never calculate engineering distances in degrees**: Expressions like $\text{dist} = |lat_1 - lat_2|$ are strictly prohibited.
- All distances, setbacks, and buffer radii are computed in **metres**.
- Areas are computed in **square metres ($m^2$)** and **square kilometres ($km^2$)**.

### Dynamic Local UTM Zone Selection for India:
$$\text{zone} = \left\lfloor \frac{\text{longitude} + 180^\circ}{6^\circ} \right\rfloor + 1$$

| Region | Longitude Span | UTM Zone | EPSG Projected CRS |
| :--- | :--- | :--- | :--- |
| **Gujarat / Western Rajasthan** | $66^\circ\text{E} - 72^\circ\text{E}$ | Zone 42N | `EPSG:32642` |
| **Maharashtra / Karnataka / Central Rajasthan** | $72^\circ\text{E} - 78^\circ\text{E}$ | Zone 43N | `EPSG:32643` |
| **Andhra Pradesh / Telangana / Tamil Nadu / Odisha** | $78^\circ\text{E} - 84^\circ\text{E}$ | Zone 44N | `EPSG:32644` |
| **West Bengal / Bihar / Eastern Odisha** | $84^\circ\text{E} - 90^\circ\text{E}$ | Zone 45N | `EPSG:32645` |
| **Assam / Northeast** | $90^\circ\text{E} - 96^\circ\text{E}$ | Zone 46N | `EPSG:32646` |

### Geodesy & Projection Precision:
- Transverse Mercator series expansion delivers sub-millimetre ($< 0.001\,\text{m}$) round-trip accuracy between WGS84 and UTM.
- Ellipsoidal geodesic distance uses Vincenty's inverse formula on the WGS84 ellipsoid ($a = 6378137.0\,\text{m}$, $f = 1/298.257223563$).
- Planar polygon area uses the Shoelace formula on projected metric UTM vertices.

---

## 9. Location Point Validation (`LOCATION_BOUNDARY_MISMATCH`)

When explicit GPS coordinates (`latitude`, `longitude`) are supplied:
1. Coordinates are checked against valid ranges $[-90, 90]$ and $[-180, 180]$.
2. Locality and administrative hierarchy are resolved.
3. The authoritative boundary dataset is queried.
4. Point containment is verified against the boundary polygon using `is_point_in_polygon_geometry`.
5. If the point lies outside the polygon:
   - System returns `status = "LOCATION_BOUNDARY_MISMATCH"`.
   - `containment_verified = False`.
   - `distance_to_boundary_m` is computed in metres.
   - Diagnostic detail reports the exact metric distance outside the boundary.

---

## 10. Database Caching (`authoritative_boundary_cache`)

Persistent cache implemented in SQLite (`backend/app/db.py`):
```sql
CREATE TABLE IF NOT EXISTS authoritative_boundary_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    state TEXT,
    district TEXT,
    subdistrict TEXT,
    village TEXT,
    village_id TEXT,
    authority TEXT NOT NULL,
    source_status TEXT NOT NULL,
    dataset TEXT,
    version TEXT,
    crs TEXT DEFAULT 'EPSG:4326',
    projected_crs TEXT,
    geometry_type TEXT NOT NULL,
    geometry_json TEXT NOT NULL,
    area_m2 REAL,
    area_km2 REAL,
    perimeter_km REAL,
    geometry_repaired INTEGER DEFAULT 0,
    retrieved_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
- Only valid, verified geometries are cached.
- **Never cache a synthetic or fabricated boundary.**

---

## 11. Elimination of Client-Side Boundary Synthesis

Phase 0 identified client-side synthetic boundary generation in `src/services/api.ts` (`generateEngineeringConcessionBoundary` multi-harmonic oval fallback).
- **Remediated**: The synthetic fallback has been removed from the authoritative boundary retrieval path.
- When no boundary is available, both backend and frontend return `status: "UNAVAILABLE"` with `boundary: null`.
- Frontend maps and displays geometries provided by the backend; it is strictly prohibited from inventing administrative boundaries.

---

## 12. Verification & Test Suite Summary

A dedicated test suite was implemented in [`tests/test_location_boundary_engine.py`](file:///home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/tests/test_location_boundary_engine.py).

All 23 Phase 2 unit & adversarial tests pass:
```
tests/test_location_boundary_engine.py ....................... [100%]
======================= 23 passed, 25 warnings in 12.84s =======================
```

The entire repository regression suite (92 tests total across all phases) passes:
```
tests/test_api.py ...............                                        [ 16%]
tests/test_baselines.py .......                                          [ 23%]
tests/test_environmental_stack.py ......                                 [ 30%]
tests/test_floris_engine.py ......                                       [ 36%]
tests/test_location_boundary_engine.py .......................           [ 61%]
tests/test_physics.py ............                                       [ 75%]
tests/test_provenance_foundation.py ...............                      [ 91%]
tests/test_wsqaoa.py ........                                            [100%]
======================= 92 passed, 29 warnings in 20.45s =======================
```
