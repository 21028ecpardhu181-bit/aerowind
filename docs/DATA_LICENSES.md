# AeroQuantum-Wind — Data Licensing, Commercial Restrictions & Legal Status

**Date**: 2026-10-06  
**Auditor**: Senior Geospatial Data Engineer + Wind Resource Engineer  
**Scope**: Legal Licensing, Intellectual Property, and Commercial Feasibility Audit  

---

## 1. Master Licensing Matrix

| Dataset | Provider | License Type | Commercial Use Permitted? | Attribution / Notice Requirements | Redistribution Permitted? | Legal Siting Risk |
|---|---|---|---|---|---|---|
| **Survey of India Village Cadastre** | Survey of India, DST | National Geospatial Policy (2022) | **YES** | Mandatory credit: "Administrative boundaries sourced from Survey of India" | Yes, with registration terms | Low (Official Government of India source) |
| **NIWE India Wind Potential Atlas** | National Institute of Wind Energy, MNRE | Government Open Data / NIWE Proprietary | **YES** | Mandatory citation of NIWE Technical Report & MNRE | Yes, for processed screening outputs | Low (Official national authority) |
| **Open-Meteo Weather & Elevation** | Open-Meteo GmbH | CC-BY 4.0 / Copernicus / ECMWF Terms | **YES** | Mandatory credit: "Weather & elevation data by Open-Meteo under CC-BY 4.0" | Yes, under CC-BY 4.0 terms | Low (For preliminary screening; not commercial warranty) |
| **Copernicus DEM GLO-30 Public** | European Space Agency (ESA) | Free and Open Public License | **YES** | Mandatory notice: "Produced using Copernicus WorldDEM data © DLR e.V. / Airbus / ESA" | Yes | Low |
| **ESA WorldCover 10m** | European Space Agency / VITO | Creative Commons Attribution 4.0 (CC-BY 4.0) | **YES** | Mandatory notice: "© ESA WorldCover project 2020/2021 / Contains modified Copernicus Sentinel data" | Yes | Low |
| **OpenStreetMap Infrastructure** | OpenStreetMap Contributors | Open Data Commons Open Database License (ODbL 1.0) | **YES** | Mandatory credit: "© OpenStreetMap contributors" | Yes, under ODbL share-alike for database modifications | Medium (Share-Alike clause on modified vector databases) |
| **Protected Planet (WDPA v4 API)** | UNEP-WCMC & IUCN | UNEP-WCMC Terms of Use (Non-Commercial) | **NO (Free API)** | Free API strictly prohibited for commercial entities or revenue generation | No | **HIGH (License breach if commercialized without IBAT)** |
| **ISRIC SoilGrids 2.0** | ISRIC — World Soil Information | Creative Commons Attribution 4.0 (CC-BY 4.0) | **YES** | Mandatory citation: "SoilGrids 2.0: ISRIC — World Soil Information" | Yes | Low (Scientific data disclaimer applies) |
| **MNRE ALMM-Wind Schedule** | Ministry of New and Renewable Energy | Public Regulatory Gazette | **YES** | Public regulatory document of Government of India | Yes | None (Statutory law) |
| **NREL FLORIS & Turbine Curves** | NREL & OEM Technical Sheets | BSD 3-Clause License / OEM Technical Specs | **YES** | Standard BSD 3-Clause copyright notice | Yes | Low |

---

## 2. In-Depth Legal & Commercial Analysis

### A. Protected Planet (UNEP-WCMC) Commercial Restriction
- **Legal Constraint**: The Protected Planet API v4 terms of use state explicitly:
  > *"The Protected Planet API is not available for commercial use. Commercial use is defined as any use by or for a commercial entity, whether revenue-generating or not, or any use that generates revenue for any type of entity."*
- **Commercial Remedy**: Commercial renewable developers, EPCs, and IPPs must subscribe to the **Integrated Biodiversity Assessment Tool (IBAT)** (`https://www.ibat-alliance.org/`).
- **Phase 1 Architectural Action**: The platform must not claim automated live Protected Planet commercial compliance without an IBAT commercial license key. For non-commercial development/academic research, the monthly free snapshot can be used with attribution.

### B. OpenStreetMap Share-Alike (ODbL 1.0)
- **Legal Constraint**: OpenStreetMap data is licensed under ODbL 1.0. 
- **Application Boundary**: If the application simply queries and displays OSM data alongside other layers (Collective Database), the surrounding proprietary code does not need to be open-sourced. However, if OSM data is substantively merged into a derivative database (e.g., combining OSM roads with proprietary cadastres into a single geodatabase), that derivative database must be released under ODbL upon distribution.
- **Phase 1 Architectural Action**: Keep the OSM exclusion cache (`osm_exclusion_cache`) logically isolated as an independent cache layer with standard ODbL attribution.

### C. Survey of India (National Geospatial Policy 2022)
- **Legal Framework**: Under the landmark National Geospatial Policy (2022), spatial data generated using public funds (including administrative boundary datasets) is democratized and made freely available to all Indian entities without requiring prior security vetting, provided accuracy limits are respected (thresholds for terrestrial lidar/sub-meter positioning near sensitive defence installations).
- **Compliance**: Siting turbines within general rural areas using the SOI Village Boundary Database is fully compliant.

### D. SoilGrids Disclaimer & Geotechnical Liability
- **Engineering Liability**: Using regional satellite/model soil data to certify structural wind turbine foundations carries catastrophic civil liability (foundation overturning under cyclic dynamic rotor thrust).
- **Mandatory Siting Disclaimer**: All geotechnical telemetry returned by AeroQuantum-Wind must carry the statutory engineering notice:
  > *"Preliminary desktop screening only. Derived from ISRIC SoilGrids 250m machine-learning models. Does not constitute geotechnical certification. Confirmatory geotechnical borehole investigation (SPT, CPT, and triaxial shear testing) is legally required prior to foundation design."*
EOF
