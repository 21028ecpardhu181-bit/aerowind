# AeroQuantum-Wind — Engineering Data Provenance Architecture

**Date**: 2026-10-06  
**Auditor**: Senior Geospatial Data Engineer + Wind Resource Engineer  
**Standard**: Universal Provenance Tracking & Non-Fabrication Architecture  

---

## 1. Core Engineering Principle

> **NO ENGINEERING NUMBER WITHOUT TRACEABLE PROVENANCE.**  
> **MISSING DATA MUST NEVER YIELD A POSITIVE ("SAFE" OR "CLEAR") ENGINEERING RESULT.**

Every environmental reading, coordinate exclusion, aerodynamic power calculation, and regulatory setback returned by AeroQuantum-Wind must carry a structured provenance envelope disclosing its authoritative origin, uncertainty, and legal applicability.

---

## 2. Universal Provenance Schema

Implemented in Python (`backend/app/provenance.py`):

```json
{
  "value": 7.82,
  "unit": "m/s",
  "source": "National Institute of Wind Energy (NIWE), MNRE",
  "source_url": "https://niwe.res.in/Open_data_Set/technical_report/19/",
  "dataset": "120m Wind Potential Atlas of India",
  "version": "Technical Report 19 / 2024 Revision",
  "resolution": "500m Meso-Micro Coupled WRF",
  "crs": "EPSG:4326 (WGS 84)",
  "retrieved_at": "2026-10-06T12:00:00Z",
  "license": "Government of India Open Data / NIWE Attribution",
  "status": "VERIFIED_REAL",
  "engineering_suitability": "ENGINEERING_GRADE",
  "is_authoritative": true,
  "limitations": "National mesoscale benchmark; microscale mast validation required for final bankable P90 yield."
}
```

---

## 3. Provenance Lifecycle Across the Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INGESTION & VALIDATION (backend/app/gis_validator.py)    │
│    - Checks source connectivity and payload integrity       │
│    - If API fails or data is missing:                       │
│      STATUS = UNKNOWN | Suitability = UNKNOWN               │
└──────────────────────────────┬──────────────────────────────┘
                               │ Structured ProvenanceMetadata
┌──────────────────────────────▼──────────────────────────────┐
│ 2. COMPUTATIONAL ENGINES (geo_engine.py / floris_engine.py) │
│    - Propagates provenance through spatial KD-Tree filters  │
│    - Attaches setback references (e.g. MNRE 2024 Clause)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Serialized Telemetry Envelope
┌──────────────────────────────▼──────────────────────────────┐
│ 3. API PRESENTATION & UI (FastAPI Schemas -> React/Cesium)  │
│    - Discloses data lineage in DataSourcesModal.tsx         │
│    - Alerts user to preliminary screening vs certified data │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Source Status Classification Taxonomy

AeroQuantum-Wind strictly enforces the following 8 status states across all subsystems:

1. **`VERIFIED_REAL`**: Authoritative, externally validated dataset currently operating with active live data.
   *Example: Open-Meteo live weather telemetry, tabulated NREL FLORIS reference power curves.*
2. **`PARTIAL`**: Real external source is connected, but spatial completeness, sampling frequency, or resolution is limited.
   *Example: Open-Meteo Copernicus GLO-90 elevation (smooths 30m features), OpenStreetMap Overpass (rural building omissions).*
3. **`MANUAL_REQUIRED`**: Authoritative official dataset exists, but requires registered portal download, offline ingestion, or API credentials.
   *Example: Survey of India Village Boundary Database, NIWE 120m Wind Potential Atlas, ESA WorldCover 10m AWS COG.*
4. **`UNAVAILABLE`**: Dataset does not exist for the queried coordinates, or external provider has permanently decommissioned the endpoint.
5. **`HARDCODED`**: Values originate from static internal Python code, mock dictionaries, or arbitrary heuristics.
   *Example: Deprecated Global Wind Atlas client in `global_wind_atlas.py`, static 10-park list in `protected_planet_client.py`.*
6. **`MOCK`**: Synthetically generated test numbers designed strictly for unit test execution. Must be labeled `is_synthetic: true`.
7. **`UNKNOWN`**: External query failed, timed out, or returned nodata. **Must be treated as an unverified hazard.**
8. **`NOT_ENGINEERING_GRADE`**: Dataset or heuristic lacks scientific fidelity and is legally or technically unfit for micro-siting decisions.

---

## 5. Non-Fabrication Invariants

1. **The Silence Rule**: If a GIS service (Overpass, SoilGrids, Nominatim) fails to respond, the system must **never** synthesize replacement data or assume zero hazards.
2. **The Clearance Invariant**:
   $$\text{Clearance Granted} \iff \text{Status} == \text{VERIFIED\_REAL} \land \text{Distance} \ge \text{Statutory Setback}$$
   If $\text{Status} \in \{\text{UNKNOWN}, \text{HARDCODED}, \text{MOCK}, \text{PARTIAL}\}$, the land must be marked as **CONDITIONAL** or **UNKNOWN**, requiring manual surveyor sign-off.
3. **The Climatology Boundary**: Real-time atmospheric forecasts ($100\,\text{m}$ weather) must carry `EngineeringSuitability.REAL_WEATHER_NOT_LONG_TERM_RESOURCE` to prevent accidental consumption by the 20-year AEP model.
EOF
