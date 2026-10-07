# AeroQuantum-Wind — Authoritative Data Sources Inventory (Phase 1)

**Date**: 2026-10-06  
**Auditor**: Senior Geospatial Data Engineer + Wind Resource Engineer (10+ Years Experience)  
**Standard**: Strict Data Provenance, Regulatory Traceability, and Source Verification  

---

## 1. Master Data Sources Registry

| # | Dataset / Category | Authoritative Provider | Purpose in Engineering Pipeline | Resolution | Geographic Coverage | Version / Update | Access Mechanism | Status | Engineering Suitability |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **Village Boundary Database** | Survey of India (SOI), DST | Official cadastral boundary & administrative envelope | Village Cadastre (1:50,000 scale) | Pan-India (All States & UTs) | 2024 National Geoportal Release | Web portal download (Registration required) | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Gold Standard for Land Siting) |
| **2** | **OSM Nominatim Administrative Boundaries** | OpenStreetMap Contributors | Secondary fallback boundary & gazetteer geocoding | Vector polygon | Global (Sparse rural village polygons) | Real-time ODbL | REST API (`polygon_geojson=1`) | **PARTIAL** | **PRELIMINARY_SCREENING_ONLY** (Missing polygons = UNKNOWN) |
| **3** | **India Wind Potential Atlas (120m / 150m AGL)** | National Institute of Wind Energy (NIWE), MNRE | Multi-year bankable wind resource & CUF baselines | 500m meso-micro WRF (validated 406 masts) | Pan-India onshore & coastal | Tech Report 19 / 2024 Revision | Web portal download (maps.niwe.res.in) | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Statutory Benchmark for AEP/Bankability) |
| **4** | **Legacy Regional Wind Heuristic** | Deprecated Repo Code (`global_wind_atlas.py`) | *Legacy placeholder (unsubstantiated)* | N/A | Hardcoded Indian regions | Prototype v1 | In-memory Python logic | **HARDCODED** | **NOT_ENGINEERING_GRADE** (Must not be used in pipeline) |
| **5** | **Live Atmospheric Telemetry (100m AGL)** | Open-Meteo GmbH (ECMWF & DWD ICON) | Current atmospheric condition & UI visualization | 0.1° (~11km) grid / Hourly | Global terrestrial | Operational Real-Time Run | Direct HTTP JSON REST | **VERIFIED_REAL** | **REAL_WEATHER_NOT_LONG_TERM_RESOURCE** (Cannot replace 20-yr AEP) |
| **6** | **Copernicus DEM Global 90m (GLO-90)** | Open-Meteo Elevation API (Copernicus / SRTM) | Preliminary terrain elevation & macro-slope screening | 90m horizontal grid | Global (84°N to 56°S) | GLO-90 2020 Release | Direct HTTP JSON REST | **VERIFIED_REAL** | **PARTIAL** (Suitable for preliminary screening; smooths steep gullies) |
| **7** | **Copernicus DEM Global 30m (GLO-30)** | European Space Agency (ESA) Copernicus Data Space | Microscale terrain gradient, aspect, and wake deflection | 30m horizontal grid | Global terrestrial | GLO-30 Public Release | S3 / OData API (OAuth2 credentials required) | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Full civil & aerodynamic terrain screening) |
| **8** | **ESA WorldCover 10m Land Classification** | European Space Agency (ESA) / VITO Remote Sensing | Physical land cover & aerodynamic roughness ($z_0$) | 10m grid (Sentinel-1 & Sentinel-2) | Global terrestrial | v200 (2021) / v100 (2020) | AWS Open Data (`eu-central-1`) / STAC COG | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Surface cover only; does not grant legal land title) |
| **9** | **Physical Infrastructure (Roads, Power, Water)** | OpenStreetMap Contributors (Overpass API) | Setback buffers for roads, railways, power lines | Vector points, ways, relations | Global (High urban, sparse rural) | Real-time OSM database | Direct Overpass QL HTTP POST/GET | **VERIFIED_REAL** | **PARTIAL** (Incomplete in remote rural zones; failure = UNKNOWN) |
| **10**| **World Database on Protected Areas (WDPA)** | UNEP-WCMC & IUCN Protected Planet | Statutory national parks, sanctuaries, and Ramsar sites | Vector boundary polygons & points | Global terrestrial & marine | Monthly Release (v4 API) | REST API v4 (`?token=...` required) | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Strictly Non-Commercial / Research Use Only) |
| **11**| **Notified Eco-Sensitive Zones (ESZ) & Forests** | MoEFCC, Government of India (PARIVESH) | Statutory wildlife eco-sensitive buffers & forest land | Official Survey Gazette / Shapefile | Pan-India | Statutory Gazette Notifications | Portal download (parivesh.nic.in) | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Legally binding under Indian Forest Act & NGT) |
| **12**| **SoilGrids 2.0 Global Gridded Soil Information** | ISRIC — World Soil Information | Soil texture (clay/sand/silt) and bulk density | 250m grid at 0–5cm, 5–15cm depths | Global terrestrial | SoilGrids 2.0 (2020/2021) | REST API (Beta/Unstable) / WCS / Direct TIF | **PARTIAL** | **PRELIMINARY_SCREENING_ONLY** (Never replaces borehole SPT/geotechnical tests) |
| **13**| **Approved List of Models & Manufacturers (ALMM-Wind)** | Ministry of New and Renewable Energy (MNRE) / NIWE | Certified commercial wind turbines eligible in India | Model-specific certified schedules | Commercial market in India | Official MNRE Gazette Orders | Official Government Circular / PDF | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Mandatory Statutory Compliance for Indian Grids) |
| **14**| **Reference Power & Thrust Curves ($C_T$)** | NREL / Manufacturer Technical Product Data | Aerodynamic wake deficit and electrical energy output | 1 m/s wind speed bins | Tabulated reference models | FLORIS v4.2 / OEM Datasheets | Verified Python dictionary | **VERIFIED_REAL** | **ENGINEERING_GRADE** (Industry Standard Reference) |
| **15**| **National Power Transmission Grid & Substations** | Central Electricity Authority (CEA) / NPP | Grid interconnection & transmission corridor planning | 220kV, 400kV, 765kV network | Pan-India | Perspective Transmission Plan | CEA Portal / NPP GIS Dashboard | **MANUAL_REQUIRED** | **PRELIMINARY_SCREENING_ONLY** (Requires State Transco load-flow study) |
| **16**| **Aviation & Defence Obstacle Limitation (OLS/CCZM)** | Airports Authority of India (AAI) / MoD | Total tip height clearance and radar safety zones | Grid-based Permissible Top Elevation | 20km–56km aerodrome radii | MCA Rules 2015 (Amended 2020) | NOCAS GIS Portal (nocas2.aai.aero) | **MANUAL_REQUIRED** | **ENGINEERING_GRADE** (Mandatory Statutory AAI/MoD Clearance) |

---

## 2. In-Depth Analysis of Critical Candidate Datasets

### A. Administrative / Village Boundaries
- **Candidate 1: Survey of India (SOI) Village Boundary Database**
  - **Status**: `MANUAL_REQUIRED`
  - **Real Source Verified**: Yes. Survey of India formally provides the Village Boundary Database through its Online Maps Portal (`https://onlinemaps.surveyofindia.gov.in/`).
  - **Structure**: Covers State, District, Sub-district (Taluk/Tehsil), and Village administrative polygons.
  - **Format**: ESRI Shapefile and Geodatabase. Delivered in geographic WGS 84 (EPSG:4326).
  - **Licensing**: Available free of cost to Indian citizens, academic institutions, and commercial organizations pursuant to the National Geospatial Policy (2022).
  - **API Feasibility**: **No automated public REST API**. Downloading requires interactive portal authentication and mobile OTP verification. Datasets must be downloaded as State/District packages and ingested into a local PostGIS or SQLite spatial database.
  - **Engineering Directive**: Village boundaries cannot be queried on-the-fly via public URL. When an un-ingested village is requested, the system must return `BOUNDARY_STATUS = MANUAL_REQUIRED (Official SOI Cadastre Not Loaded)`. Generating circular or synthetic multi-harmonic polygons is strictly prohibited.

- **Candidate 2: OpenStreetMap Nominatim Administrative Cadastre**
  - **Status**: `PARTIAL`
  - **Evaluation**: While Nominatim supports `polygon_geojson=1`, rural Indian villages frequently exist only as single point nodes (`place=village`).
  - **Engineering Directive**: If a query returns a point node rather than a polygon, the system must report `BOUNDARY_GEOMETRY = UNAVAILABLE`. Never derive a polygon from satellite imagery or bounding-box coordinates.

---

### B. Wind Resource & Climatology
- **Candidate 1: NIWE Wind Potential Atlas (120m / 150m AGL)**
  - **Status**: `MANUAL_REQUIRED`
  - **Real Source Verified**: Yes. National Institute of Wind Energy (NIWE), Chennai (autonomous body under MNRE) publishes the national wind atlas developed via mesoscale WRF and microscale WAsP modelling at 500m spatial resolution. Validated across 406 dedicated meteorological masts.
  - **Data Contents**: Mean wind speed ($120\,\text{m}$ and $150\,\text{m}$), Wind Power Density (WPD, $\text{W/m}^2$), estimated Capacity Utilization Factor (CUF %), and statutory land exclusions (forests, water bodies, urban zones, elevation $>1500\,\text{m}$, slope $>16^\circ$).
  - **Access**: Downloadable as technical reports, state-wise potential tables, and GIS layers from `https://niwe.res.in/` and `https://maps.niwe.res.in/`.
  - **API Feasibility**: **No public REST API**. NIWE sells granular 10-minute mast time series through its commercial wing, while raster atlas layers require static GIS ingestion.
  - **Clean Replacement Architecture**: Replace the legacy `if/elif` code in `global_wind_atlas.py` with an offline pre-processed spatial index or local GeoTIFF raster covering major Indian renewable hubs.

- **Candidate 2: Live Weather (Open-Meteo European Centre ECMWF / ICON)**
  - **Status**: `VERIFIED_REAL` (Weather Only)
  - **Runtime Role**: Provides live hourly wind speed at $100\,\text{m}$ hub height ($v_{100}$), wind direction ($\theta_{100}$), atmospheric pressure, and air density.
  - **Engineering Rule**: Must be isolated to the UI weather widget and instantaneous dynamic test cases. **Strictly prohibited** from being fed into the 20-year Annual Energy Production (AEP) calculation engine.

---

### C. Terrain & Surface Elevation
- **Candidate 1: Open-Meteo Elevation API (Copernicus DEM GLO-90)**
  - **Status**: `VERIFIED_REAL` (GLO-90, not GLO-30)
  - **Audit Finding**: The repository documentation claimed "Copernicus DEM 30m (GLO-30)". Public Open-Meteo Elevation endpoints actually query the Copernicus Global 90m (GLO-90) and SRTM datasets.
  - **Engineering Implication**: 90m horizontal sampling is sufficient for regional macro-slope screening ($<16^\circ$), but averages out sharp gully features and micro-ridges smaller than 90m.
  - **Classification**: Valid for Phase 1 screening, but must be truthfully labeled as **Copernicus DEM GLO-90**.

- **Candidate 2: Copernicus Data Space Ecosystem (GLO-30 Public)**
  - **Status**: `MANUAL_REQUIRED`
  - **Real Source Verified**: GLO-30 public tiles provide true 30m horizontal resolution under European Space Agency open data terms, but programmatic access through the Copernicus Data Space Ecosystem requires OAuth2 registration and S3/OData credential configuration.

---

### D. Land Cover Classification
- **Candidate: ESA WorldCover 10m (v100 2020 / v200 2021)**
  - **Status**: `MANUAL_REQUIRED`
  - **Real Source Verified**: Yes. Published by European Space Agency and VITO Remote Sensing at 10m spatial resolution derived from Sentinel-1 radar and Sentinel-2 optical imagery.
  - **Classification Scheme**: 11 global classes:
    - 10: Tree cover (Roughness $z_0 = 0.75\,\text{m}$)
    - 20: Shrubland ($z_0 = 0.08\,\text{m}$)
    - 30: Grassland ($z_0 = 0.03\,\text{m}$)
    - 40: Cropland ($z_0 = 0.05\,\text{m}$)
    - 50: Built-up / Urban settlements ($z_0 = 1.0\,\text{m}$; Exclusion candidate)
    - 60: Bare / sparse vegetation ($z_0 = 0.01\,\text{m}$)
    - 70: Snow and ice
    - 80: Permanent water bodies (Exclusion)
    - 90: Herbaceous wetland (Exclusion)
    - 95: Mangroves (Exclusion)
    - 100: Moss and lichen
  - **Storage & Access**: Hosted on AWS Open Data (`s3://esa-worldcover/` in `eu-central-1`) as Cloud-Optimized GeoTIFFs (COGs) divided into $3^\circ \times 3^\circ$ tiles.
  - **Licensing**: Creative Commons Attribution 4.0 International (CC-BY 4.0). Fully approved for commercial use.
  - **Clean Architecture**: Eliminate all latitude/longitude bounding-box code. Access tiles via HTTP range requests on AWS COGs or local clipped rasters.
  - **Critical Principle**: Ground cover classification (e.g. "cropland" or "grassland") is **NOT** legal title or development permission. Revenue land conversion requires State revenue department approval.

---

### E. Physical Infrastructure Exclusions (OSM Overpass)
- **Status**: `VERIFIED_REAL` (with critical rural caveats)
- **Query Mechanism**: Live HTTP queries to `https://overpass-api.de/api/interpreter`.
- **Queried Infrastructure**:
  - Settlements / Dwellings: `place in (city, town, village, hamlet)` and `building=*`
  - High-Voltage Grid: `power in (line, cable, tower, minor_line, substation)`
  - Roads: `highway in (motorway, trunk, primary, secondary, tertiary, residential)`
  - Railways: `railway in (rail, narrow_gauge)`
  - Waterways: `waterway in (river, stream, canal)` and `natural=water`
- **Rural Blindspot & Failure Rule**: In rural India, building footprints are often unmapped in OpenStreetMap. If an Overpass query returns 0 buildings, the system **must not** declare the land free of habitations. The status must be recorded as:
  `BUILDING_DATA_STATUS = UNVERIFIED_RURAL_ZONE (Zero OSM structures detected; satellite/drone verification mandatory)`.
  If the API call fails or times out, the status must be recorded as:
  `BUILDING_DATA_STATUS = UNKNOWN (Query failure; no clearance granted)`.

---

### F. Protected Areas & Conservation
- **Candidate 1: UNEP-WCMC / IUCN Protected Planet (WDPA v4)**
  - **Status**: `MANUAL_REQUIRED`
  - **Real Source Verified**: Yes. Official World Database on Protected Areas (WDPA) provides global spatial polygons of national parks, wildlife sanctuaries, and biosphere reserves.
  - **API Restrictions**: Version 4 REST API (`https://api.protectedplanet.net/`) requires a registered personal token (`?token=...`). **Crucially, the free API terms strictly prohibit commercial use.** Commercial developers must subscribe through the Integrated Biodiversity Assessment Tool (IBAT, `https://www.ibat-alliance.org/`).
  - **Clean Architecture**: For open engineering evaluation, monthly global shapefile/GeoPackage packages can be downloaded and filtered for India. Static hardcoding of 10 parks is completely deprecated.

- **Candidate 2: Ministry of Environment, Forest & Climate Change (MoEFCC) PARIVESH**
  - **Status**: `MANUAL_REQUIRED`
  - **Real Source Verified**: Official Indian statutory notifications and spatial maps for Eco-Sensitive Zones (ESZ) around protected areas.
  - **Regulatory Enforcement**: Enforces a default 10km buffer zone around protected areas where Eco-Sensitive Zone clearance from the National Board for Wildlife (NBWL) is legally mandatory.

---

### G. Soil / Geotechnical Investigation
- **Candidate: ISRIC SoilGrids 2.0 (250m Global Grids)**
  - **Status**: `PARTIAL`
  - **Real Source Verified**: Yes. Produced by International Soil Reference and Information Centre (Wageningen, Netherlands).
  - **Variables**: Clay %, Silt %, Sand %, Bulk density ($0\text{--}5\,\text{cm}$ and $5\text{--}15\,\text{cm}$).
  - **Current Access Constraint**: The public REST API v2.0 is currently in beta with frequent downtime and rate limits.
  - **Engineering Classification**: Strictly **PRELIMINARY DESKTOP SCREENING**. SoilGrids pixels represent machine-learning spatial extrapolations with substantial local variance. Regional soil maps **can never** be used to certify foundation safety, bearing capacity, or pile depth. Formal civil design requires physical borehole Standard Penetration Tests (SPT) and laboratory triaxial shear testing.

---

### H. Indian Regulatory Setbacks (MNRE 2024 Guidelines)
- **Governing Authority**: Ministry of New and Renewable Energy (MNRE), New Delhi.
- **Statutory Document**: *Guidelines for Development of Onshore Wind Power Projects* (Originally issued October 22, 2016; **Major Amendment Issued July 4, 2024**).
- **Legally Binding Safety Setback Formula**:
  $$\text{Safety Distance} = H_{\text{hub}} + 0.5 \cdot D_{\text{rotor}} + 5\,\text{m}$$
  *(Hub Height + Half Rotor Diameter + 5 meters)*.
  Applies to:
  1. Notified Public Roads (National Highways, State Highways, Major District Roads)
  2. Railway tracks
  3. Buildings and Public Institutions (schools, hospitals, offices)
  4. Extra High Voltage (EHV) transmission lines ($>66\,\text{kV}$)
- **Habitation & Noise Buffer**: Minimum **500 meters** from any cluster of dwellings ($\ge 15$ inhabited dwellings).
- **Inter-Developer Micrositing Distance**:
  - Perpendicular to predominant wind direction: $5.0 \cdot D_{\text{max}}$
  - Parallel / In-line with predominant wind direction: $7.0 \cdot D_{\text{max}}$
- **Internal Optimization**: Internal inter-turbine spacing within a single developer's parcel is determined by IEC 61400-1 flow modeling and wake optimization rather than a rigid fixed number.
- **Engineering Directive**: Arbitrary rules (such as 1.5D or unreferenced 500m guesses) are replaced by the verified MNRE 2024 formula.

---

### I. Turbine Certification (MNRE ALMM-Wind / RLMM)
- **Governing Mechanism**: Approved List of Models and Manufacturers – Wind (ALMM-Wind; formerly Revised List of Models and Manufacturers, RLMM).
- **Managing Agency**: National Institute of Wind Energy (NIWE) on behalf of MNRE.
- **Requirement**: Only wind turbine models holding valid Type Certificates (TÜV NORD, DNV, UL) and listed in the active ALMM-Wind circular are legally permitted to connect to the Indian Central Transmission Utility (CTU) or State Transmission Utility (STU) grids.
- **Catalogue Verification**: All models in `backend/data/mnre_almm_wind_catalogue.json` are verified against active ALMM-Wind listings or flagged as academic reference baselines (NREL 5-MW, IEA 15-MW).
