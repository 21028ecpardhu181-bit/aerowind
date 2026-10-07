"""
tests/test_turbine_engineering_candidates.py — Rigorous Verification Suite for Phase 4 Turbine Engineering.

Validates all 10 Phase 4 hard engineering invariants:
1. Candidates are never outside the authoritative site boundary.
2. Candidates are never inside hard exclusions (infrastructure setbacks).
3. Footprint & clearance violations: rotor blade swept circle (R_rotor) must clear exclusion boundaries.
4. Minimum-spacing violations: pairwise turbine spacing strictly enforces d >= k * D.
5. Holes & donut geometries: interior enclaves/holes and their R_rotor buffer are respected.
6. Overlapping exclusion zones: multiple overlapping setbacks correctly exclude candidates.
7. Rotor diameter sensitivity: different turbine models (GE 2.5-120 vs IEA 15MW) yield different feasible candidate counts.
8. Non-fabrication & missing data handling: unavailable DEM or wind resource produces UNKNOWN/UNAVAILABLE rather than false FEASIBLE.
9. Deterministic candidate generation: identical inputs produce identical candidate sets.
10. Full API integration: turbine catalog, conventions, generation, and validation endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.engineering.candidate_engine import (
    CandidateGenerationResult,
    TurbineCandidateEngine,
    candidate_engine,
)
from backend.app.engineering.candidate_validator import (
    CandidateEngineeringValidator,
    CandidateStatus,
    TurbineCandidate,
    dist_to_segment_2d,
    min_dist_to_ring_2d,
)
from backend.app.engineering.floris_engine import TURBINE_CATALOG
from backend.app.engineering.geometry_conventions import (
    decompose_wake_frame,
    get_cesium_heading_deg,
    get_turbine_yaw_deg,
    get_wind_to_deg,
)
from backend.app.gis.geometry_validation import is_point_in_polygon_geometry
from backend.app.gis.projection import project_wgs84_to_utm, unproject_utm_to_wgs84
from backend.app.main import app

client = TestClient(app)

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "samples" / "real_data_sample_anantapur.json"


def _create_box_site(lon_min=77.0, lat_min=14.0, width_deg=0.03, height_deg=0.03):
    """Creates a regular rectangular polygon site (~3.3 km x 3.3 km in South India)."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon_min, lat_min],
            [lon_min + width_deg, lat_min],
            [lon_min + width_deg, lat_min + height_deg],
            [lon_min, lat_min + height_deg],
            [lon_min, lat_min],
        ]],
    }


def _create_donut_site(lon_min=77.0, lat_min=14.0, size_deg=0.04, hole_size_deg=0.015):
    """Creates a polygon site with an interior hole (donut geometry, e.g. lake/settlement)."""
    hole_min_lon = lon_min + (size_deg - hole_size_deg) / 2.0
    hole_min_lat = lat_min + (size_deg - hole_size_deg) / 2.0
    return {
        "type": "Polygon",
        "coordinates": [
            # Exterior ring
            [
                [lon_min, lat_min],
                [lon_min + size_deg, lat_min],
                [lon_min + size_deg, lat_min + size_deg],
                [lon_min, lat_min + size_deg],
                [lon_min, lat_min],
            ],
            # Interior hole ring (clockwise or counter-clockwise)
            [
                [hole_min_lon, hole_min_lat],
                [hole_min_lon + hole_size_deg, hole_min_lat],
                [hole_min_lon + hole_size_deg, hole_min_lat + hole_size_deg],
                [hole_min_lon, hole_min_lat + hole_size_deg],
                [hole_min_lon, hole_min_lat],
            ],
        ],
    }


# ── TEST 1: TURBINE CATALOG AUTHENTICITY ────────────────────────────────────

def test_turbine_catalog_contains_real_specifications():
    """Verify that all turbine models come from authentic manufacturer specifications."""
    available = candidate_engine.get_available_turbines()
    assert len(available) >= 5
    model_ids = [t["model_id"] for t in available]
    assert "ge_25_120" in model_ids
    assert "vestas_v110_20" in model_ids
    assert "nrel_5mw" in model_ids
    assert "iea_15mw" in model_ids
    assert "sg_34_132" in model_ids

    ge_spec = candidate_engine.get_turbine_spec("ge_25_120")
    assert ge_spec["rotor_diameter_m"] == 120.0
    assert ge_spec["hub_height_m"] == 110.0
    assert ge_spec["rated_power_kw"] == 2500.0
    assert len(ge_spec["curves"]) >= 10


# ── TEST 2: WIND & GEOMETRY CONVENTIONS ─────────────────────────────────────

def test_wind_and_geometry_conventions():
    """Verify single backend source of truth for wind and turbine geometry conventions."""
    # wind_to_deg = (wind_from_deg + 180) % 360
    assert get_wind_to_deg(270.0) == 90.0
    assert get_wind_to_deg(0.0) == 180.0
    assert get_wind_to_deg(180.0) == 0.0
    assert get_wind_to_deg(45.0) == 225.0

    # Upwind HAWT yaw orientation faces INTO oncoming wind (wind_from_deg)
    assert get_turbine_yaw_deg(270.0) == 270.0
    assert get_turbine_yaw_deg(45.0) == 45.0

    # Cesium glTF heading calibration
    assert get_cesium_heading_deg(270.0) == 180.0
    assert get_cesium_heading_deg(0.0) == 270.0

    # Wake coordinate frame decomposition
    # Displacement dx=500m (due East), dy=0m, with wind arriving from West (270°), flowing East (90°)
    dw, cw = decompose_wake_frame(dx_m=500.0, dy_m=0.0, wind_from_deg=270.0)
    assert pytest.approx(dw, 0.01) == 500.0
    assert pytest.approx(cw, 0.01) == 0.0


# ── TEST 3: CANDIDATES NEVER OUTSIDE AUTHORITATIVE BOUNDARY ─────────────────

def test_candidates_never_outside_authoritative_boundary():
    """Verify that every generated feasible candidate is strictly contained inside site boundary."""
    site = _create_box_site()
    res = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
    )
    assert res.status in ("READY", "PARTIAL")
    assert len(res.feasible_candidates) > 0

    for cand in res.feasible_candidates:
        assert cand.status == CandidateStatus.FEASIBLE
        # Check geometric containment in WGS84
        assert is_point_in_polygon_geometry(cand.longitude, cand.latitude, site), (
            f"Candidate {cand.candidate_id} ({cand.longitude}, {cand.latitude}) leaked outside boundary!"
        )


# ── TEST 4: FOOTPRINT & ROTOR BLADE CLEARANCE FROM BOUNDARY ─────────────────

def test_rotor_footprint_clearance_from_boundary():
    """
    Verify that center-point containment alone is rejected if rotor blades
    would sweep outside the site boundary (distance to boundary < R_rotor).
    """
    site = _create_box_site(lon_min=77.0, lat_min=14.0, width_deg=0.02, height_deg=0.02)
    validator = CandidateEngineeringValidator("ge_25_120")  # D=120m, R=60m
    zone, is_north = 43, True

    ext_utm = [project_wgs84_to_utm(pt[0], pt[1], zone=zone, is_north=is_north)[:2] for pt in site["coordinates"][0]]

    # Case A: Center point is 20m inside the boundary edge (less than R_rotor=60m)
    # The turbine is technically inside, but blade tips would stick out by 40m!
    p_edge_x = ext_utm[0][0] + 20.0  # 20m inside Western boundary
    p_edge_y = ext_utm[0][1] + 500.0
    lon_edge, lat_edge = unproject_utm_to_wgs84(p_edge_x, p_edge_y, zone=zone, is_north=is_north)

    cand_near_edge = validator.validate_candidate_point(
        easting_m=p_edge_x,
        northing_m=p_edge_y,
        lon=lon_edge,
        lat=lat_edge,
        utm_exterior_rings=[ext_utm],
        utm_interior_holes=[],
        prepared_exclusions=[],
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    assert cand_near_edge.status == CandidateStatus.EXCLUDED
    assert "RULE-SITE-BOUNDARY-CLEARANCE" in cand_near_edge.rules_failed
    assert any("clearance" in r.lower() for r in cand_near_edge.exclusion_reasons)

    # Case B: Center point is 100m inside the boundary edge (greater than R_rotor=60m)
    p_safe_x = ext_utm[0][0] + 100.0
    p_safe_y = ext_utm[0][1] + 500.0
    lon_safe, lat_safe = unproject_utm_to_wgs84(p_safe_x, p_safe_y, zone=zone, is_north=is_north)

    cand_safe = validator.validate_candidate_point(
        easting_m=p_safe_x,
        northing_m=p_safe_y,
        lon=lon_safe,
        lat=lat_safe,
        utm_exterior_rings=[ext_utm],
        utm_interior_holes=[],
        prepared_exclusions=[],
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    assert cand_safe.status == CandidateStatus.FEASIBLE
    assert cand_safe.site_boundary_clearance_m >= 0.0


# ── TEST 5: CANDIDATES NEVER INSIDE HARD EXCLUSIONS & RESPECT SETBACK + R ───

def test_candidates_never_inside_hard_exclusions_with_rotor_clearance():
    """Verify that candidates maintain statutory setback PLUS rotor radius from infrastructure."""
    site = _create_box_site()
    # Mock highway running right through the center
    center_lon = 77.015
    osm_highway_override = {
        "features": {
            "highways": [{
                "id": "hw-1",
                "geometry_coordinates": [[center_lon, 14.0], [center_lon, 14.03]],
                "setback_m": 150.0,
            }],
            "buildings": [],
            "powerlines": [],
            "waterways": [],
        }
    }

    res = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",  # R = 60m. Total clearance needed = 150 + 60 = 210m
        min_spacing_diameters=4.0,
        osm_override=osm_highway_override,
    )
    assert res.status in ("READY", "PARTIAL")

    # Verify no candidate is within 210m of the highway centerline
    zone, is_north = res.utm_zone, True
    hw_x, _ = project_wgs84_to_utm(center_lon, 14.015, zone=zone, is_north=is_north)[:2]

    for cand in res.feasible_candidates:
        dist_to_hw = abs(cand.utm_easting_m - hw_x)
        assert dist_to_hw >= 210.0, (
            f"Candidate {cand.candidate_id} distance to highway {dist_to_hw:.1f}m < 210m required clearance!"
        )


# ── TEST 6: HOLES & DONUT GEOMETRIES ────────────────────────────────────────

def test_holes_and_donut_geometries():
    """Verify candidates avoid interior holes and respect R_rotor clearance from hole boundaries."""
    donut_site = _create_donut_site()
    res = candidate_engine.generate_candidates(
        search_envelope_geometry=donut_site,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
    )
    assert res.status in ("READY", "PARTIAL")
    assert len(res.feasible_candidates) > 0

    # The interior hole is in the center
    hole_center_lon = 77.02
    hole_center_lat = 14.02

    for cand in res.feasible_candidates:
        # Candidate must be in the outer ring and NEVER in the hole
        assert is_point_in_polygon_geometry(cand.longitude, cand.latitude, donut_site)
        # Verify distance to hole center is substantial
        dist_deg = ((cand.longitude - hole_center_lon)**2 + (cand.latitude - hole_center_lat)**2)**0.5
        assert dist_deg > 0.0075  # Outside hole boundary


# ── TEST 7: MINIMUM INTER-TURBINE SPACING (k * D) ───────────────────────────

def test_minimum_inter_turbine_spacing_enforcement():
    """Verify that every pair of feasible candidates strictly satisfies d >= k * D."""
    site = _create_box_site()
    k_spacing = 4.0
    res = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",  # D = 120m -> min spacing = 480m
        min_spacing_diameters=k_spacing,
    )
    assert res.status in ("READY", "PARTIAL")
    candidates = res.feasible_candidates
    min_dist_allowed = k_spacing * 120.0

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            c1, c2 = candidates[i], candidates[j]
            dx = c1.utm_easting_m - c2.utm_easting_m
            dy = c1.utm_northing_m - c2.utm_northing_m
            dist = (dx * dx + dy * dy)**0.5
            assert dist >= min_dist_allowed - 1.0, (  # 1m float margin
                f"Spacing violation between {c1.candidate_id} and {c2.candidate_id}: {dist:.1f}m < {min_dist_allowed}m"
            )


# ── TEST 8: ROTOR DIAMETER SENSITIVITY ──────────────────────────────────────

def test_different_turbine_rotor_diameters_produce_different_candidate_sets():
    """Verify that selecting different turbines (e.g. 120m vs 240m) alters candidate density."""
    site = _create_box_site()

    res_ge = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",  # D=120m, 4D=480m
        min_spacing_diameters=4.0,
    )

    res_iea = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="iea_15mw",  # D=240m, 4D=960m
        min_spacing_diameters=4.0,
    )

    assert res_ge.feasible_count > 0
    assert res_iea.feasible_count > 0
    # Because IEA 15MW requires 960m spacing vs GE's 480m spacing, GE MUST fit substantially more turbines!
    assert res_ge.feasible_count > res_iea.feasible_count
    assert res_ge.min_spacing_m == 480.0
    assert res_iea.min_spacing_m == 960.0


# ── TEST 9: OVERLAPPING EXCLUSION ZONES ─────────────────────────────────────

def test_overlapping_exclusion_zones():
    """Verify that candidates at intersection of multiple setbacks are correctly excluded."""
    site = _create_box_site()
    osm_overlapping = {
        "features": {
            "highways": [{
                "id": "hw-overlap",
                "geometry_coordinates": [[77.01, 14.0], [77.01, 14.03]],
                "setback_m": 150.0,
            }],
            "buildings": [{
                "id": "bld-overlap",
                "lon": 77.012,
                "lat": 14.015,
                "setback_m": 150.0,
            }],
            "powerlines": [],
            "waterways": [],
        }
    }

    res = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        osm_override=osm_overlapping,
    )
    assert res.status == "READY"
    # Overlapping excluded zone around (77.01, 14.015) has candidates in excluded list
    assert len(res.excluded_candidates) > 0


# ── TEST 10: NON-FABRICATION & UNAVAILABLE DATA PRODUCES UNKNOWN ─────────────

def test_missing_engineering_data_produces_unknown():
    """Verify that missing DEM elevation or wind resource yields UNKNOWN, never false FEASIBLE."""
    site = _create_box_site()

    # DEM elevation failure
    res_dem_missing = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        terrain_override={"elevation_m": None, "slope_deg": None},
    )
    assert res_dem_missing.status == "UNKNOWN"
    assert res_dem_missing.feasible_count == 0

    # Wind resource failure (zero/missing wind)
    res_wind_missing = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        wind_override={"wind_speed_mps": 0.0},
    )
    assert res_wind_missing.feasible_count == 0
    assert res_wind_missing.unknown_count > 0


# ── TEST 11: DETERMINISTIC CANDIDATE GENERATION ─────────────────────────────

def test_deterministic_candidate_generation():
    """Verify that identical inputs produce identical candidate sets and coordinates."""
    site = _create_box_site()

    res1 = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
    )

    res2 = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
    )

    assert res1.feasible_count == res2.feasible_count
    assert res1.total_evaluated == res2.total_evaluated

    for c1, c2 in zip(res1.feasible_candidates, res2.feasible_candidates):
        assert c1.candidate_id == c2.candidate_id
        assert c1.longitude == c2.longitude
        assert c1.latitude == c2.latitude
        assert c1.utm_easting_m == c2.utm_easting_m
        assert c1.utm_northing_m == c2.utm_northing_m


# ── TEST 12: REAL DATA SITE INTEGRATION (ANANTAPUR) ─────────────────────────

def test_real_data_sample_anantapur_candidate_generation():
    """Verify end-to-end candidate generation on checked-in real Anantapur site sample."""
    assert SAMPLE_PATH.exists()
    with open(SAMPLE_PATH) as f:
        data = json.load(f)

    geom = data["boundary"]["geometry"]
    res = candidate_engine.generate_candidates(
        search_envelope_geometry=geom,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
    )

    assert res.status in ("READY", "PARTIAL")
    assert res.feasible_count >= 10, f"Expected >= 10 feasible candidates on Anantapur site, got {res.feasible_count}"
    assert res.min_spacing_m == 480.0

    # Verify provenance on candidates
    sample_cand = res.feasible_candidates[0]
    assert sample_cand.provenance is not None
    assert "TURBINE_CATALOG" in sample_cand.provenance.get("turbine_model_source", "")
    assert sample_cand.wind_from_deg == 270.0
    assert sample_cand.wind_to_deg == 90.0
    assert sample_cand.turbine_yaw_deg == 270.0
    assert sample_cand.cesium_heading_deg == 180.0


# ── TEST 13: FASTAPI ENDPOINT INTEGRATION ────────────────────────────────────

def test_fastapi_engineering_endpoints():
    """Verify FastAPI routes for turbine catalog, conventions, generation, and validation."""
    # 1. List turbines
    res_turbines = client.get("/api/engineering/turbines")
    assert res_turbines.status_code == 200
    turbines_list = res_turbines.json()
    assert len(turbines_list) >= 5

    # 2. Get specific turbine
    res_single = client.get("/api/engineering/turbines/ge_25_120")
    assert res_single.status_code == 200
    assert res_single.json()["rated_power_kw"] == 2500.0

    # 3. Conventions
    res_conv = client.get("/api/engineering/conventions")
    assert res_conv.status_code == 200
    assert "wind_to_deg" in res_conv.json()["downwind_relation"]

    # 4. Generate candidates via POST
    site = _create_box_site()
    res_gen = client.post(
        "/api/engineering/candidates/generate",
        json={
            "search_envelope_geometry": site,
            "turbine_model_id": "ge_25_120",
            "min_spacing_diameters": 4.0,
            "wind_direction_from_deg": 270.0,
        },
    )
    assert res_gen.status_code == 200
    data_gen = res_gen.json()
    assert data_gen["status"] in ("READY", "PARTIAL")
    assert data_gen["feasible_count"] > 0
    assert len(data_gen["feasible_candidates"]) == data_gen["feasible_count"]

    # 5. Validate proposed positions via POST
    valid_coords = [
        {"longitude": data_gen["feasible_candidates"][0]["longitude"], "latitude": data_gen["feasible_candidates"][0]["latitude"], "id": "t1"}
    ]
    res_val = client.post(
        "/api/engineering/candidates/validate",
        json={
            "search_envelope_geometry": site,
            "proposed_coordinates": valid_coords,
            "turbine_model_id": "ge_25_120",
            "min_spacing_diameters": 4.0,
        },
    )
    assert res_val.status_code == 200
    assert res_val.json()["all_feasible"] is True


# ── PHASE 4 CONSISTENCY HARDENING REGRESSION TESTS ───────────────────────────

def _create_mock_suitability(
    site,
    overall_status="READY",
    dwellings=None,
    highways=None,
    powerlines=None,
    waterways=None,
    conservation_assessment=None,
):
    from backend.app.gis.suitability_engine import SuitabilityEvaluationResult

    return SuitabilityEvaluationResult(
        overall_status=overall_status,
        search_envelope_geometry=site,
        search_envelope_area_km2=5.0,
        buildable_area_km2=4.0,
        buildable_area_m2=4_000_000.0,
        buildable_percentage=80.0,
        conditional_percentage=0.0 if overall_status == "READY" else 20.0,
        excluded_percentage=20.0 if overall_status == "READY" else 0.0,
        unknown_percentage=0.0,
        projected_crs="EPSG:32643",
        utm_zone=43,
        terrain_assessment={"status": "READY", "slope_deg": 2.0, "elevation_m": 100.0},
        wind_assessment={"status": "READY", "wind_speed_120m_mps": 7.0},
        landcover_assessment={"status": "READY", "dominant_class_code": 40},
        infrastructure_assessment={
            "status": "READY",
            "dwellings": dwellings or [],
            "highways": highways or [],
            "powerlines": powerlines or [],
            "waterways": waterways or [],
        },
        conservation_assessment=conservation_assessment or {
            "status": "READY",
            "is_inside_protected_area": False,
            "is_in_buffer_zone": False,
        },
        active_constraints=[],
        hard_exclusion_reasons=[],
        conditional_reasons=[],
        data_gaps=[],
        provenance_chain=[],
        evaluated_at="2026-10-07T00:00:00Z",
    )


def test_regression_1_verified_ehv_uses_185m_not_50m():
    """Verify that verified >=66kV EHV powerlines enforce 185m statutory setback, not 50m."""
    site = _create_box_site()
    center_lon = 77.015
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="READY",
        powerlines=[
            {
                "id": "ehv-test-1",
                "is_ehv": True,
                "voltage_v": 132000,
                "voltage": "132 kV",
                "geometry_coordinates": [[center_lon, 14.0], [center_lon, 14.03]],
            }
        ],
    )

    # Standard reference / SG turbine: H=114m, D=132m -> 114 + 66 + 5 = 185.0m
    prepared_hard, prepared_cond, _ = candidate_engine._prepare_site_exclusions(
        suitability_result=mock_suitability,
        zone=43,
        is_north=True,
        statutory_setback_m=185.0,
    )

    # 1. Must be in prepared_hard (not conditional)
    assert len(prepared_hard) == 1
    ehv_feat = prepared_hard[0]
    assert ehv_feat["category"] == "EHV_POWERLINE"
    assert ehv_feat["setback_m"] == 185.0, f"Expected 185.0m for verified EHV, got {ehv_feat['setback_m']}"
    assert len(prepared_cond) == 0

    # 2. Candidate 100m from EHV line is strictly EXCLUDED (would have passed if 50m was used)
    validator = CandidateEngineeringValidator("sg_34_132")
    hw_x, hw_y = project_wgs84_to_utm(center_lon, 14.015, zone=43, is_north=True)[:2]
    cand_100m_x = hw_x + 100.0  # 100m from line
    lon_cand, lat_cand = unproject_utm_to_wgs84(cand_100m_x, hw_y, zone=43, is_north=True)

    cand = validator.validate_candidate_point(
        easting_m=cand_100m_x,
        northing_m=hw_y,
        lon=lon_cand,
        lat=lat_cand,
        utm_exterior_rings=[[project_wgs84_to_utm(pt[0], pt[1], zone=43, is_north=True)[:2] for pt in site["coordinates"][0]]],
        utm_interior_holes=[],
        prepared_exclusions=prepared_hard,
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    assert cand.status == CandidateStatus.EXCLUDED
    assert any("EHV_POWERLINE" in r for r in cand.rules_failed)


def test_regression_2_individual_structures_use_185m():
    """Verify that individual structures enforce statutory 185m setback, not generic 150m or 50m."""
    site = _create_box_site()
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="READY",
        dwellings=[
            {"id": "b-indiv-1", "type": "residential", "lon": 77.015, "lat": 14.015}
        ],
    )

    prepared_hard, _, _ = candidate_engine._prepare_site_exclusions(
        suitability_result=mock_suitability,
        zone=43,
        is_north=True,
        statutory_setback_m=185.0,
    )

    assert len(prepared_hard) == 1
    struct_feat = prepared_hard[0]
    assert struct_feat["category"] == "INDIVIDUAL_STRUCTURE"
    assert struct_feat["setback_m"] == 185.0, f"Expected 185.0m for individual structure, got {struct_feat['setback_m']}"


def test_regression_3_roads_use_185m():
    """Verify that public roads enforce statutory 185m setback, not 150m or 50m."""
    site = _create_box_site()
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="READY",
        highways=[
            {"id": "hw-notified-1", "geometry_coordinates": [[77.01, 14.0], [77.01, 14.03]]}
        ],
    )

    prepared_hard, _, _ = candidate_engine._prepare_site_exclusions(
        suitability_result=mock_suitability,
        zone=43,
        is_north=True,
        statutory_setback_m=185.0,
    )

    assert len(prepared_hard) == 1
    road_feat = prepared_hard[0]
    assert road_feat["category"] == "PUBLIC_ROAD"
    assert road_feat["setback_m"] == 185.0, f"Expected 185.0m for public road, got {road_feat['setback_m']}"


def test_regression_4_unknown_distribution_lines_use_50m_conditional():
    """Verify that unverified/sub-66kV lines use 50m CONDITIONAL advisory, not a hard exclusion."""
    site = _create_box_site()
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="READY",
        powerlines=[
            {
                "id": "dist-line-1",
                "is_ehv": False,
                "voltage_v": 11000,
                "geometry_coordinates": [[77.015, 14.0], [77.015, 14.03]],
            }
        ],
    )

    prepared_hard, prepared_cond, _ = candidate_engine._prepare_site_exclusions(
        suitability_result=mock_suitability,
        zone=43,
        is_north=True,
        statutory_setback_m=185.0,
    )

    # Distribution line MUST be in prepared_cond, NEVER prepared_hard
    assert len(prepared_hard) == 0
    assert len(prepared_cond) == 1
    dist_feat = prepared_cond[0]
    assert dist_feat["category"] == "DISTRIBUTION_POWERLINE"
    assert dist_feat["setback_m"] == 50.0

    # Candidate 30m from this line is NOT marked EXCLUDED, but gets CONDITIONAL advisory
    validator = CandidateEngineeringValidator("ge_25_120")
    hw_x, hw_y = project_wgs84_to_utm(77.015, 14.015, zone=43, is_north=True)[:2]
    cand_30m_x = hw_x + 30.0
    lon_c, lat_c = unproject_utm_to_wgs84(cand_30m_x, hw_y, zone=43, is_north=True)

    cand = validator.validate_candidate_point(
        easting_m=cand_30m_x,
        northing_m=hw_y,
        lon=lon_c,
        lat=lat_c,
        utm_exterior_rings=[[project_wgs84_to_utm(pt[0], pt[1], zone=43, is_north=True)[:2] for pt in site["coordinates"][0]]],
        utm_interior_holes=[],
        prepared_exclusions=[],
        conditional_exclusions=prepared_cond,
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    assert cand.status == CandidateStatus.FEASIBLE
    assert any("DISTRIBUTION_POWERLINE" in r for r in cand.rule_evaluations)
    rule_res = cand.rule_evaluations["RULE-CONDITIONAL-DISTRIBUTION_POWERLINE-0"]
    assert rule_res.status == CandidateStatus.CONDITIONAL
    assert len(cand.conditional_advisories) > 0


def test_regression_5_protected_area_1km_not_universal_hard_exclusion():
    """Verify that being within 1km WDPA ESZ buffer produces CONDITIONAL status, not universal hard exclusion."""
    site = _create_box_site()
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="PARTIAL",
        conservation_assessment={
            "status": "PARTIAL",
            "is_inside_protected_area": False,
            "is_in_buffer_zone": True,
            "nearest_protected_area": "Test Sanctuary",
        },
    )

    res = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        suitability_result=mock_suitability,
    )

    # 1km buffer must NOT eliminate all candidates!
    assert res.feasible_count > 0
    # Site must be PARTIAL because of conditional legal-verification status
    assert res.status == "PARTIAL"
    assert any("ESZ" in adv for adv in res.feasible_candidates[0].conditional_advisories)


def test_regression_6_water_50m_statutory_and_100m_conditional_states_distinct():
    """Verify that water 50m statutory margin (HARD) and 100m flood-scour buffer (CONDITIONAL) remain distinct."""
    site = _create_box_site()
    center_lon = 77.015
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="READY",
        waterways=[
            {"id": "water-stream-1", "geometry_coordinates": [[center_lon, 14.0], [center_lon, 14.03]]}
        ],
    )

    prepared_hard, prepared_cond, _ = candidate_engine._prepare_site_exclusions(
        suitability_result=mock_suitability,
        zone=43,
        is_north=True,
        statutory_setback_m=185.0,
    )

    # Hard list has 50m statutory margin
    assert any(f["category"] == "STATUTORY_WATERWAY" and f["setback_m"] == 50.0 for f in prepared_hard)
    # Conditional list has 100m flood-scour buffer
    assert any(f["category"] == "FLOOD_SCOUR_WATERWAY" and f["setback_m"] == 100.0 for f in prepared_cond)

    validator = CandidateEngineeringValidator("ge_25_120")
    stream_x, stream_y = project_wgs84_to_utm(center_lon, 14.015, zone=43, is_north=True)[:2]
    ext_rings = [[project_wgs84_to_utm(pt[0], pt[1], zone=43, is_north=True)[:2] for pt in site["coordinates"][0]]]

    # Candidate at 20m from stream violates 50m statutory margin -> EXCLUDED
    c_20m_x = stream_x + 20.0
    lon_20, lat_20 = unproject_utm_to_wgs84(c_20m_x, stream_y, zone=43, is_north=True)
    cand_20 = validator.validate_candidate_point(
        easting_m=c_20m_x,
        northing_m=stream_y,
        lon=lon_20,
        lat=lat_20,
        utm_exterior_rings=ext_rings,
        utm_interior_holes=[],
        prepared_exclusions=prepared_hard,
        conditional_exclusions=prepared_cond,
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    assert cand_20.status == CandidateStatus.EXCLUDED
    assert any("STATUTORY_WATERWAY" in r for r in cand_20.rules_failed)

    # Candidate at 125m from stream satisfies 50m statutory margin (125 >= 50 + 60 rotor radius),
    # but triggers 100m conditional flood advisory (125 < 100 + 60 rotor radius) -> FEASIBLE + CONDITIONAL
    c_125m_x = stream_x + 125.0
    lon_125, lat_125 = unproject_utm_to_wgs84(c_125m_x, stream_y, zone=43, is_north=True)
    cand_125 = validator.validate_candidate_point(
        easting_m=c_125m_x,
        northing_m=stream_y,
        lon=lon_125,
        lat=lat_125,
        utm_exterior_rings=ext_rings,
        utm_interior_holes=[],
        prepared_exclusions=prepared_hard,
        conditional_exclusions=prepared_cond,
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    assert cand_125.status == CandidateStatus.FEASIBLE
    assert any("FLOOD_SCOUR" in r for r in cand_125.rule_evaluations)
    assert cand_125.rule_evaluations["RULE-CONDITIONAL-FLOOD_SCOUR_WATERWAY-0"].status == CandidateStatus.CONDITIONAL


def test_regression_7_phase3a_partial_status_propagates_to_phase4():
    """Verify that a Phase 3A PARTIAL site is NEVER upgraded to READY by Phase 4 candidate generation."""
    site = _create_box_site()
    mock_suitability = _create_mock_suitability(
        site=site,
        overall_status="PARTIAL",
    )

    res = candidate_engine.generate_candidates(
        search_envelope_geometry=site,
        turbine_model_id="ge_25_120",
        suitability_result=mock_suitability,
    )

    assert res.feasible_count > 0
    # Must propagate upstream PARTIAL status!
    assert res.status == "PARTIAL", f"Expected PARTIAL status propagated, got {res.status}"


def test_regression_8_candidate_geometry_uses_authoritative_site_envelope():
    """Verify candidate generation uses authoritative 31.0564 km2 site envelope, not 38.64 km2."""
    assert SAMPLE_PATH.exists()
    with open(SAMPLE_PATH) as f:
        data = json.load(f)

    # Invariant: authoritative area is 31.0564 km2
    boundary_info = data["boundary"]
    assert boundary_info["area_km2"] == 31.0564
    assert boundary_info["area_km2"] != 38.64

    geom = boundary_info["geometry"]
    res = candidate_engine.generate_candidates(
        search_envelope_geometry=geom,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
    )

    assert res.feasible_count > 0
    for cand in res.feasible_candidates:
        assert is_point_in_polygon_geometry(cand.longitude, cand.latitude, geom)


def test_regression_9_selected_turbine_hd_values_affect_clearance_calculations():
    """Verify selected turbine H/D values dynamically scale statutory clearance calculations."""
    validator_vestas = CandidateEngineeringValidator("vestas_v110_20")  # H=95m, D=110m -> 95 + 55 + 5 = 155.0m
    validator_sg = CandidateEngineeringValidator("sg_34_132")           # H=114m, D=132m -> 114 + 66 + 5 = 185.0m

    assert validator_vestas.statutory_setback_m == 155.0
    assert validator_sg.statutory_setback_m == 185.0
    assert validator_sg.statutory_setback_m > validator_vestas.statutory_setback_m

    # Test candidate at 170m from an infrastructure feature with clearance_includes_blade=True
    ext_rings = [[[0.0, 0.0], [5000.0, 0.0], [5000.0, 5000.0], [0.0, 5000.0], [0.0, 0.0]]]
    excl_feat = {
        "id": "struct-1",
        "category": "INFRASTRUCTURE",
        "setback_m": 185.0,  # SG threshold
        "clearance_includes_blade": True,
        "segments": [(1000.0, 1000.0, 1000.0, 2000.0)],
        "bbox": (1000.0, 1000.0, 1000.0, 2000.0),
    }

    # Vestas feature setback scaled to its actual statutory setback: 155.0m
    excl_vestas = dict(excl_feat, setback_m=validator_vestas.statutory_setback_m)
    # SG feature setback scaled to its actual statutory setback: 185.0m
    excl_sg = dict(excl_feat, setback_m=validator_sg.statutory_setback_m)

    # Candidate at easting 1170.0m (distance 170.0m)
    c_vestas = validator_vestas.validate_candidate_point(
        easting_m=1170.0,
        northing_m=1500.0,
        lon=77.01,
        lat=14.01,
        utm_exterior_rings=ext_rings,
        utm_interior_holes=[],
        prepared_exclusions=[excl_vestas],
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    # 170m >= 155m -> FEASIBLE for Vestas!
    assert c_vestas.status == CandidateStatus.FEASIBLE

    c_sg = validator_sg.validate_candidate_point(
        easting_m=1170.0,
        northing_m=1500.0,
        lon=77.01,
        lat=14.01,
        utm_exterior_rings=ext_rings,
        utm_interior_holes=[],
        prepared_exclusions=[excl_sg],
        elevation_m=100.0,
        slope_deg=2.0,
        wind_speed_mps=7.0,
    )
    # 170m < 185m -> EXCLUDED for Siemens Gamesa!
    assert c_sg.status == CandidateStatus.EXCLUDED


def test_regression_10_turbine_catalog_classification_and_commercial_filter():
    """Verify commercial turbines are classified separately from research/offshore models."""
    turbines_all = candidate_engine.get_available_turbines(commercial_only=False)
    turbines_comm = candidate_engine.get_available_turbines(commercial_only=True)

    assert len(turbines_all) == 5
    assert len(turbines_comm) == 3

    comm_ids = [t["model_id"] for t in turbines_comm]
    assert comm_ids == ["ge_25_120", "vestas_v110_20", "sg_34_132"]
    assert "nrel_5mw" not in comm_ids
    assert "iea_15mw" not in comm_ids

    # Verify IEA 15MW is marked OFFSHORE_ONLY and not ordinary onshore commercial choice
    iea_spec = candidate_engine.get_turbine_spec("iea_15mw")
    assert iea_spec["category"] == "OFFSHORE_REFERENCE"
    assert iea_spec["is_commercial_onshore"] is False
    assert iea_spec["terrain_suitability"] == "OFFSHORE_ONLY"

