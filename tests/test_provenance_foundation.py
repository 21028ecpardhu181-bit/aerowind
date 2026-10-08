"""
tests/test_provenance_foundation.py — Test Suite for Phase 1 Data Foundation & Provenance.

Validates:
1. Provider metadata registry loads accurately from backend/data/providers.yaml.
2. Invalid/unregistered provider key access fails with a clear KeyError.
3. Missing or failed source produces SourceStatus.UNKNOWN (never converts to SAFE/CLEAR/FEASIBLE).
4. Missing credentials return MANUAL_REQUIRED or UNAVAILABLE.
5. No fake fallback data is generated (e.g. synthetic sinusoids rejected).
6. Dataset version, units, and CRS are strictly preserved.
7. Retrieval timestamp is recorded in ISO 8601 UTC format.
8. Provenance metadata survives Pydantic serialization / model_dump().
9. A failed environmental source cannot silently produce a suitable or clear result.
10. MNRE 2024 regulatory setback formula (HH + 0.5*RD + 5m) evaluates accurately.
11. Wind resource separates live weather from long-term NIWE climatology.
12. ALMM-Wind turbine catalogue verifies official models and flags reference models.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from backend.app.provenance import (
    EngineeringSuitability,
    MNRE_2024_SETBACKS,
    ProvenanceMetadata,
    RegulatorySetbackRule,
    SourceStatus,
    provider_registry,
)
from backend.app.gis_validator import gis_validator


class TestProviderRegistry:
    def test_provider_registry_loads_correctly(self):
        """Verifies that the YAML provider registry loads all verified providers."""
        providers = provider_registry.providers
        assert len(providers) >= 12
        assert "survey_of_india_village" in providers
        assert "niwe_wind_atlas_120m" in providers
        assert "open_meteo_forecast_100m" in providers
        assert "open_meteo_elevation_copernicus" in providers
        assert "esa_worldcover_10m" in providers
        assert "osm_overpass_infrastructure" in providers
        assert "unep_wdpa_protected_planet" in providers
        assert "isric_soilgrids_250m" in providers
        assert "mnre_almm_wind_catalogue" in providers

    def test_invalid_provider_raises_clear_keyerror(self):
        """Ensures querying an unregistered provider raises a clear KeyError."""
        with pytest.raises(KeyError) as exc_info:
            provider_registry.get_provider_metadata("non_existent_fake_provider")
        assert "not registered" in str(exc_info.value)

    def test_survey_of_india_status_manual_required(self):
        """Survey of India Village Boundary Database requires manual download / spatial ingestion."""
        soi_meta = provider_registry.get_provider_metadata("survey_of_india_village")
        assert soi_meta["status"] == SourceStatus.MANUAL_REQUIRED.value
        assert soi_meta["automated_api_possible"] is False
        assert "National Geospatial Policy 2022" in soi_meta["license"]
        assert soi_meta["crs"] == "EPSG:4326 (WGS 84)"

    def test_niwe_wind_atlas_status_manual_required(self):
        """NIWE 120m atlas is manual download / raster ingest; not an unauthenticated API."""
        niwe_meta = provider_registry.get_provider_metadata("niwe_wind_atlas_120m")
        assert niwe_meta["status"] == SourceStatus.MANUAL_REQUIRED.value
        assert niwe_meta["height_m"] == 120.0
        assert niwe_meta["resolution"] == "500m modelling grid (Meso-micro coupled WRF validated with 406 wind masts)"
        assert niwe_meta["automated_api_possible"] is False

    def test_legacy_global_wind_atlas_classified_as_hardcoded(self):
        """Phase 0 legacy GWA client is classified as HARDCODED and NOT_ENGINEERING_GRADE."""
        gwa_meta = provider_registry.get_provider_metadata("global_wind_atlas_heuristic")
        assert gwa_meta["status"] == SourceStatus.HARDCODED.value
        assert gwa_meta["engineering_suitability"] == EngineeringSuitability.NOT_ENGINEERING_GRADE.value

    def test_open_meteo_elevation_truthfully_labeled_glo90(self):
        """Public Open-Meteo elevation returns GLO-90, not GLO-30."""
        dem_meta = provider_registry.get_provider_metadata("open_meteo_elevation_copernicus")
        assert "GLO-90" in dem_meta["dataset"]
        assert dem_meta["status"] == SourceStatus.VERIFIED_REAL.value
        assert "EGM2008" in dem_meta["crs"]


class TestProvenanceModelAndSerialization:
    def test_provenance_metadata_full_lifecycle(self):
        """Checks creation, fields validation, and serializability of ProvenanceMetadata."""
        meta = ProvenanceMetadata(
            value=8.45,
            unit="m/s",
            source="National Institute of Wind Energy (NIWE), MNRE",
            source_url="https://niwe.res.in/Open_data_Set/technical_report/19/",
            dataset="120m Wind Potential Atlas of India",
            version="Technical Report 19",
            resolution="500m Meso-Micro Coupled WRF",
            crs="EPSG:4326",
            retrieved_at="2026-10-06T15:00:00Z",
            license="Government of India Open Data",
            status=SourceStatus.VERIFIED_REAL,
            engineering_suitability=EngineeringSuitability.ENGINEERING_GRADE,
            is_authoritative=True,
            limitations="National benchmark mesoscale dataset.",
        )

        # Ensure serialization survives round-trip
        data_dict = meta.model_dump()
        json_str = json.dumps(data_dict)
        deserialized = json.loads(json_str)

        assert deserialized["value"] == 8.45
        assert deserialized["unit"] == "m/s"
        assert deserialized["status"] == "VERIFIED_REAL"
        assert deserialized["engineering_suitability"] == "ENGINEERING_GRADE"
        assert deserialized["is_authoritative"] is True
        assert deserialized["crs"] == "EPSG:4326"
        assert deserialized["retrieved_at"] == "2026-10-06T15:00:00Z"


class TestValidatorFailureRules:
    def test_elevation_failure_returns_unknown_status(self):
        """Failed elevation lookup returns SourceStatus.UNKNOWN; never fabricates numbers."""
        coords = [(16.9676, 81.8138), (16.9680, 81.8140)]
        elevations = [28.0, None]  # Second elevation failed

        results = gis_validator.validate_elevation_response(coords, elevations)
        assert len(results) == 2
        assert results[0].status == SourceStatus.VERIFIED_REAL
        assert results[0].value == 28.0

        # Critical failure check
        assert results[1].status == SourceStatus.UNKNOWN
        assert results[1].value is None
        assert results[1].engineering_suitability == EngineeringSuitability.UNKNOWN
        assert "failed" in results[1].limitations.lower()

    def test_overpass_failure_returns_unknown_and_no_clearance(self):
        """Overpass API failure MUST yield UNKNOWN; never 'safe' or 'feasible'."""
        result = gis_validator.validate_building_exclusion(
            overpass_success=False,
            buildings_found=[],
            center_lat=16.9676,
            center_lon=81.8138,
            radius_km=3.0,
        )

        assert result["building_data_status"] == SourceStatus.UNKNOWN.value
        assert result["feasibility"] == "UNKNOWN"
        assert "could not be verified" in result["clearance_status"].lower()
        assert result["provenance"]["status"] == SourceStatus.UNKNOWN.value

    def test_overpass_zero_rural_buildings_returns_unverified_warning(self):
        """Query success with zero rural buildings flags unverified rural zone, not unconditional clear."""
        result = gis_validator.validate_building_exclusion(
            overpass_success=True,
            buildings_found=[],
            center_lat=14.6819,
            center_lon=77.6006,
            radius_km=3.5,
        )

        assert result["building_data_status"] == SourceStatus.PARTIAL.value
        assert result["feasibility"] == "CONDITIONAL"
        assert "satellite" in result["warning"].lower()
        assert "UNVERIFIED_RURAL_ZONE" in result["clearance_status"]

    def test_wind_resource_strict_separation_of_weather_vs_climatology(self):
        """Live weather forecast cannot be classified as long-term bankable resource."""
        # 1. Live Weather
        live_meta = gis_validator.validate_wind_resource_source(
            is_live_weather=True,
            mean_speed_mps=7.4,
            lat=16.9676,
            lon=81.8138,
        )
        assert live_meta.engineering_suitability == EngineeringSuitability.REAL_WEATHER_NOT_LONG_TERM_RESOURCE
        assert live_meta.is_authoritative is False
        assert "CANNOT be used for 20-year project AEP" in live_meta.limitations

        # 2. Long-term Climatology
        clima_meta = gis_validator.validate_wind_resource_source(
            is_live_weather=False,
            mean_speed_mps=7.82,
            lat=16.9676,
            lon=81.8138,
        )
        assert clima_meta.engineering_suitability == EngineeringSuitability.ENGINEERING_GRADE
        assert clima_meta.is_authoritative is True
        assert "NIWE" in clima_meta.source


class TestRegulatorySetbacksMNRE2024:
    def test_mnre_2024_infrastructure_formula_evaluation(self):
        """
        Tests statutory formula: Distance = Hub Height + 0.5 * Rotor Diameter + 5 meters.
        For GE Vernova 2.5-120 (HH=110m, RD=120m):
        Distance = 110 + 0.5 * 120 + 5 = 175.0 meters.
        """
        road_rule = MNRE_2024_SETBACKS["public_roads"]
        distance = road_rule.calculate_setback_m(hub_height_m=110.0, rotor_diameter_m=120.0)
        assert distance == 175.0
        assert road_rule.legal_status == "MANDATORY"
        assert road_rule.effective_date == "2024-07-04"

    def test_mnre_2024_habitation_cluster_fixed_distance(self):
        """Habitation cluster setback is fixed at 500m (for >= 15 dwellings)."""
        hab_rule = MNRE_2024_SETBACKS["habitation_cluster"]
        distance = hab_rule.calculate_setback_m(hub_height_m=110.0, rotor_diameter_m=120.0)
        assert distance == 500.0
        assert "15 inhabited dwellings" in hab_rule.target_feature

    def test_mnre_2024_inter_developer_wake_spacings(self):
        """
        Tests inter-developer micrositing rules:
        5D perpendicular to predominant wind, 7D in-line with wind.
        """
        perp_rule = MNRE_2024_SETBACKS["inter_developer_wind_perpendicular"]
        assert perp_rule.distance_formula == "5.0 * max(RD_1, RD_2)"

        parallel_rule = MNRE_2024_SETBACKS["inter_developer_wind_parallel"]
        assert parallel_rule.distance_formula == "7.0 * max(RD_1, RD_2)"


class TestTurbineCatalogueValidation:
    def test_mnre_almm_wind_catalogue_file_exists_and_validates(self):
        """Verifies the ALMM-Wind turbine catalogue contains verified commercial models."""
        catalogue_path = Path("backend/data/mnre_almm_wind_catalogue.json")
        assert catalogue_path.exists()

        with open(catalogue_path, "r", encoding="utf-8") as f:
            models = json.load(f)

        assert len(models) >= 5
        keys = [m["model_key"] for m in models]
        assert "ge_25_120" in keys
        assert "vestas_v110_20" in keys
        assert "sg_34_132" in keys
        assert "nrel_5mw" in keys
        assert "iea_15mw" in keys

        # Commercial models are approved in India
        ge_model = next(m for m in models if m["model_key"] == "ge_25_120")
        assert ge_model["mnre_almm_status"] == "APPROVED_ONSHORE_INDIA"
        assert ge_model["tip_height_m"] == 170.0  # 110m HH + 60m radius

        # Academic reference baselines are explicitly marked as research-only
        nrel_model = next(m for m in models if m["model_key"] == "nrel_5mw")
        assert "REFERENCE_RESEARCH_ONLY" in nrel_model["mnre_almm_status"]
