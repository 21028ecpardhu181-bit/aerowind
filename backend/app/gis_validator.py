"""
backend/app/gis_validator.py — Environmental Source Validation & Strict Fallback Safeguards.

CRITICAL FAILURE RULE:
No API error, missing raster, failed polygon query, or sparse building set may EVER
be converted into "safe", "clear", "feasible", or "available".

If a source query fails:
    STATUS = UNKNOWN
    FEASIBILITY = UNKNOWN (Must require engineering confirmation)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from backend.app.provenance import (
    EngineeringSuitability,
    ProvenanceMetadata,
    SourceStatus,
    provider_registry,
)


class EnvironmentalDatasetValidator:
    """Validates external datasets and ensures strict handling of missing data."""

    @staticmethod
    def validate_elevation_response(
        coords: List[Tuple[float, float]],
        elevations: List[Optional[float]],
        raw_source: str = "Open-Meteo Elevation API",
    ) -> List[ProvenanceMetadata]:
        """
        Validates elevation values. If elevation is None or query failed,
        marks status as UNKNOWN with NOT_ENGINEERING_GRADE suitability.
        """
        results: List[ProvenanceMetadata] = []
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for (lat, lon), el in zip(coords, elevations):
            if el is None:
                meta = ProvenanceMetadata(
                    value=None,
                    unit="m",
                    source=raw_source,
                    source_url="https://api.open-meteo.com/v1/elevation",
                    dataset="Copernicus DEM Global (GLO-90)",
                    version="2020",
                    resolution="90m",
                    crs="EPSG:4326 / EGM2008",
                    retrieved_at=now_ts,
                    license="CC-BY 4.0 / Copernicus WorldDEM",
                    status=SourceStatus.UNKNOWN,
                    engineering_suitability=EngineeringSuitability.UNKNOWN,
                    limitations="Elevation query failed or returned nodata. Terrain clearance UNKNOWN.",
                )
            else:
                meta = ProvenanceMetadata(
                    value=float(el),
                    unit="m",
                    source=raw_source,
                    source_url="https://api.open-meteo.com/v1/elevation",
                    dataset="Copernicus DEM Global (GLO-90)",
                    version="2020",
                    resolution="90m",
                    crs="EPSG:4326 / EGM2008",
                    retrieved_at=now_ts,
                    license="CC-BY 4.0 / Copernicus WorldDEM",
                    status=SourceStatus.VERIFIED_REAL,
                    engineering_suitability=EngineeringSuitability.PRELIMINARY_SCREENING_ONLY,
                    limitations="90m public grid resolution; does not capture micro-gullies < 90m.",
                )
            results.append(meta)
        return results

    @staticmethod
    def validate_building_exclusion(
        overpass_success: bool,
        buildings_found: List[Dict[str, Any]],
        center_lat: float,
        center_lon: float,
        radius_km: float,
    ) -> Dict[str, Any]:
        """
        Validates Overpass building query.
        RULE: If Overpass failed or timed out, BUILDING_DATA_STATUS must be UNKNOWN.
        NEVER assume missing buildings means land is clear.
        """
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if not overpass_success:
            return {
                "building_data_status": SourceStatus.UNKNOWN.value,
                "buildings_count": 0,
                "buildings": [],
                "clearance_status": "UNKNOWN (Building footprint data could not be verified)",
                "feasibility": "UNKNOWN",
                "warning": "OSM Overpass query failed. Ground truth dwellings cannot be confirmed. Manual cadastral survey required.",
                "provenance": ProvenanceMetadata(
                    value=0,
                    unit="count",
                    source="OpenStreetMap Overpass API",
                    source_url="https://overpass-api.de/api/interpreter",
                    dataset="OSM Buildings & Places",
                    retrieved_at=now_ts,
                    status=SourceStatus.UNKNOWN,
                    engineering_suitability=EngineeringSuitability.UNKNOWN,
                    limitations="API failure. No engineering clearance may be granted.",
                ).model_dump(),
            }

        if len(buildings_found) == 0:
            # Query succeeded, but zero buildings returned in rural area
            return {
                "building_data_status": SourceStatus.PARTIAL.value,
                "buildings_count": 0,
                "buildings": [],
                "clearance_status": "UNVERIFIED_RURAL_ZONE (Zero OSM structures detected; satellite inspection required)",
                "feasibility": "CONDITIONAL",
                "warning": "Zero buildings in OSM. High probability of unmapped rural dwellings. Satellite inspection mandatory.",
                "provenance": ProvenanceMetadata(
                    value=0,
                    unit="count",
                    source="OpenStreetMap Overpass API",
                    source_url="https://overpass-api.de/api/interpreter",
                    dataset="OSM Buildings & Places",
                    retrieved_at=now_ts,
                    status=SourceStatus.PARTIAL,
                    engineering_suitability=EngineeringSuitability.PRELIMINARY_SCREENING_ONLY,
                    limitations="OSM crowdsourced coverage in rural India has significant omissions.",
                ).model_dump(),
            }

        return {
            "building_data_status": SourceStatus.VERIFIED_REAL.value,
            "buildings_count": len(buildings_found),
            "buildings": buildings_found,
            "clearance_status": "VERIFIED_OSM_FEATURES",
            "feasibility": "FEASIBLE",
            "warning": None,
            "provenance": ProvenanceMetadata(
                value=len(buildings_found),
                unit="count",
                source="OpenStreetMap Overpass API",
                source_url="https://overpass-api.de/api/interpreter",
                dataset="OSM Buildings & Places",
                retrieved_at=now_ts,
                status=SourceStatus.VERIFIED_REAL,
                engineering_suitability=EngineeringSuitability.PRELIMINARY_SCREENING_ONLY,
                limitations="Covers mapped OSM features within query radius.",
            ).model_dump(),
        }

    @staticmethod
    def validate_wind_resource_source(
        is_live_weather: bool,
        mean_speed_mps: float,
        lat: float,
        lon: float,
    ) -> ProvenanceMetadata:
        """
        Enforces clean separation between Live Weather and Long-Term Climatology.
        Live weather MUST NEVER be labeled as long-term resource.
        """
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if is_live_weather:
            return ProvenanceMetadata(
                value=mean_speed_mps,
                unit="m/s",
                source="Open-Meteo European Centre (ECMWF) Numerical Weather Prediction",
                source_url="https://api.open-meteo.com/v1/forecast",
                dataset="ECMWF Operational 100m Atmospheric Forecast",
                version="Live Run",
                resolution="0.1° (~11km) / Hourly",
                crs="EPSG:4326",
                retrieved_at=now_ts,
                license="CC-BY 4.0",
                status=SourceStatus.VERIFIED_REAL,
                engineering_suitability=EngineeringSuitability.REAL_WEATHER_NOT_LONG_TERM_RESOURCE,
                is_authoritative=False,
                limitations="Current instantaneous weather. CANNOT be used for 20-year project AEP financing.",
            )
        else:
            return ProvenanceMetadata(
                value=mean_speed_mps,
                unit="m/s",
                source="National Institute of Wind Energy (NIWE) / MNRE",
                source_url="https://niwe.res.in/Open_data_Set/technical_report/19/",
                dataset="120m Wind Potential Atlas of India",
                version="Technical Report 19",
                resolution="500m Meso-Micro Coupled WRF",
                crs="WGS 84",
                retrieved_at=now_ts,
                license="Government of India Open Data / NIWE Attribution",
                status=SourceStatus.MANUAL_REQUIRED,
                engineering_suitability=EngineeringSuitability.ENGINEERING_GRADE,
                is_authoritative=True,
                limitations="Official national benchmark for onshore wind capacity assessment.",
            )


gis_validator = EnvironmentalDatasetValidator()
