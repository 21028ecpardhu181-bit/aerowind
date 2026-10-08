# AeroQuantum-Wind — Engineering Data Gaps, Uncertainties & Blockers

**Date**: 2026-10-06  
**Auditor**: Senior Geospatial Data Engineer + Wind Resource Engineer  
**Scope**: Explicit Identification of Missing Data, Technical Blockers, and Mitigations  

---

## 1. Primary Data Gaps & Technical Blockers

### Gap 1: Automated Village Administrative Cadastre (Survey of India)
- **Current Problem**: The platform relies on OpenStreetMap Nominatim, which frequently returns point centroids rather than cadastral polygons in rural India.
- **Authoritative Source**: Survey of India Village Boundary Database.
- **The Blocker**: Survey of India provides no public programmatic REST API. Downloading requires Indian mobile OTP login and manual shapefile retrieval.
- **Phase 2 Mitigation**:
  - Establish an offline pre-loaded spatial database (`aeroquantum_cadastre.db`) pre-populated with SOI village boundaries for primary renewable energy districts (e.g. Anantapur, Kurnool, Jaisalmer, Kutch, Kanyakumari).
  - When a requested site falls outside the pre-loaded SOI database, the system must truthfully report `BOUNDARY_STATUS = MANUAL_REQUIRED (Official Cadastre Not Ingested)` rather than inventing a boundary.

---

### Gap 2: Automated Bankable Wind Atlas (NIWE 120m/150m)
- **Current Problem**: The codebase uses hardcoded `if/elif` regional approximations in `global_wind_atlas.py`.
- **Authoritative Source**: National Institute of Wind Energy (NIWE) 120m / 150m Wind Potential Atlas.
- **The Blocker**: NIWE does not expose a public real-time API for wind rasters. Data is distributed as technical reports and offline GIS layers.
- **Phase 2 Mitigation**:
  - Ingest the official 500m NIWE raster layers for target states into local GeoTIFF format.
  - Query local GeoTIFF grids via `rasterio` sampling.
  - Mark missing areas as `WIND_RESOURCE_STATUS = UNKNOWN`.

---

### Gap 3: High-Resolution Land Cover (ESA WorldCover 10m)
- **Current Problem**: `worldcover_client.py` uses latitude/longitude bounding-box heuristics.
- **Authoritative Source**: ESA WorldCover 10m Cloud-Optimized GeoTIFFs on AWS Open Data (`eu-central-1`).
- **The Blocker**: Real-time STAC / HTTP Range queries on 3x3 degree GeoTIFFs require GDAL / rasterio raster dependencies in the backend environment.
- **Phase 2 Mitigation**:
  - Integrate Cloud-Optimized GeoTIFF window reading using `rasterio` or a lightweight local tile cache.
  - Eliminate all coordinate-band heuristics.

---

### Gap 4: Protected Areas & Conservation Screening (WDPA / MoEFCC)
- **Current Problem**: `protected_planet_client.py` contains a static list of 10 Indian parks.
- **Authoritative Sources**: UNEP-WCMC Protected Planet WDPA v4 API / MoEFCC PARIVESH Eco-Sensitive Zones.
- **The Blocker**:
  - Protected Planet API v4 requires a personal token and strictly prohibits commercial use.
  - MoEFCC PARIVESH does not provide a public developer REST API.
- **Phase 2 Mitigation**:
  - Download and filter the monthly official Indian WDPA spatial shapefile.
  - Store protected area polygons in a local spatial SQLite table.
  - Screen candidate coordinates using spatial polygon distance (`ST_Distance`) with statutory 1km and 10km buffers.

---

### Gap 5: Rural Building Footprint Omissions (OpenStreetMap Overpass)
- **Current Problem**: Remote agricultural land in India often has zero building footprints mapped in OpenStreetMap, creating a false impression of unencumbered land.
- **The Blocker**: Overpass cannot return structures that volunteers have not mapped.
- **Phase 2 Mitigation**:
  - Enforce the new rule: When Overpass returns 0 buildings in a rural zone, status is `PARTIAL / UNVERIFIED_RURAL_ZONE`.
  - Alert the user that satellite optical verification and ground survey are mandatory.
  - Never convert missing buildings into "clear land".

---

### Gap 6: Geotechnical Soil Uncertainty (ISRIC SoilGrids 2.0)
- **Current Problem**: Code translates SoilGrids regional pixels into concrete foundation types.
- **The Blocker**: SoilGrids REST API v2.0 is in beta with intermittent downtime, and global 250m soil grids have high prediction uncertainty.
- **Phase 2 Mitigation**:
  - Formally classify all soil data as **PRELIMINARY DESKTOP SCREENING ONLY**.
  - Provide explicit statutory disclaimers that borehole Standard Penetration Tests (SPT) are required prior to foundation design.

---

## 2. Summary of Engineering Limitations & Siting Warnings

| Subsystem | Current State | Siting Limitation | User-Facing Warning |
|---|---|---|---|
| **Village Boundary** | Point centroids or synthetic envelopes | May not match legal revenue survey sheets | *"Preliminary boundary. Official Survey of India revenue cadastre verification required."* |
| **Wind Resource** | Live weather or mock GWA | Inadequate for bankable 20-year energy yields | *"Live atmospheric telemetry only. Does not replace NIWE certified mast measurement for financing."* |
| **Terrain Slope** | 90m Copernicus DEM | May smooth micro-ridges and narrow ravines | *"Macro-slope gradient (90m resolution). Topographic drone survey required for crane pad design."* |
| **Habitations** | OSM Overpass crowdsourcing | Rural farmsteads and huts may be omitted | *"Unmapped rural dwellings may exist. Satellite optical confirmation mandatory before final layout."* |
| **Protected Land** | Static list | Wildlife corridors and reserve forests missed | *"Statutory MoEFCC / State Forest Department clearance required for final concession boundary."* |
| **Soil Capacity** | 250m ML model | Does not capture subterranean rock strata | *"Desktop screening only. Physical borehole geotechnical testing mandatory prior to foundation pouring."* |
EOF
