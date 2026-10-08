# AeroQuantum-Wind — Data Access & Retrieval Specifications

**Date**: 2026-10-06  
**Auditor**: Senior Geospatial Data Engineer + Wind Resource Engineer  
**Scope**: Technical Access Protocols, Endpoints, Formats, and Failure Handlers  

---

## 1. Access Protocol Overview

AeroQuantum-Wind interfaces with external geospatial and physical systems across four distinct architectural patterns:

1. **Direct HTTP REST API (Automated & Operational)**: Open-Meteo Atmospheric Forecast, Open-Meteo Elevation, OSM Nominatim, OSM Overpass.
2. **Cloud-Optimized Object Storage (Direct S3 / COG)**: AWS Open Data (ESA WorldCover 10m).
3. **Authenticated Restricted API (Token / Credentials Required)**: UNEP-WCMC Protected Planet (WDPA v4), Copernicus Data Space (GLO-30).
4. **Manual Download & Spatial DB Ingestion (Portal Auth / Offline)**: Survey of India Village Boundary Database, NIWE India Wind Potential Atlas, MoEFCC PARIVESH, AAI NOCAS.

---

## 2. Technical Ingestion Specifications by Dataset

### A. Survey of India (SOI) Village Boundary Database
- **Portal URL**: `https://onlinemaps.surveyofindia.gov.in/`
- **Protocol**: Interactive HTTPS Web Portal.
- **Authentication**: Indian Mobile OTP and registered account credentials.
- **Automated Querying Possible?**: **NO**. Survey of India explicitly restricts automated programmatic scrapers/crawlers under its portal terms of service.
- **Data Delivery**: Downloadable ZIP archives partitioned by State and District containing `.shp`, `.shx`, `.dbf`, `.prj` (EPSG:4326), or `.gdb` (ESRI File Geodatabase).
- **Ingestion Workflow for Phase 2**:
  1. Manual download of target renewable energy States (Andhra Pradesh, Gujarat, Karnataka, Tamil Nadu, Rajasthan, Maharashtra, Odisha).
  2. Batch import into spatial database via `ogr2ogr`:
     ```bash
     ogr2ogr -f "SQLite" -dsco SPATIALITE=YES aeroquantum_spatial.db soi_villages_ap.shp -nln village_boundaries
     ```
  3. Spatial index creation on `ST_Intersects` and village name.
- **Runtime Failure Behavior**: If a user searches for a coordinate or village not yet ingested from the official SOI database, the system must return:
  `BOUNDARY_STATUS = MANUAL_REQUIRED (Official Survey of India Cadastre Not Ingested for District)`
  Under no circumstances may the application synthesize a circular or harmonic boundary.

---

### B. NIWE India Wind Potential Atlas (120m / 150m AGL)
- **Portal URL**: `https://niwe.res.in/Open_data_Set/technical_report/19/` and `https://maps.niwe.res.in/`
- **Protocol**: Static HTTP File Download & Map Viewer.
- **Authentication**: Public download for technical summary reports; formal data acquisition agreement for granular GIS layers.
- **Automated Querying Possible?**: **NO public REST API**.
- **Data Delivery**: Multi-band GeoTIFF rasters (500m resolution) and PDF technical tables.
- **Ingestion Workflow for Phase 2**:
  1. Download regional GeoTIFFs covering prime wind corridors.
  2. Clip raster grids to project concession bounding boxes.
  3. Sample wind speed ($120\,\text{m}$), Weibull scale parameter ($A$), shape parameter ($k$), and WPD ($\text{W/m}^2$) using GDAL/rasterio:
     ```python
     with rasterio.open("niwe_wind_120m_india.tif") as src:
         wind_speed_120m = list(src.sample([(lon, lat)]))[0][0]
     ```
- **Runtime Failure Behavior**: If the coordinate falls outside ingested NIWE coverage, report:
  `WIND_RESOURCE_STATUS = UNKNOWN (NIWE 120m Atlas coverage not loaded)`.
  Never invoke the legacy `if/elif` bounding-box heuristics in `global_wind_atlas.py`.

---

### C. Live Atmospheric Telemetry (Open-Meteo)
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Protocol**: HTTP GET JSON REST.
- **Authentication**: None required for standard non-commercial usage; commercial rate-limit subscription available.
- **Request Parameters**:
  ```
  latitude=16.9676&longitude=81.8138&hourly=wind_speed_100m,wind_direction_100m,surface_pressure,temperature_2m&forecast_days=1
  ```
- **Response Structure**:
  ```json
  {
    "latitude": 16.9676,
    "longitude": 81.8138,
    "hourly": {
      "time": ["2026-10-06T00:00", ...],
      "wind_speed_100m": [7.8, ...],
      "wind_direction_100m": [270, ...]
    }
  }
  ```
- **Engineering Isolation**: Value labeled strictly as `LIVE_ATMOSPHERIC_TELEMETRY`. Prevented by type validation from entering AEP annual energy calculation.

---

### D. Terrain & Surface Elevation (Copernicus DEM via Open-Meteo)
- **Endpoint**: `https://api.open-meteo.com/v1/elevation`
- **Protocol**: HTTP GET JSON REST.
- **Underlying Dataset**: Copernicus DEM GLO-90 / SRTM.
- **Request Parameters**:
  ```
  latitude=16.9676,16.9680,...&longitude=81.8138,81.8140,...
  ```
- **Batching & Rate Limits**: Maximum 100 points per batch. Rate limit 10,000 queries/day under open terms.
- **Local Disk Cache**: SQLite table `dem_cache` indexed on `(lat_round, lon_round)` to 4 decimal places ($~11\,\text{m}$ precision).
- **Runtime Failure Behavior**: If the API times out, return:
  `ELEVATION_STATUS = UNKNOWN`.
  Never substitute synthetic sinusoids like `45.0 + 35.0 * sin(...)`.

---

### E. ESA WorldCover 10m Land Classification
- **Data Host**: Registry of Open Data on AWS (`s3://esa-worldcover/` in region `eu-central-1`).
- **Protocol**: HTTP Range GET on Cloud-Optimized GeoTIFFs (COGs) or STAC API.
- **STAC Endpoint**: `https://services.terrascope.be/stac`
- **Authentication**: None required for open AWS bucket.
- **Tile Naming Convention**: Delivered as $3^\circ \times 3^\circ$ tiles named `ESA_WorldCover_10m_2021_v200_<TileID>_Map.tif`.
- **Query Mechanism**:
  ```python
  import rasterio
  from rasterio.windows import from_bounds

  cog_url = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N15E078_Map.tif"
  with rasterio.open(cog_url) as src:
      window = from_bounds(west, south, east, north, src.transform)
      landcover_array = src.read(1, window=window)
  ```
- **Runtime Failure Behavior**: If network access to AWS S3 fails, return:
  `LAND_COVER_STATUS = UNKNOWN`.
  Never classify land based on latitude coordinate ranges.

---

### F. Physical Exclusions & Infrastructure (OSM Overpass)
- **Endpoint**: `https://overpass-api.de/api/interpreter`
- **Protocol**: HTTP POST with Overpass QL query string.
- **Timeout**: 12.0 seconds server-side timeout.
- **Query Format**:
  ```
  [out:json][timeout:12];
  (
    node["place"~"city|town|village|hamlet"](around:3500, 16.9676, 81.8138);
    way["building"](around:3500, 16.9676, 81.8138);
    relation["building"](around:3500, 16.9676, 81.8138);
    way["highway"](around:3500, 16.9676, 81.8138);
    way["power"](around:3500, 16.9676, 81.8138);
    way["waterway"](around:3500, 16.9676, 81.8138);
  );
  out center;
  ```
- **Caching**: Full query response cached in SQLite table `osm_exclusion_cache` keyed by `(center_lat, center_lon, radius_km)`.
- **Runtime Failure Behavior**: If Overpass returns HTTP 429, 504, or network timeout:
  `BUILDING_DATA_STATUS = UNKNOWN`
  `INFRASTRUCTURE_DATA_STATUS = UNKNOWN`
  The system must state: "Physical exclusions cannot be verified due to external API timeout. Land feasibility cannot be established."

---

### G. Protected Areas & Conservation (Protected Planet / WDPA)
- **Endpoint**: `https://api.protectedplanet.net/v4/protected_areas`
- **Protocol**: HTTP GET JSON REST.
- **Authentication**: Query parameter token `?token=<YOUR_TOKEN>`.
- **Commercial Restrictions**: Commercial entities must use the Integrated Biodiversity Assessment Tool (IBAT).
- **Alternative Open Protocol**: Offline ingestion of the official monthly WDPA Indian polygon shapefile (`WDPA_IND_shapefile.zip`).
- **Runtime Failure Behavior**: If token is absent or API fails, and local spatial layer is not loaded:
  `CONSERVATION_STATUS = MANUAL_REQUIRED (Protected Area Clearance Unverified)`.
  Never rely on the deprecated 10-park static list.
EOF
