# Environmental Suitability & Buildable Land Architecture (Phase 3)

## 1. Executive Architecture Summary

**Phase 3** delivers the **Environmental Suitability & Buildable Land Engine** for **AeroQuantum-Wind**, establishing a scientifically defensible, statutory-compliant spatial screening engine.

### Core Architectural Principle:
> **The administrative village boundary from Phase 2 is strictly the geographic SEARCH ENVELOPE. It is NEVER the wind-farm development area.**
> 
> Land inside a village boundary is **NOT** assumed buildable. The actual buildable mask is computed by strictly clipping and subtracting statutory hard exclusions, ecological zones, terrain constraints, and physical safety setbacks in local projected UTM space (metres).

```
AUTHORITATIVE SEARCH ENVELOPE (Phase 2)
              │
              ▼
   TERRAIN SCREENING (Copernicus DEM 30m GLO-30)
              │  • Slopes > 15° ──> HARD_EXCLUSION (IEC 61400 complex terrain)
              │  • Slopes 8°–15° ──> CONDITIONAL (benching & cut/fill required)
              ▼
   LONG-TERM WIND RESOURCE (NIWE 120m Potential Atlas)
              │  • Climatological baseline screening (WRF / Mast corridors)
              │  • Unindexed zones ──> INFORMATIONAL (on-site mast mandatory)
              ▼
   LAND COVER (ESA WorldCover 10m v200)
              │  • Built-up (50), Water (80), Wetlands (90), Mangroves (95) ──> HARD_EXCLUSION
              │  • Tree cover (10) ──> CONDITIONAL (Forest Conservation Act clearance)
              ▼
   INFRASTRUCTURE & DWELLINGS (OSM Overpass + MNRE 2024 Statutory Setbacks)
              │  • Habitation Cluster (≥15 dwellings) ──> Mandatory 500m buffer
              │  • Roads, Railways, Canals, EHV lines (>66kV) ──> Formula setback:
              │       Distance = Hub Height + 0.5 × Rotor Diameter + 5 meters
              │  • Rural 0-dwellings condition ──> UNVERIFIED_RURAL_ZONE (CONDITIONAL)
              ▼
   CONSERVATION SCREENING (Protected Planet WDPA v4)
              │  • National Park / Wildlife Sanctuary Interior ──> PROHIBITED (HARD_EXCLUSION)
              │  • Eco-Sensitive Zone (ESZ) ──> Mandatory 1.0 km Buffer (HARD_EXCLUSION)
              ▼
   METRIC PROJECTED CLIP & BUILDABLE MASK
              │  • Local UTM projection (EPSG:32642 - 32646 for India)
              │  • Ray-casting containment preserving exterior bounds and interior holes
              ▼
   OUTPUT CONTRACT:
     - overall_status: READY | PARTIAL | UNKNOWN | UNBUILDABLE
     - search_envelope_area_km2, buildable_area_km2, buildable_area_m2
     - buildable_percentage, conditional_percentage, excluded_percentage, unknown_percentage
     - active_constraints (with legal citation & statutory authority)
     - hard_exclusion_reasons, conditional_reasons, data_gaps
     - buildable_mask_geojson (MultiPolygon preserving parcel boundaries)
     - provenance_chain
```

---

## 2. Statutory Constraint Taxonomy & Citation Matrix

All exclusion rules strictly cite real statutory frameworks rather than arbitrary heuristic numbers:

| Constraint Category | Target Feature | Statutory Authority | Governing Reference | Setback / Metric Rule | Classification Tier |
|---|---|---|---|---|---|
| **Habitation** | Settlement Cluster ($\ge 15$ dwellings) | Ministry of New and Renewable Energy (MNRE) | MNRE Guidelines for Development of Onshore Wind Projects (July 4, 2024 Amendment) | Fixed $500\,\text{m}$ buffer | `HARD_EXCLUSION` |
| **Dwellings / Institutions** | Individual Permanent Structures, Schools, Hospitals | MNRE, Govt. of India | MNRE 2024 Guidelines, Infrastructure Safety Distances | $\text{Safety Distance} = H_{\text{hub}} + 0.5 \cdot D_{\text{rotor}} + 5\,\text{m}$ | `HARD_EXCLUSION` |
| **Transportation** | Notified Highways, Major District Roads, Railways | MNRE / MoRTH / Indian Railways | MNRE 2024 Guidelines, Road & Railway Corridors | $\text{Safety Distance} = H_{\text{hub}} + 0.5 \cdot D_{\text{rotor}} + 5\,\text{m}$ | `HARD_EXCLUSION` |
| **Transmission Grid** | Extra High Voltage (EHV) Powerlines ($>66\,\text{kV}$) | MNRE / Central Electricity Authority (CEA) | CEA Transmission Line Safety Clearances | $\text{Safety Distance} = H_{\text{hub}} + 0.5 \cdot D_{\text{rotor}} + 5\,\text{m}$ | `HARD_EXCLUSION` |
| **Ecology / Water** | Rivers, Permanent Lakes, Streams, Wet Margins | MoEFCC / Central Ground Water Board (CGWB) | National River Conservation Plan / Wet Margin Rules | Statutory buffer ($H_{\text{hub}} + 0.5 \cdot D_{\text{rotor}} + 5\,\text{m}$) | `HARD_EXCLUSION` |
| **Protected Areas** | National Parks, Wildlife Sanctuaries, Tiger Reserves | Supreme Court of India / MoEFCC / NBWL | Wildlife (Protection) Act, 1972 & Supreme Court ESZ Orders (2022) | Interior PROHIBITED; $1.0\,\text{km}$ Eco-Sensitive Zone mandatory setback | `HARD_EXCLUSION` |
| **Terrain Slope** | Complex Slope ($> 15^\circ$) | International Electrotechnical Commission (IEC) / MNRE | IEC 61400-1 Site Assessment Standard | Slope $> 15^\circ$ prohibited for crane erection and civil works | `HARD_EXCLUSION` |
| **Moderate Terrain** | Benching Slope ($8^\circ\text{--}15^\circ$) | MNRE Civil Works Manual / IEC 61400-6 | IEC 61400-6 Foundation & Benching Guidelines | Requires cut/fill grading and civil review | `CONDITIONAL` |
| **Forest / Tree Cover** | Forest Land, High Tree Canopy | State Forest Department / MoEFCC | Forest (Conservation) Act, 1980 | Non-Forest Certificate or clearance required | `CONDITIONAL` |
| **Rural Data Gap** | Zero OSM Dwellings in Rural Zone | MNRE / District Revenue Administration | Rural Ground Truth Safeguard | Satellite visual inspection mandatory to prevent dwelling impingement | `CONDITIONAL` |
| **Missing Raster / API Fail** | Failed DEM or Failed Infrastructure Query | Survey of India / ESA / OSM | Non-Fabrication Invariant | API failure requires cadastral ground survey; land clearance NEVER assumed | `UNKNOWN` |

---

## 3. Strict Non-Fabrication Invariants Enforced

1. **Missing Data is Never Assumed Safe**:
   If Copernicus DEM GLO-30 fails or times out, the slope status is marked `UNKNOWN` with `unknown_percentage > 0.0`. Under no circumstances is missing elevation treated as flat or buildable land.

2. **Zero Rural Buildings is Never Assumed Clear**:
   In rural Indian terrain, OpenStreetMap crowdsourcing has known omissions. If an Overpass query returns 0 buildings in a rural boundary, the engine tags `OSM-RURAL-ZERO-DWELLINGS` as `CONDITIONAL` (`UNVERIFIED_RURAL_ZONE`), requiring satellite confirmation rather than blindly placing turbines over unmapped homes.

3. **Elimination of Fake Synthetics**:
   - Eliminated the Phase 0 hack in `overpass_client.py` which previously injected an artificial `osm_settlement_core` at $(0, 0)$.
   - Eliminated the coordinate bounding box heuristics (`is_arid_west`, `is_coastal_east`) in `worldcover_client.py`, returning authentic Sentinel-derived classification metadata and decoupling physical land cover from legal development zoning.

4. **Geometry Integrity**:
   - Buildable area calculations operate via local projected UTM Cartesian coordinates (metres).
   - Ray-casting containment respects outer polygon perimeters and interior holes (e.g. water bodies and enclaves).
   - The resulting buildable mask parcels strictly reside within the Phase 2 search envelope.

---

## 4. API Endpoints & Interfaces

### 1. `POST /api/geo/suitability/evaluate`
Accepts:
```json
{
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "hub_height_m": 120.0,
  "rotor_diameter_m": 120.0
}
```
Returns:
```json
{
  "overall_status": "PARTIAL",
  "search_envelope_area_km2": 12.5664,
  "buildable_area_km2": 8.4210,
  "buildable_area_m2": 8421000.0,
  "buildable_percentage": 67.0,
  "conditional_percentage": 18.0,
  "excluded_percentage": 15.0,
  "unknown_percentage": 0.0,
  "projected_crs": "EPSG:32644",
  "utm_zone": 44,
  "buildable_mask_geojson": { "type": "MultiPolygon", "coordinates": [...] },
  "terrain_assessment": { "elevation_m": 42.0, "slope_deg": 3.2, "is_complex_terrain": false },
  "wind_assessment": { "status": "READY", "annual_mean_wind_speed_mps": 7.42 },
  "landcover_assessment": { "dominant_class_name": "Cropland", "status": "PARTIAL" },
  "infrastructure_assessment": { "counts": { "dwellings": 2, "highways": 1 } },
  "conservation_assessment": { "is_inside_protected_area": false },
  "active_constraints": [...],
  "hard_exclusion_reasons": [...],
  "conditional_reasons": [...],
  "provenance_chain": [...]
}
```

### 2. `GET /api/geo/land-data?lat=...&lon=...&radius_km=...`
Refactored to evaluate through the `EnvironmentalSuitabilityEngine`, returning real slope, real Copernicus DEM elevations, real land cover, and honest buildable percentages to the existing frontend.

---

## 5. Verification & Test Suite Summary

The engine is protected by a dedicated 14-scenario test suite in `tests/test_suitability_buildable_engine.py`:
- `test_search_envelope_is_not_assumed_buildable` (PASS)
- `test_steep_slope_hard_exclusion` (PASS)
- `test_moderate_slope_conditional` (PASS)
- `test_protected_area_interior_prohibition` (PASS)
- `test_eco_sensitive_zone_buffer_exclusion` (PASS)
- `test_rural_zero_dwellings_uncertainty` (PASS)
- `test_missing_terrain_raster_triggers_unknown` (PASS)
- `test_habitation_cluster_500m_setback` (PASS)
- `test_statutory_infrastructure_formula_distance` (PASS)
- `test_buildable_mask_never_exceeds_search_envelope` (PASS)
- `test_polygon_with_interior_hole_preserved` (PASS)
- `test_deterministic_evaluation` (PASS)
- `test_api_suitability_evaluate_endpoint` (PASS)
- `test_api_land_data_endpoint_uses_suitability_engine` (PASS)

**Full regression status**: **106 passed** across all backend test modules. Frontend builds cleanly (`npm run build`).
