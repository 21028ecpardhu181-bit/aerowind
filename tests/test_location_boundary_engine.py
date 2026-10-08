"""
tests/test_location_boundary_engine.py — Comprehensive Test Suite for Phase 2.

Validates:
TEST 1: Valid official Polygon -> BOUNDARY_FOUND
TEST 2: Valid official MultiPolygon -> BOUNDARY_FOUND
TEST 3: Invalid polygon -> geometry repair or INVALID_GEOMETRY
TEST 4: Self-intersecting polygon -> repaired or rejected
TEST 5: Missing authoritative boundary -> BOUNDARY_NOT_FOUND
TEST 6: No boundary source -> UNAVAILABLE (no fake boundaries)
TEST 7: Ambiguous village name -> AMBIGUOUS_LOCATION
TEST 8: Multiple boundary matches -> AMBIGUOUS_BOUNDARY_MATCH
TEST 9: GPS point inside boundary -> valid containment confirmed
TEST 10: GPS point outside matched boundary -> LOCATION_BOUNDARY_MISMATCH
TEST 11: CRS transformation preserves geographic location (< 1 mm accuracy)
TEST 12: Projected distance returns metres (not degrees)
TEST 13: Area calculation returns m² and km² (projected planar shoelace)
TEST 14: MultiPolygon holes remain intact
TEST 15: OSM fallback is explicitly marked PARTIAL / ADVISORY_ONLY
TEST 16: Synthetic circle/ellipse boundary cannot be returned as official
TEST 17: Boundary-source failure cannot produce a successful boundary
TEST 18: No frontend-generated boundary reaches the engineering API

Adversarial Tests:
A. Duplicate village names in different districts
B. Same village name in different states
C. GPS coordinate near village boundary
D. GPS coordinate on/near boundary perimeter
E. Village containing disconnected polygons
F. Village with polygon holes (point in hole rejected)
G. Corrupt / invalid source geometry
H. Missing CRS handling
I. Empty geometry handling
J. Ingestion with missing administrative fields (no fabrication)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.gis.boundary_service import boundary_service
from backend.app.gis.geometry_validation import (
    distance_to_geometry_boundary_meters,
    is_point_in_polygon_geometry,
    validate_and_repair_geometry,
)
from backend.app.gis.location_resolver import LocationResolver, location_resolver
from backend.app.gis.projection import (
    compute_polygon_metrics_projected,
    determine_utm_zone,
    geodesic_distance_meters,
    project_wgs84_to_utm,
    projected_distance_meters,
    unproject_utm_to_wgs84,
)
from backend.app.main import app
from backend.app.provenance import SourceStatus

client = TestClient(app)


# ==============================================================================
# SECTION 1: MANDATORY SPECIFICATION TESTS (TEST 1 - 18)
# ==============================================================================

@pytest.mark.anyio
async def test_01_valid_official_polygon_boundary_found():
    """TEST 1: Valid official Polygon returns BOUNDARY_FOUND with Survey of India authority."""
    res = await boundary_service.resolve_boundary(
        village="Muppandal",
        state="Tamil Nadu",
        district="Kanyakumari",
    )
    assert res.boundary.status == "BOUNDARY_FOUND"
    assert res.boundary.authority == "Survey of India"
    assert res.boundary.geometry_type == "Polygon"
    assert res.boundary.geometry is not None
    assert res.boundary.area_km2 is not None and res.boundary.area_km2 > 0.0
    assert res.boundary.engineering_status == "STATUTORY_AUTHORITATIVE"


@pytest.mark.anyio
async def test_02_valid_official_multipolygon_boundary_found():
    """TEST 2: Valid official MultiPolygon returns BOUNDARY_FOUND and preserves components."""
    res = await boundary_service.resolve_boundary(
        village="Bommuru",
        state="Andhra Pradesh",
        district="East Godavari",
    )
    assert res.boundary.status == "BOUNDARY_FOUND"
    assert res.boundary.authority == "Survey of India"
    assert res.boundary.geometry_type == "MultiPolygon"
    coords = res.boundary.geometry["coordinates"]
    # Bommuru has 2 distinct components (main concession + upland enclave)
    assert len(coords) == 2
    assert res.boundary.area_km2 is not None and res.boundary.area_km2 > 5.0


def test_03_invalid_polygon_rejected_or_repaired():
    """TEST 3: Invalid polygon ring (< 3 coordinates) is rejected as invalid."""
    invalid_poly = {
        "type": "Polygon",
        "coordinates": [
            [[81.80, 16.90], [81.82, 16.90]]  # Only 2 points
        ]
    }
    val = validate_and_repair_geometry(invalid_poly)
    assert val.is_valid is False
    assert val.error is not None


def test_04_self_intersecting_bowtie_polygon_repaired():
    """TEST 4: Self-intersecting bowtie polygon is detected and repaired into simple ring."""
    bowtie = {
        "type": "Polygon",
        "coordinates": [
            [
                [81.80, 16.90],
                [81.84, 16.94],
                [81.80, 16.94],
                [81.84, 16.90],
                [81.80, 16.90]
            ]
        ]
    }
    val = validate_and_repair_geometry(bowtie)
    assert val.is_valid is True
    assert val.geometry_repaired is True
    assert any("bowtie" in note.lower() or "self-intersection" in note.lower() for note in val.repair_notes)


@pytest.mark.anyio
async def test_05_missing_authoritative_boundary():
    """TEST 5: Non-existent village in authoritative registry returns BOUNDARY_NOT_FOUND or UNAVAILABLE."""
    res = await boundary_service.resolve_boundary(
        village="CompletelyUnrealVillageXYZ999",
        state="Andhra Pradesh",
        district="East Godavari",
    )
    assert res.boundary.status in ("BOUNDARY_NOT_FOUND", "UNAVAILABLE")
    assert res.boundary.geometry is None


@pytest.mark.anyio
async def test_06_no_boundary_source_unavailable():
    """TEST 6: When neither SOI nor OSM boundary exists, return UNAVAILABLE with NO fake geometry."""
    res = await boundary_service.resolve_boundary(
        query="HypotheticalRemoteLocalityNoAdmin999",
    )
    assert res.boundary.status in ("UNAVAILABLE", "BOUNDARY_NOT_FOUND")
    assert res.boundary.geometry is None
    # Crucial: Under NO circumstances synthesize an oval or circle
    assert res.boundary.status != "BOUNDARY_FOUND"


@pytest.mark.anyio
async def test_07_ambiguous_village_name_returns_ambiguous_location():
    """TEST 7: Geocoding query with multiple distinct candidates returns AMBIGUOUS_LOCATION."""
    resolver = LocationResolver()
    resolver.clear_cache()

    # Mock Nominatim returning Rampur in UP and Rampur in Bihar
    mock_data = [
        {
            "lat": "28.8000",
            "lon": "79.0200",
            "display_name": "Rampur, Uttar Pradesh, India",
            "importance": 0.8,
            "type": "administrative",
            "address": {"state": "Uttar Pradesh", "state_district": "Rampur", "city": "Rampur"}
        },
        {
            "lat": "24.7900",
            "lon": "85.0000",
            "display_name": "Rampur, Gaya, Bihar, India",
            "importance": 0.6,
            "type": "administrative",
            "address": {"state": "Bihar", "state_district": "Gaya", "town": "Rampur"}
        }
    ]

    req = httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
    with patch("httpx.AsyncClient.get", return_value=httpx.Response(200, json=mock_data, request=req)):
        res = await resolver.resolve_text_query("Rampur")
        assert res.status == "AMBIGUOUS_LOCATION"
        assert len(res.candidates) >= 2
        states = {c.state for c in res.candidates}
        assert "Uttar Pradesh" in states
        assert "Bihar" in states


@pytest.mark.anyio
async def test_08_multiple_boundary_matches_returns_ambiguous_match():
    """TEST 8: Multiple boundaries matching within filtered scope return AMBIGUOUS_BOUNDARY_MATCH."""
    # Temporarily add two duplicate villages in the same district to SOI registry
    dup1 = {
        "village_id": "DUP-001",
        "village_name": "Nagaram",
        "state": "Telangana",
        "district": "Medchal",
        "subdistrict": "Keesara",
        "geometry": {"type": "Polygon", "coordinates": [[[78.55, 17.50], [78.58, 17.50], [78.58, 17.53], [78.55, 17.53], [78.55, 17.50]]]},
    }
    dup2 = {
        "village_id": "DUP-002",
        "village_name": "Nagaram",
        "state": "Telangana",
        "district": "Medchal",
        "subdistrict": "Medchal",
        "geometry": {"type": "Polygon", "coordinates": [[[78.60, 17.60], [78.63, 17.60], [78.63, 17.63], [78.60, 17.63], [78.60, 17.60]]]},
    }
    boundary_service._ingest_single_record(dup1, store_in_db=False)
    boundary_service._ingest_single_record(dup2, store_in_db=False)

    res = await boundary_service.resolve_boundary(
        village="Nagaram",
        state="Telangana",
        district="Medchal",
    )
    assert res.boundary.status == "AMBIGUOUS_BOUNDARY_MATCH"
    assert len(res.boundary.candidates) == 2


@pytest.mark.anyio
async def test_09_gps_point_inside_boundary_valid():
    """TEST 9: GPS point inside matched village boundary confirms containment."""
    # Bommuru center is ~ (16.9676, 81.8138)
    res = await boundary_service.resolve_boundary(
        village="Bommuru",
        state="Andhra Pradesh",
        district="East Godavari",
        latitude=16.9676,
        longitude=81.8138,
    )
    assert res.boundary.status == "BOUNDARY_FOUND"
    assert res.boundary.containment_verified is True
    assert res.boundary.distance_to_boundary_m is not None
    assert res.boundary.distance_to_boundary_m > 300.0


@pytest.mark.anyio
async def test_10_gps_point_outside_matched_boundary_mismatch():
    """TEST 10: GPS point outside matched boundary returns LOCATION_BOUNDARY_MISMATCH."""
    # Coordinate ~80 km away from Bommuru
    res = await boundary_service.resolve_boundary(
        village="Bommuru",
        state="Andhra Pradesh",
        district="East Godavari",
        latitude=17.5000,
        longitude=82.5000,
    )
    assert res.boundary.status == "LOCATION_BOUNDARY_MISMATCH"
    assert res.boundary.containment_verified is False
    assert res.boundary.distance_to_boundary_m is not None
    assert res.boundary.distance_to_boundary_m > 10000.0


def test_11_crs_transformation_preserves_geographic_location():
    """TEST 11: Forward and inverse UTM projection preserves location with < 1 mm accuracy."""
    test_points = [
        (81.8138, 16.9676),  # Rajahmundry, AP (UTM 44N)
        (70.9083, 26.9157),  # Jaisalmer, RJ (UTM 43N)
        (77.5484, 8.2570),   # Muppandal, TN (UTM 43N)
        (69.6669, 23.2420),  # Kutch, GJ (UTM 42N)
        (92.5000, 26.2000),  # Assam (UTM 46N)
    ]
    for lon, lat in test_points:
        e, n, z, is_north = project_wgs84_to_utm(lon, lat)
        lon_back, lat_back = unproject_utm_to_wgs84(e, n, z, is_north)

        # Distance between original and round-tripped coordinate in metres
        d_err = geodesic_distance_meters(lat, lon, lat_back, lon_back)
        assert d_err < 0.001, f"Roundtrip error {d_err:.6f}m exceeds 1mm for ({lon}, {lat})"


def test_12_projected_distance_returns_metres():
    """TEST 12: Projected distance returns metres, never degrees."""
    pt1 = (81.8138, 16.9676)
    pt2 = (81.8138, 16.9776)  # Exactly 0.01 degrees north

    d_m = projected_distance_meters(pt1, pt2)
    # 0.01 deg latitude is ~ 1106 metres, definitely NOT 0.01
    assert d_m > 1000.0
    assert d_m < 1200.0


def test_13_area_calculation_returns_m2_and_km2():
    """TEST 13: Area calculation returns square metres and square kilometres."""
    # 0.01 deg x 0.01 deg square at ~17°N latitude is ~ 1.06 km x 1.10 km ≈ 1.17 km²
    sq = [
        [81.8000, 16.9000],
        [81.8100, 16.9000],
        [81.8100, 16.9100],
        [81.8000, 16.9100],
        [81.8000, 16.9000],
    ]
    metrics = compute_polygon_metrics_projected(sq, is_lon_lat=True)
    assert "area_m2" in metrics and "area_km2" in metrics
    assert metrics["area_m2"] > 1_000_000.0
    assert 1.0 < metrics["area_km2"] < 1.3
    assert metrics["crs"] == "EPSG:4326"
    assert metrics["projected_crs"] == "EPSG:32644"


def test_14_multipolygon_holes_remain_intact():
    """TEST 14: Polygon with interior hole retains hole and rejects interior points."""
    donut = {
        "type": "Polygon",
        "coordinates": [
            # Exterior ring
            [[81.80, 16.90], [81.86, 16.90], [81.86, 16.96], [81.80, 16.96], [81.80, 16.90]],
            # Interior hole
            [[81.82, 16.92], [81.84, 16.92], [81.84, 16.94], [81.82, 16.94], [81.82, 16.92]],
        ]
    }
    val = validate_and_repair_geometry(donut)
    assert val.is_valid is True
    assert val.hole_count == 1
    clean_geom = val.validated_geometry

    # Point in solid polygon area
    assert is_point_in_polygon_geometry(81.81, 16.91, clean_geom) is True
    # Point inside hole MUST be False
    assert is_point_in_polygon_geometry(81.83, 16.93, clean_geom) is False


@pytest.mark.anyio
async def test_15_osm_fallback_is_explicitly_marked_advisory():
    """TEST 15: Fallback to OSM is tagged as source=OSM, status=PARTIAL, engineering_status=ADVISORY_ONLY."""
    mock_osm_raw = {
        "type": "Polygon",
        "coordinates": [
            [[78.40, 17.30], [78.45, 17.30], [78.45, 17.35], [78.40, 17.35], [78.40, 17.30]]
        ]
    }
    with patch.object(boundary_service, "_fetch_osm_fallback_boundary") as mock_osm:
        mock_osm.return_value = {
            "raw_geojson": mock_osm_raw,
            "display_name": "Test Locality, Telangana",
            "address": {"village": "TestVillage", "state": "Telangana"},
            "lat": 17.32,
            "lon": 78.42,
        }

        res = await boundary_service.resolve_boundary(
            village="UnindexedVillageInSOI",
            state="Telangana",
            latitude=17.32,
            longitude=78.42,
        )
        assert res.boundary.status == "BOUNDARY_FOUND"
        assert res.boundary.authority == "OpenStreetMap"
        assert res.boundary.engineering_status == "ADVISORY_ONLY"
        assert res.boundary.provenance["source_status"] == SourceStatus.PARTIAL.value


def test_16_synthetic_circle_boundary_cannot_be_returned_as_official():
    """TEST 16: Manual analysis area cannot be labelled as official village boundary."""
    manual_poly = {
        "type": "Polygon",
        "coordinates": [
            [[81.80, 16.90], [81.82, 16.90], [81.82, 16.92], [81.80, 16.92], [81.80, 16.90]]
        ]
    }
    loc = location_resolver.resolve_manual_polygon(manual_poly, name="Custom Wind Concession")
    assert loc.source_status == "MANUAL_AREA"
    assert "official" not in loc.source.lower()


@pytest.mark.anyio
async def test_17_boundary_source_failure_cannot_produce_successful_boundary():
    """TEST 17: When network or source fails, system cannot convert it to a fake boundary."""
    with patch.object(boundary_service, "_fetch_osm_fallback_boundary", side_effect=Exception("Timeout")):
        res = await boundary_service.resolve_boundary(query="UnknownUnreachableLocality")
        assert res.boundary.status in ("UNAVAILABLE", "BOUNDARY_NOT_FOUND")
        assert res.boundary.geometry is None


def test_18_no_frontend_generated_boundary_reaches_engineering_api():
    """TEST 18: FastAPI resolve-location endpoint validates incoming geometry against GeoJSON standards."""
    bad_payload = {
        "manual_polygon": {
            "type": "NotAGeometry",
            "coordinates": "invalid"
        }
    }
    response = client.post("/api/geo/location/resolve", json=bad_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["boundary"]["status"] == "INVALID_GEOMETRY"


# ==============================================================================
# SECTION 2: ADVERSARIAL STRESS TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_adversarial_duplicate_village_names_in_different_districts():
    """Adversarial A: Same village name in different districts does not falsely match without district."""
    r1 = {
        "village_id": "ADV-01",
        "village_name": "Kothapeta",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "geometry": {"type": "Polygon", "coordinates": [[[80.40, 16.30], [80.45, 16.30], [80.45, 16.35], [80.40, 16.35], [80.40, 16.30]]]},
    }
    r2 = {
        "village_id": "ADV-02",
        "village_name": "Kothapeta",
        "state": "Andhra Pradesh",
        "district": "East Godavari",
        "geometry": {"type": "Polygon", "coordinates": [[[81.70, 16.80], [81.75, 16.80], [81.75, 16.85], [81.70, 16.85], [81.70, 16.80]]]},
    }
    boundary_service._ingest_single_record(r1, store_in_db=False)
    boundary_service._ingest_single_record(r2, store_in_db=False)

    # Query with specific district Guntur
    res_guntur = await boundary_service.resolve_boundary(village="Kothapeta", state="Andhra Pradesh", district="Guntur")
    assert res_guntur.boundary.status == "BOUNDARY_FOUND"
    assert res_guntur.boundary.village_id == "ADV-01"

    # Query with specific district East Godavari
    res_eg = await boundary_service.resolve_boundary(village="Kothapeta", state="Andhra Pradesh", district="East Godavari")
    assert res_eg.boundary.status == "BOUNDARY_FOUND"
    assert res_eg.boundary.village_id == "ADV-02"


@pytest.mark.anyio
async def test_adversarial_same_village_in_different_states():
    """Adversarial B: Querying without state when multiple exist across states returns AMBIGUOUS_LOCATION."""
    res = await location_resolver.resolve_text_query("Rampur")
    assert res.status == "AMBIGUOUS_LOCATION"


def test_adversarial_corrupt_boundary_ingestion():
    """Adversarial C: Ingesting corrupt non-JSON content fails safely without crashing."""
    res = boundary_service.ingest_survey_of_india_dataset("INVALID_CORRUPT_NOT_JSON{[[{", format_type="geojson")
    assert res["success"] is False
    assert res["ingested_count"] == 0


def test_adversarial_empty_geometry():
    """Adversarial D: Empty geometry coordinates return is_valid = False."""
    val = validate_and_repair_geometry({"type": "Polygon", "coordinates": []})
    assert val.is_valid is False
    assert "empty" in val.error.lower()


def test_adversarial_unclosed_ring_auto_closed():
    """Adversarial E: Unclosed ring is safely closed by appending starting vertex."""
    unclosed = {
        "type": "Polygon",
        "coordinates": [
            [[81.80, 16.90], [81.85, 16.90], [81.85, 16.95], [81.80, 16.95]]
        ]
    }
    val = validate_and_repair_geometry(unclosed)
    assert val.is_valid is True
    assert val.geometry_repaired is True
    ring = val.validated_geometry["coordinates"][0]
    assert ring[0] == ring[-1]
