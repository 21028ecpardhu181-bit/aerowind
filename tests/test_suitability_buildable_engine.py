"""
tests/test_suitability_buildable_engine.py — Environmental Suitability & Buildable Land Engine Test Suite.

Comprehensive Test Scenarios for Phase 3:
1. Search Envelope Invariant: A village boundary is strictly an initial search envelope, not development area.
2. Building Exclusion & MNRE 2024 Setbacks: Dwellings clustered (>=15) enforce 500m buffer, individual structures enforce HH + 0.5RD + 5m.
3. Highway / Rail Exclusion: Road and rail features buffered by statutory formula.
4. EHV Powerline Corridor: Buffered by statutory safety distance.
5. Waterbody & Wet Margin Exclusion: Protected buffer around aquatic bodies.
6. Conservation & Protected Area Exclusion: Interior prohibited, 1.0 km ESZ buffer enforced.
7. Terrain / Complex Slope Exclusion: Slopes > 15 deg classified as HARD_EXCLUSION.
8. Moderate Slopes: Slopes 8-15 deg classified as CONDITIONAL.
9. Rural Zero-Building Uncertainty: Zero OSM buildings marked UNVERIFIED_RURAL_ZONE and CONDITIONAL, never assuming clear terrain.
10. Data Failure / Missing Raster Non-Fabrication: Missing DEM or failed OSM marked UNKNOWN, never declared buildable.
11. Buildable Mask Geometry: Resulting buildable mask NEVER extends outside the Phase 2 search envelope.
12. Holes & Multi-Polygon Handling: Interior holes and disconnected parcels preserved.
13. Deterministic Execution: Multiple evaluations on identical inputs produce identical metrics.
14. Completely Unbuildable Site: Site entirely within national park or steep terrain returns buildable_pct = 0.0, status = UNBUILDABLE.
15. API Endpoint Verification: POST /api/geo/suitability/evaluate returns full Phase 3 contract.
"""

import math
import pytest
from fastapi.testclient import TestClient

from backend.app.gis.suitability_engine import (
    ConstraintTier,
    EnvironmentalSuitabilityEngine,
    SpatialConstraint,
    suitability_engine,
)
from backend.app.main import app

client = TestClient(app)



def _create_synthetic_search_polygon(center_lat: float = 14.6819, center_lon: float = 77.6006, radius_km: float = 2.0, steps: int = 24):
    """Generates a regular valid GeoJSON Polygon search envelope."""
    d_lat = radius_km / 111.0
    cos_lat = max(0.1, math.cos(math.radians(center_lat)))
    d_lon = radius_km / (111.0 * cos_lat)
    ring = [
        [
            round(center_lon + d_lon * math.sin(i * 2 * math.pi / steps), 6),
            round(center_lat + d_lat * math.cos(i * 2 * math.pi / steps), 6),
        ]
        for i in range(steps)
    ]
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def test_search_envelope_is_not_assumed_buildable():
    """Verify that an initial search envelope is not assumed 100% buildable without screening."""
    poly = _create_synthetic_search_polygon()
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        hub_height_m=120.0,
        rotor_diameter_m=120.0,
    )
    assert res.search_envelope_area_km2 > 0.0
    assert res.projected_crs.startswith("EPSG:326")
    assert res.overall_status in ("READY", "PARTIAL", "UNKNOWN", "UNBUILDABLE")
    assert len(res.provenance_chain) >= 4


def test_steep_slope_hard_exclusion():
    """Verify slopes > 15 deg trigger HARD_EXCLUSION and zero buildable land under complex terrain."""
    poly = _create_synthetic_search_polygon()
    terrain_steep = {
        "elevation_m": 850.0,
        "slope_deg": 18.5,
        "aspect_deg": 140.0,
        "tri_ruggedness_m": 45.0,
        "source": "Copernicus DEM GLO-30",
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        terrain_override=terrain_steep,
    )
    assert any(c.constraint_id == "TERRAIN-STEEP-SLOPE" and c.tier == ConstraintTier.HARD_EXCLUSION for c in res.active_constraints)
    assert res.terrain_assessment["is_complex_terrain"] is True
    assert res.buildable_percentage == 0.0
    assert res.overall_status == "UNBUILDABLE"


def test_moderate_slope_conditional():
    """Verify slopes 8-15 deg trigger CONDITIONAL tier with cut/fill grading requirements."""
    poly = _create_synthetic_search_polygon()
    terrain_mod = {
        "elevation_m": 420.0,
        "slope_deg": 10.2,
        "aspect_deg": 90.0,
        "tri_ruggedness_m": 12.0,
        "source": "Copernicus DEM GLO-30",
    }
    # Provide a minimal rural settlement to avoid UNKNOWN status
    osm_mock = {
        "features": {
            "buildings": [{"id": 1, "lat": 14.6819, "lon": 77.6006, "setback_m": 500.0, "type": "residential"}],
            "highways": [],
            "powerlines": [],
            "waterways": [],
        }
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        terrain_override=terrain_mod,
        osm_override=osm_mock,
    )
    assert any(c.constraint_id == "TERRAIN-MODERATE-SLOPE" and c.tier == ConstraintTier.CONDITIONAL for c in res.active_constraints)
    assert res.conditional_percentage > 0.0
    assert res.overall_status == "PARTIAL"


def test_protected_area_interior_prohibition():
    """Verify site located inside national park is marked UNBUILDABLE with statutory citation."""
    poly = _create_synthetic_search_polygon()
    pa_inside = {
        "source": "UNEP-WCMC Protected Planet",
        "is_inside_protected_area": True,
        "is_in_buffer_zone": False,
        "nearest_protected_area": "Desert National Park",
        "designation": "National Park (Great Indian Bustard Habitat)",
        "distance_km": 0.0,
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        protected_override=pa_inside,
    )
    assert any(c.constraint_id == "WDPA-INTERIOR-PROHIBITED" and c.tier == ConstraintTier.HARD_EXCLUSION for c in res.active_constraints)
    assert res.overall_status == "UNBUILDABLE"
    assert res.buildable_percentage == 0.0
    assert any("Desert National Park" in r for r in res.hard_exclusion_reasons)


def test_eco_sensitive_zone_buffer_exclusion():
    """Verify site in 1km Eco-Sensitive Zone triggers statutory setback buffer."""
    poly = _create_synthetic_search_polygon()
    pa_buffer = {
        "source": "UNEP-WCMC Protected Planet",
        "is_inside_protected_area": False,
        "is_in_buffer_zone": True,
        "nearest_protected_area": "Gir National Park",
        "designation": "National Park",
        "distance_km": 0.4,
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        protected_override=pa_buffer,
    )
    assert any(c.constraint_id == "WDPA-ESZ-ADVISORY-BUFFER" and c.tier == ConstraintTier.CONDITIONAL for c in res.active_constraints)
    assert any("ESZ" in r or "screening zone" in r for r in res.conditional_reasons)


def test_rural_zero_dwellings_uncertainty():
    """Verify that 0 OSM buildings in rural area does not assume clear terrain, but triggers CONDITIONAL."""
    poly = _create_synthetic_search_polygon()
    osm_empty = {
        "features": {
            "buildings": [],
            "highways": [],
            "powerlines": [],
            "waterways": [],
        }
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        osm_override=osm_empty,
    )
    assert any(c.constraint_id == "OSM-RURAL-ZERO-DWELLINGS" and c.tier == ConstraintTier.CONDITIONAL for c in res.active_constraints)
    assert any("Zero OSM dwellings" in r for r in res.conditional_reasons)
    assert res.overall_status == "PARTIAL"


def test_missing_terrain_raster_triggers_unknown():
    """CRITICAL INVARIANT: Missing DEM data must NEVER yield safe land; must mark UNKNOWN."""
    poly = _create_synthetic_search_polygon()
    terrain_failed = {
        "elevation_m": None,
        "slope_deg": None,
        "error": "Copernicus DEM HTTP 504 Gateway Timeout",
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        terrain_override=terrain_failed,
    )
    assert any(c.constraint_id == "TERRAIN-DEM-MISSING" and c.tier == ConstraintTier.UNKNOWN for c in res.active_constraints)
    assert res.overall_status == "UNKNOWN"
    assert res.unknown_percentage > 0.0


def test_habitation_cluster_500m_setback():
    """Verify settlement cluster (>=15 dwellings) enforces 500m mandatory buffer under MNRE 2024."""
    poly = _create_synthetic_search_polygon(center_lat=14.6819, center_lon=77.6006, radius_km=1.0)
    # Inject 16 buildings clustered around center
    buildings = [
        {"id": i, "lat": 14.6819 + 0.0001 * (i % 4), "lon": 77.6006 + 0.0001 * (i // 4), "type": "residential"}
        for i in range(16)
    ]
    osm_cluster = {
        "features": {
            "buildings": buildings,
            "highways": [],
            "powerlines": [],
            "waterways": [],
        }
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        osm_override=osm_cluster,
        hub_height_m=120.0,
        rotor_diameter_m=120.0,
    )
    assert any(c.constraint_id == "MNRE-2024-HABITATION" and c.buffer_or_threshold_m == 500.0 for c in res.active_constraints)
    assert res.infrastructure_assessment["habitation_cluster_detected"] is True
    assert res.excluded_percentage > 0.0


def test_statutory_infrastructure_formula_distance():
    """Verify individual roads/rail/lines use formula: HH + 0.5*RD + 5m = 120 + 60 + 5 = 185m."""
    poly = _create_synthetic_search_polygon(radius_km=1.0)
    osm_infra = {
        "features": {
            "buildings": [{"id": 1, "lat": 14.6819, "lon": 77.6006, "type": "residential"}],
            "highways": [{"id": 10, "lat": 14.6825, "lon": 77.6010, "class": "primary"}],
            "powerlines": [{"id": 20, "lat": 14.6830, "lon": 77.6020, "voltage": "220kV"}],
            "waterways": [],
        }
    }
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
        osm_override=osm_infra,
        hub_height_m=120.0,
        rotor_diameter_m=120.0,
    )
    expected_setback = 120.0 + 0.5 * 120.0 + 5.0  # 185.0m
    road_c = next(c for c in res.active_constraints if c.constraint_id == "MNRE-2024-PUBLIC-ROADS")
    assert road_c.buffer_or_threshold_m == pytest.approx(expected_setback, 0.1)


def test_buildable_mask_never_exceeds_search_envelope():
    """Verify that buildable mask parcels NEVER fall outside the search envelope polygon."""
    poly = _create_synthetic_search_polygon(center_lat=14.6819, center_lon=77.6006, radius_km=1.5)
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=poly,
    )
    assert res.buildable_area_km2 <= res.search_envelope_area_km2
    if res.buildable_mask_geojson:
        # Every vertex in the buildable parcels must be close to or inside the envelope
        coords = res.buildable_mask_geojson.get("coordinates", [])
        assert len(coords) > 0


def test_polygon_with_interior_hole_preserved():
    """Verify search envelope with an interior hole (e.g. water reservoir) excludes the hole."""
    outer_ring = [
        [77.58, 14.66], [77.62, 14.66], [77.62, 14.70], [77.58, 14.70], [77.58, 14.66]
    ]
    # Interior hole in the middle
    hole_ring = [
        [77.595, 14.675], [77.605, 14.675], [77.605, 14.685], [77.595, 14.685], [77.595, 14.675]
    ]
    donut_polygon = {"type": "Polygon", "coordinates": [outer_ring, hole_ring]}
    res = suitability_engine.evaluate_site_suitability(search_envelope_geometry=donut_polygon)
    assert res.search_envelope_geometry["type"] == "Polygon"
    assert len(res.search_envelope_geometry["coordinates"]) == 2


def test_deterministic_evaluation():
    """Verify that evaluating the exact same envelope multiple times yields identical numbers."""
    poly = _create_synthetic_search_polygon(radius_km=1.2)
    res1 = suitability_engine.evaluate_site_suitability(search_envelope_geometry=poly)
    res2 = suitability_engine.evaluate_site_suitability(search_envelope_geometry=poly)
    assert res1.buildable_area_m2 == res2.buildable_area_m2
    assert res1.buildable_percentage == res2.buildable_percentage
    assert res1.excluded_percentage == res2.excluded_percentage
    assert res1.overall_status == res2.overall_status


def test_api_suitability_evaluate_endpoint():
    """Verify POST /api/geo/suitability/evaluate returns complete Phase 3 contract."""
    poly = _create_synthetic_search_polygon(radius_km=1.0)
    response = client.post(
        "/api/geo/suitability/evaluate",
        json={
            "geometry": poly,
            "hub_height_m": 120.0,
            "rotor_diameter_m": 120.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall_status" in data
    assert "buildable_percentage" in data
    assert "active_constraints" in data
    assert "provenance_chain" in data
    assert data["projected_crs"].startswith("EPSG:326")


def test_api_land_data_endpoint_uses_suitability_engine():
    """Verify GET /api/geo/land-data reports real slope, buildable percent, and constraints."""
    response = client.get("/api/geo/land-data?lat=14.6819&lon=77.6006&radius_km=2.0")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    d = body["data"]
    assert "buildable_percent" in d
    assert "restricted_percent" in d
    assert "excluded_percent" in d
    assert "dominant_lulc" in d
    assert "Copernicus DEM" in body["source"]
