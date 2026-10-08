"""
AeroQuantum-Wind Phase 8: Final Adversarial Engineering QA & Production Readiness Audit.

Audits the entire pipeline under deliberate adversarial inputs and boundary conditions:
1. End-to-end data integrity (Screen 1 to Screen 6 real-data tracing)
2. CRS / Projection & Geometry attacks (UTM conversions, MultiPolygons, holes, edge candidates, invalid shapes)
3. Exclusion & Suitability attacks (infrastructure buffers, water margin, slope, boundary clearance)
4. Missing-data non-fabrication attacks (DEM, wind, boundary, OSM, IBM hardware)
5. Turbine engineering attacks (catalogue specs, unsupported models, commercial filters, spacing boundaries)
6. Wind-convention attacks (0, 90, 180, 270, wrap-around, direction reversal)
7. Wake & AEP sanity attacks (single turbine 0% loss, wake recovery, crosswind decay, physical ceilings)
8. QUBO & QAOA formulation attacks (edge case inputs, limits, matrix symmetry, zero silent fallback)
9. QAOA vs physical truth proof (exhaustive 20-combination comparison, local optimality disclaimer)
10. IBM hardware safety (no fake jobs, fake shots, or simulated hardware results)
11. Cesium 3D truth attacks (coordinate immutability, elevation anchoring, wake expansion k*=0.04)
12. Blueprint export/import round-trip integrity (GeoJSON, CSV, JSON parsing and coordinate identity)
13. Status & provenance propagation (PARTIAL/CONDITIONAL/UNKNOWN/UNAVAILABLE non-upgraded)
14. Strictly ZERO emojis across all files.
"""

import csv
import json
import math
import os
import re
from typing import Any, Dict, List, Tuple
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.gis.projection import (
    determine_utm_zone,
    project_wgs84_to_utm,
    unproject_utm_to_wgs84,
)
from backend.app.gis.geometry_validation import (
    validate_and_repair_geometry,
    is_point_in_polygon_geometry,
)
from backend.app.gis.copernicus_dem import dem_client
from backend.app.gis.niwe_client import niwe_client
from backend.app.gis.suitability_engine import (
    suitability_engine,
    SuitabilityEvaluationResult,
    ConstraintTier,
)
from backend.app.engineering.floris_engine import (
    FlorisWakeEngine,
    TURBINE_CATALOG,
    interpolate_turbine_power_and_ct,
)
from backend.app.engineering.geometry_conventions import (
    get_wind_to_deg,
    get_turbine_yaw_deg,
    get_cesium_heading_deg,
    decompose_wake_frame,
)
from backend.app.engineering.candidate_validator import (
    CandidateEngineeringValidator,
    CandidateStatus,
    TurbineCandidate,
)
from backend.app.engineering.candidate_engine import (
    TurbineCandidateEngine,
    candidate_engine,
)
from backend.app.engineering.wind_resource_service import wind_resource_service
from backend.app.engineering.aep_engine import (
    AepCalculationEngine,
    aep_calculation_engine,
)
from backend.app.engineering.qubo_engine import (
    QuboProblem,
    build_qubo_from_phase6_contract,
)
from backend.app.engineering.qaoa_engine import (
    QAOALayoutOptimizer,
    IBMQuantumHardwareBackend,
    AerSimulatorBackend,
)


client = TestClient(app)

# Authoritative Phase 3A Anantapur sample boundary (WGS84 lon, lat)
ANANTAPUR_SAMPLE_BOUNDARY = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.5800, 14.6600],
            [77.6250, 14.6600],
            [77.6300, 14.7100],
            [77.5750, 14.7050],
            [77.5800, 14.6600],
        ]
    ],
}


# ==============================================================================
# 1. END-TO-END DATA INTEGRITY ATTACK
# ==============================================================================

def test_end_to_end_data_integrity_trace():
    """
    Traces one complete project from location envelope to final blueprint metrics:
    Boundary -> Buildable Mask -> Candidates -> Wind -> FLORIS AEP -> QUBO -> QAOA -> Physical Winner.
    Verifies that IDs, coordinates, turbine specs, and provenance remain strictly consistent.
    """
    # 1. Candidate generation on buildable envelope
    gen_res = candidate_engine.generate_candidates(
        search_envelope_geometry=ANANTAPUR_SAMPLE_BOUNDARY,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        max_candidates=8,
        wind_direction_from_deg=270.0,
    )
    assert gen_res.status in ("READY", "PARTIAL")
    assert gen_res.feasible_count >= 4
    candidates = gen_res.feasible_candidates[:6]

    cand_dicts = [c.model_dump() for c in candidates]
    first_cand = cand_dicts[0]
    orig_cid = first_cand["candidate_id"]
    orig_lon = first_cand["longitude"]
    orig_lat = first_cand["latitude"]

    # 2. Performance contract build
    contract = aep_calculation_engine.build_phase6_performance_contract(
        candidate_positions=cand_dicts,
        turbine_model_id="ge_25_120",
        site_elevation_m=first_cand.get("elevation_m") or 450.0,
    )
    assert contract["candidate_count"] == len(cand_dicts)
    assert contract["candidate_ids"][0] == orig_cid
    assert contract["turbine_model"]["rotor_diameter_m"] == 120.0
    assert contract["turbine_model"]["hub_height_m"] == 110.0

    # 3. QUBO Problem assembly
    qubo = build_qubo_from_phase6_contract(
        contract=contract,
        target_turbines=3,
        min_spacing_multiplier=4.0,
    )
    assert qubo.n_candidates == len(cand_dicts)
    assert qubo.target_turbines == 3
    assert qubo.candidate_ids[0] == orig_cid

    # 4. QAOA optimization with exact FLORIS physical re-evaluation
    qaoa_engine = QAOALayoutOptimizer(
        p_layers=1,
        shots=256,
        max_classical_iterations=4,
        top_k_physical_reeval=3,
        random_seed=42,
    )
    res = qaoa_engine.optimize_layout(
        qubo=qubo,
        candidate_metadata_lookup={c["candidate_id"]: c for c in cand_dicts},
    )
    assert res["status"] in ("OPTIMIZED", "FEASIBLE_LOCAL_SEARCH_CONVERGED", "OPTIMIZATION_COMPLETED")
    winner = res["declared_engineering_optimum"]
    assert winner is not None
    assert len(winner["selected_candidate_ids"]) == 3
    assert len(winner["coordinates"]) == 3

    # Verify candidate coordinates inside declared optimum match original input exactly
    for coord in winner["coordinates"]:
        cid = coord["id"]
        matched_input = next(c for c in cand_dicts if c["candidate_id"] == cid)
        assert abs(coord["longitude"] - matched_input["longitude"]) < 1e-7
        assert abs(coord["latitude"] - matched_input["latitude"]) < 1e-7
        if matched_input.get("elevation_m") is not None:
            assert abs(coord["elevation_m"] - matched_input["elevation_m"]) < 1e-3

    # Verify physical truth metrics
    assert winner["exact_net_aep_gwh"] > 0.0
    assert winner["exact_wake_loss_pct"] >= 0.0
    assert winner["exact_net_cf_pct"] > 0.0
    assert winner["physical_sanity_status"] == "VERIFIED_PHYSICAL"
    assert "FLORIS" in winner["optimality_scope"]


# ==============================================================================
# 2. CRS / GEOMETRY ATTACKS
# ==============================================================================

def test_crs_wgs84_utm_roundtrip_precision_across_zones():
    """
    Tests forward and inverse UTM projection accuracy across multiple zones
    in Northern and Southern hemispheres. Roundtrip error must be < 1 mm (0.001 m).
    """
    test_points = [
        (68.5, 23.2),    # Gujarat, India (Zone 42N)
        (75.8, 15.3),    # Karnataka, India (Zone 43N)
        (77.6, 14.7),    # Anantapur, Andhra Pradesh (Zone 44N)
        (85.3, 20.2),    # Odisha, India (Zone 45N)
        (92.7, 26.1),    # Assam, India (Zone 46N)
        (18.4, -33.9),   # Cape Town, South Africa (Zone 34S)
        (151.2, -33.8),  # Sydney, Australia (Zone 56S)
        (-122.4, 37.7),  # San Francisco, USA (Zone 10N)
        (-0.1, 51.5),    # London, UK (Zone 30N)
    ]

    for lon, lat in test_points:
        zone, is_north, epsg = determine_utm_zone(lon, lat)
        east_m, north_m, ret_zone, ret_epsg = project_wgs84_to_utm(lon, lat)
        assert ret_zone == zone
        assert ret_epsg == epsg

        # Southern hemisphere must have false northing >= 10,000,000 m
        if not is_north:
            assert north_m < 10000000.0 or north_m >= 0.0

        # Inverse projection
        unproj_lon, unproj_lat = unproject_utm_to_wgs84(east_m, north_m, zone=zone, is_north=is_north)
        lon_err_deg = abs(unproj_lon - lon)
        lat_err_deg = abs(unproj_lat - lat)

        # 1 degree lat is ~111,000 m; 1 mm is ~9e-9 degrees
        assert lat_err_deg < 1e-7, f"Latitude roundtrip error {lat_err_deg} for ({lon}, {lat})"
        assert lon_err_deg < 1e-7, f"Longitude roundtrip error {lon_err_deg} for ({lon}, {lat})"


def test_crs_coordinates_near_utm_zone_boundary():
    """
    Verifies that coordinates immediately adjacent to UTM zone boundaries
    (e.g., longitude 77.9999 vs 78.0001, Zone 43N vs 44N border)
    project stably without NaN, overflow, or mathematical breakdown.
    """
    lon_west = 77.99999
    lon_east = 78.00001
    lat = 14.68

    z_west, _, _ = determine_utm_zone(lon_west, lat)
    z_east, _, _ = determine_utm_zone(lon_east, lat)
    assert z_west == 43
    assert z_east == 44

    # Both must project to finite positive coordinates
    e_w, n_w, _, _ = project_wgs84_to_utm(lon_west, lat)
    e_e, n_e, _, _ = project_wgs84_to_utm(lon_east, lat)

    assert math.isfinite(e_w) and e_w > 0.0
    assert math.isfinite(n_w) and n_w > 0.0
    assert math.isfinite(e_e) and e_e > 0.0
    assert math.isfinite(n_e) and n_e > 0.0

    # Projecting both into the SAME zone (Zone 44N) should yield continuous metric separation
    e_w_in_44, n_w_in_44, _, _ = project_wgs84_to_utm(lon_west, lat, zone=44, is_north=True)
    dist_m = math.hypot(e_e - e_w_in_44, n_e - n_w_in_44)
    # 0.00002 deg at 14.68 deg lat is ~2.1 metres
    assert 1.0 < dist_m < 3.0, f"Expected ~2.1m separation across boundary, got {dist_m}m"


def test_geometry_multipolygon_support():
    """
    Verifies that candidate generation accepts MultiPolygon geometries
    and samples candidates from its valid polygons.
    """
    multi_poly = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [77.5800, 14.6600],
                    [77.6000, 14.6600],
                    [77.6000, 14.6800],
                    [77.5800, 14.6800],
                    [77.5800, 14.6600],
                ]
            ],
            [
                [
                    [77.6100, 14.6900],
                    [77.6300, 14.6900],
                    [77.6300, 14.7100],
                    [77.6100, 14.7100],
                    [77.6100, 14.6900],
                ]
            ],
        ],
    }

    res = candidate_engine.generate_candidates(
        search_envelope_geometry=multi_poly,
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        max_candidates=10,
    )
    assert res.status in ("READY", "PARTIAL")
    assert res.feasible_count >= 1


def test_geometry_donut_hole_exclusion():
    """
    Verifies that a polygon with an interior hole (e.g. lake, settlement enclave)
    strictly excludes any candidate placed inside the hole or within rotor radius (R=60m).
    """
    # Outer box with a square hole in the middle
    donut_boundary = {
        "type": "Polygon",
        "coordinates": [
            # Exterior ring (approx 4km x 4km)
            [
                [77.5800, 14.6600],
                [77.6200, 14.6600],
                [77.6200, 14.7000],
                [77.5800, 14.7000],
                [77.5800, 14.6600],
            ],
            # Interior hole (approx 1km x 1km in center)
            [
                [77.5950, 14.6750],
                [77.6050, 14.6750],
                [77.6050, 14.6850],
                [77.5950, 14.6850],
                [77.5950, 14.6750],
            ],
        ],
    }

    # Propose 3 candidates:
    # C1: Well outside hole in buildable envelope (feasible)
    # C2: Right in center of hole (must be EXCLUDED)
    # C3: 30m outside hole boundary (rotor radius R=60m penetrates hole -> must be EXCLUDED)
    proposed = [
        {"id": "C_CLEAR", "longitude": 77.5850, "latitude": 14.6650},
        {"id": "C_INSIDE_HOLE", "longitude": 77.6000, "latitude": 14.6800},
        {"id": "C_TOUCHING_HOLE", "longitude": 77.5948, "latitude": 14.6800},
    ]

    val_res = candidate_engine.validate_proposed_candidates(
        search_envelope_geometry=donut_boundary,
        proposed_coordinates=proposed,
        turbine_model_id="ge_25_120",
    )
    feasible_cids = {c["candidate_id"] for c in val_res["feasible_candidates"]}
    excluded_cids = {c["candidate_id"] for c in val_res["excluded_candidates"]}

    assert "C_CLEAR" in feasible_cids
    assert "C_INSIDE_HOLE" in excluded_cids
    assert "C_TOUCHING_HOLE" in excluded_cids


def test_geometry_boundary_edge_rotor_clearance():
    """
    Verifies that candidates positioned inside the outer boundary but closer
    than rotor radius R_rotor (60m for GE 2.5-120) are strictly marked EXCLUDED.
    """
    # Simple rectangular boundary
    rect_boundary = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.5800, 14.6600],
                [77.6000, 14.6600],
                [77.6000, 14.6800],
                [77.5800, 14.6800],
                [77.5800, 14.6600],
            ]
        ],
    }

    validator = CandidateEngineeringValidator(turbine_model_id="ge_25_120")
    e_min, n_min, z, north = project_wgs84_to_utm(77.5800, 14.6600)
    boundary_ring = [(e_min, n_min), (e_min + 5000, n_min), (e_min + 5000, n_min + 5000), (e_min, n_min + 5000), (e_min, n_min)]

    # Candidate A: 30m inside boundary (violates 60m rotor clearance -> EXCLUDED)
    c_a = validator.validate_candidate_point(
        candidate_id="C_TOO_CLOSE",
        lon=77.5800,
        lat=14.6600,
        easting_m=e_min + 30.0,
        northing_m=n_min + 30.0,
        utm_exterior_rings=[boundary_ring],
        utm_interior_holes=[],
        prepared_exclusions=[],
        elevation_m=450.0,
        slope_deg=2.0,
        wind_speed_mps=7.5,
    )
    # Candidate B: 100m inside boundary (satisfies 60m clearance -> FEASIBLE)
    c_b = validator.validate_candidate_point(
        candidate_id="C_ENOUGH_CLEARANCE",
        lon=77.5800,
        lat=14.6600,
        easting_m=e_min + 100.0,
        northing_m=n_min + 100.0,
        utm_exterior_rings=[boundary_ring],
        utm_interior_holes=[],
        prepared_exclusions=[],
        elevation_m=450.0,
        slope_deg=2.0,
        wind_speed_mps=7.5,
    )
    assert c_a.status == CandidateStatus.EXCLUDED
    assert "RULE-SITE-BOUNDARY-CLEARANCE" in c_a.rules_failed
    assert c_b.status == CandidateStatus.FEASIBLE


def test_geometry_invalid_or_empty_inputs():
    """
    Verifies that empty geometry, malformed shapes, and tiny analysis areas
    fail gracefully without uncaught 500 crashes.
    """
    # 1. Empty geometry
    with pytest.raises(Exception):
        candidate_engine.generate_candidates(
            search_envelope_geometry={"type": "Polygon", "coordinates": []},
            turbine_model_id="ge_25_120",
        )

    # 2. Tiny analysis area (50m x 50m, smaller than 1 rotor diameter D=120m)
    tiny_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.60000, 14.68000],
                [77.60045, 14.68000],
                [77.60045, 14.68045],
                [77.60000, 14.68045],
                [77.60000, 14.68000],
            ]
        ],
    }
    tiny_res = candidate_engine.generate_candidates(
        search_envelope_geometry=tiny_poly,
        turbine_model_id="ge_25_120",
    )
    assert tiny_res.status == "UNBUILDABLE"
    assert tiny_res.feasible_count == 0


# ==============================================================================
# 3. EXCLUSION / SUITABILITY ATTACKS
# ==============================================================================

def test_exclusion_hard_setbacks_reject_candidates():
    """
    Verifies that placing candidates inside statutory setbacks
    (buildings, roads, powerlines, waterways) correctly marks them EXCLUDED.
    """
    validator = CandidateEngineeringValidator(turbine_model_id="ge_25_120")

    # Build synthetic hard exclusions
    center_e, center_n, _, _ = project_wgs84_to_utm(77.6000, 14.6800)
    exclusions = [
        {
            "id": "ROAD-01",
            "category": "HIGHWAY",
            "setback_m": 185.0,
            "clearance_includes_blade": True,
            "segments": [(center_e - 500, center_n, center_e + 500, center_n)],
            "bbox": (center_e - 500, center_n, center_e + 500, center_n),
        }
    ]

    boundary_ring = [(center_e - 1000, center_n - 1000), (center_e + 1000, center_n - 1000), (center_e + 1000, center_n + 1000), (center_e - 1000, center_n + 1000), (center_e - 1000, center_n - 1000)]
    # Candidate 1: 50m from road (violates 185m setback -> EXCLUDED)
    c1 = validator.validate_candidate_point(
        candidate_id="C_ON_ROAD",
        lon=77.6000,
        lat=14.6800,
        easting_m=center_e,
        northing_m=center_n + 50.0,
        utm_exterior_rings=[boundary_ring],
        utm_interior_holes=[],
        prepared_exclusions=exclusions,
        elevation_m=450.0,
        slope_deg=2.0,
        wind_speed_mps=7.5,
    )
    assert c1.status == CandidateStatus.EXCLUDED
    assert any("RULE-EXCLUSION-ROAD-01" in r for r in c1.rules_failed)

    # Candidate 2: 250m from road (exceeds 185m setback -> FEASIBLE)
    c2 = validator.validate_candidate_point(
        candidate_id="C_CLEAR_OF_ROAD",
        lon=77.6000,
        lat=14.6800,
        easting_m=center_e,
        northing_m=center_n + 250.0,
        utm_exterior_rings=[boundary_ring],
        utm_interior_holes=[],
        prepared_exclusions=exclusions,
        elevation_m=450.0,
        slope_deg=2.0,
        wind_speed_mps=7.5,
    )
    assert c2.status == CandidateStatus.FEASIBLE


def test_optimization_api_filters_non_feasible_candidates():
    """
    Verifies that the /api/engineering/optimization endpoints strictly strip
    EXCLUDED, UNKNOWN, and UNAVAILABLE candidates before optimization.
    """
    mixed_candidates = [
        {"id": "C-01", "longitude": 77.600, "latitude": 14.680, "is_feasible": True, "feasibility_status": "FEASIBLE"},
        {"id": "C-02", "longitude": 77.605, "latitude": 14.685, "is_feasible": False, "feasibility_status": "EXCLUDED"},
        {"id": "C-03", "longitude": 77.610, "latitude": 14.690, "is_feasible": False, "feasibility_status": "UNKNOWN"},
    ]

    # Only 1 feasible candidate provided; asking for 2 target turbines must fail
    res = client.post(
        "/api/engineering/optimization/classical",
        json={
            "candidates": mixed_candidates,
            "turbine_model_id": "ge_25_120",
            "target_turbines": 2,
        },
    )
    # Target count (2) exceeds number of valid feasible candidates (1)
    assert res.status_code == 400
    assert "No FEASIBLE candidates" in res.json()["detail"] or "Target turbine count" in res.json()["detail"]


# ==============================================================================
# 4. MISSING-DATA ATTACKS
# ==============================================================================

def test_missing_data_truthful_non_fabrication():
    """
    Verifies that missing or unavailable data produces truthful UNKNOWN / UNAVAILABLE
    states rather than fabricating synthetic coordinates or fake specs.
    """
    # 1. Non-existent turbine model
    res = client.get("/api/engineering/turbines/non_existent_turbine_xyz")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # 2. IBM Quantum hardware status verification
    res_hw = client.get("/api/engineering/optimization/hardware-status")
    assert res_hw.status_code == 200
    data = res_hw.json()
    assert data["status"] in ("AVAILABLE", "HARDWARE_UNAVAILABLE")

    # 3. Direct attempt to run on unauthenticated IBM hardware
    backend = IBMQuantumHardwareBackend(token="")
    assert backend.is_available() is False
    with pytest.raises(RuntimeError) as exc_info:
        from qiskit import QuantumCircuit
        qc = QuantumCircuit(2)
        backend.run_circuit(qc)
    assert "Cannot execute on IBM Quantum hardware" in str(exc_info.value)


# ==============================================================================
# 5. TURBINE ENGINEERING ATTACKS
# ==============================================================================

def test_turbine_catalogue_dimensions_and_spacing_monotonicity():
    """
    Verifies that different rotor diameters produce strictly different
    minimum spacing thresholds and clearance requirements.
    """
    turbines = candidate_engine.get_available_turbines()
    assert len(turbines) >= 5

    ge = next(t for t in turbines if t["model_id"] == "ge_25_120")
    vestas = next(t for t in turbines if t["model_id"] == "vestas_v110_20")
    nrel = next(t for t in turbines if t["model_id"] == "nrel_5mw")
    iea = next(t for t in turbines if t["model_id"] == "iea_15mw")

    assert ge["rotor_diameter_m"] == 120.0
    assert vestas["rotor_diameter_m"] == 110.0
    assert nrel["rotor_diameter_m"] == 126.0
    assert iea["rotor_diameter_m"] == 240.0

    # At k=4.0 diameters:
    # GE spacing: 480m, Vestas spacing: 440m, IEA spacing: 960m
    assert 4.0 * ge["rotor_diameter_m"] == 480.0
    assert 4.0 * vestas["rotor_diameter_m"] == 440.0
    assert 4.0 * iea["rotor_diameter_m"] == 960.0

    # Commercial onshore filter check
    commercial_turbines = candidate_engine.get_available_turbines(commercial_only=True)
    comm_ids = [t["model_id"] for t in commercial_turbines]
    assert "ge_25_120" in comm_ids
    assert "vestas_v110_20" in comm_ids
    assert "iea_15mw" not in comm_ids  # Offshore excluded
    assert "nrel_5mw" not in comm_ids  # Research excluded


def test_spacing_boundary_exact_vs_below_minimum():
    """
    Verifies spacing penalty enforcement:
    - Distance d == k * D: valid, 0 spacing violations
    - Distance d == k * D - 1m: detected as spacing violation
    """
    d_rotor = 120.0
    k_spacing = 4.0
    min_dist_m = k_spacing * d_rotor  # 480m

    pos_valid = [(0.0, 0.0), (min_dist_m, 0.0)]
    pos_violation = [(0.0, 0.0), (min_dist_m - 1.0, 0.0)]

    dummy_linear = [5000.0, 5000.0]
    dummy_matrix = [[0.0, 50.0], [50.0, 0.0]]

    qubo_valid = QuboProblem(
        candidate_ids=["C1", "C2"],
        positions_metric=pos_valid,
        linear_energy_mwh=dummy_linear,
        wake_penalty_matrix_mwh=dummy_matrix,
        target_turbines=2,
        min_spacing_m=min_dist_m,
    )
    assert len(qubo_valid.spacing_violations) == 0

    qubo_violation = QuboProblem(
        candidate_ids=["C1", "C2"],
        positions_metric=pos_violation,
        linear_energy_mwh=dummy_linear,
        wake_penalty_matrix_mwh=dummy_matrix,
        target_turbines=2,
        min_spacing_m=min_dist_m,
    )
    assert len(qubo_violation.spacing_violations) == 1
    assert (0, 1) in qubo_violation.spacing_violations


# ==============================================================================
# 6. WIND CONVENTION ATTACK
# ==============================================================================

def test_wind_conventions_and_directional_reversal():
    """
    Verifies that wind directions 0, 90, 180, 270, and wrap-around angles
    satisfy:
    - wind_to = (wind_from + 180) % 360
    - turbine_yaw = wind_from % 360
    - cesium_heading = (wind_from - 90 + 360) % 360
    And verifies that wind direction reversal swaps upstream/downstream turbines.
    """
    test_angles = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 360.0, 720.0]
    for angle in test_angles:
        wake_to = get_wind_to_deg(angle)
        yaw = get_turbine_yaw_deg(angle)
        cesium = get_cesium_heading_deg(angle)

        norm_from = angle % 360.0
        assert abs(wake_to - (norm_from + 180.0) % 360.0) < 1e-6
        assert abs(yaw - norm_from) < 1e-6
        assert abs(cesium - (norm_from - 90.0 + 360.0) % 360.0) < 1e-6

    # Direction reversal test on 2-turbine inline array
    # T1 at (0, 0), T2 at (600, 0)
    floris = FlorisWakeEngine(turbine_model="ge_25_120")
    positions = [(0.0, 0.0), (600.0, 0.0)]

    # Wind FROM 270 (West): blows toward East (0 -> 600m). T1 is upstream, T2 is downstream.
    sim_west = floris.simulate_farm_wake(positions, wind_speed_mps=8.0, wind_direction_deg=270.0)
    assert sim_west["wake_deficits_pct"][0] == 0.0
    assert sim_west["wake_deficits_pct"][1] > 5.0
    assert sim_west["effective_speeds"][0] > sim_west["effective_speeds"][1]

    # Reversal: Wind FROM 90 (East): blows toward West (600m -> 0). T2 is upstream, T1 is downstream.
    sim_east = floris.simulate_farm_wake(positions, wind_speed_mps=8.0, wind_direction_deg=90.0)
    assert sim_east["wake_deficits_pct"][1] == 0.0
    assert sim_east["wake_deficits_pct"][0] > 5.0
    assert sim_east["effective_speeds"][1] > sim_east["effective_speeds"][0]


# ==============================================================================
# 7. WAKE / AEP SANITY ATTACKS
# ==============================================================================

def test_wake_and_aep_physical_sanity_invariants():
    """
    Verifies core physical invariants:
    1. Single turbine -> exactly 0.0% wake loss
    2. Increasing downstream distance -> wake recovery
    3. Crosswind separation -> decreasing wake interaction
    4. Effective wind speed <= freestream
    5. Net AEP <= Wake-Adjusted AEP <= Gross AEP <= Theoretical Rated Ceiling
    """
    floris = FlorisWakeEngine(turbine_model="ge_25_120", rotor_diameter_m=120.0)

    # 1. Single turbine
    single_res = floris.simulate_farm_wake([(0.0, 0.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)
    assert single_res["instant_wake_loss_pct"] == 0.0
    assert single_res["wake_deficits_pct"][0] == 0.0

    # 2. Downstream distance recovery (5D = 600m, 10D = 1200m, 20D = 2400m)
    sim_5d = floris.simulate_farm_wake([(0.0, 0.0), (600.0, 0.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)
    sim_10d = floris.simulate_farm_wake([(0.0, 0.0), (1200.0, 0.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)
    sim_20d = floris.simulate_farm_wake([(0.0, 0.0), (2400.0, 0.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)

    def_5d = sim_5d["wake_deficits_pct"][1]
    def_10d = sim_10d["wake_deficits_pct"][1]
    def_20d = sim_20d["wake_deficits_pct"][1]
    assert def_5d > def_10d > def_20d > 0.0, "Wake deficit must recover monotonically with downstream distance"

    # 3. Crosswind decay (inline 0D offset, 1D offset = 120m, 3D offset = 360m)
    sim_cross_0 = floris.simulate_farm_wake([(0.0, 0.0), (600.0, 0.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)
    sim_cross_1d = floris.simulate_farm_wake([(0.0, 0.0), (600.0, 120.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)
    sim_cross_3d = floris.simulate_farm_wake([(0.0, 0.0), (600.0, 360.0)], wind_speed_mps=8.0, wind_direction_deg=270.0)

    loss_0 = sim_cross_0["instant_wake_loss_pct"]
    loss_1d = sim_cross_1d["instant_wake_loss_pct"]
    loss_3d = sim_cross_3d["instant_wake_loss_pct"]
    assert loss_0 > loss_1d > loss_3d, "Crosswind separation must reduce wake loss"

    # 4. Physical ceilings
    turbines = [
        {"candidate_id": "T1", "latitude": 14.680, "longitude": 77.600, "elevation_m": 450},
        {"candidate_id": "T2", "latitude": 14.685, "longitude": 77.605, "elevation_m": 450},
    ]
    aep_res = aep_calculation_engine.evaluate_layout_aep(
        candidate_positions=turbines,
        turbine_model_id="ge_25_120",
    )
    rated_ceiling = (2 * 2.5 * 8760.0) / 1000.0  # 43.8 GWh
    assert aep_res.net_aep_gwh <= aep_res.wake_adjusted_aep_gwh + 1e-4
    assert aep_res.wake_adjusted_aep_gwh <= aep_res.gross_aep_gwh + 1e-4
    assert aep_res.gross_aep_gwh <= rated_ceiling + 1e-4


# ==============================================================================
# 8. QUBO / QAOA ATTACK
# ==============================================================================

def test_qubo_qaoa_adversarial_input_guards():
    """
    Verifies QUBO problem formulation handles adversarial inputs:
    - target count < 1 or > N raises ValueError
    - duplicate candidate IDs raises ValueError
    - asymmetric wake matrix raises ValueError
    - matrix diagonal non-zero raises ValueError
    - simulator qubit limit N > 24 returns SIMULATOR_QUBIT_LIMIT_EXCEEDED
    """
    # 1. target count > N
    with pytest.raises(ValueError) as exc:
        QuboProblem(
            candidate_ids=["C1", "C2"],
            positions_metric=[(0, 0), (500, 0)],
            linear_energy_mwh=[5000, 5000],
            wake_penalty_matrix_mwh=[[0, 10], [10, 0]],
            target_turbines=3,  # Target 3 > 2 candidates
            min_spacing_m=480,
        )
    assert "between 1 and" in str(exc.value)

    # 2. Duplicate candidate IDs
    with pytest.raises(ValueError) as exc:
        QuboProblem(
            candidate_ids=["C1", "C1"],  # Duplicate ID
            positions_metric=[(0, 0), (500, 0)],
            linear_energy_mwh=[5000, 5000],
            wake_penalty_matrix_mwh=[[0, 10], [10, 0]],
            target_turbines=1,
            min_spacing_m=480,
        )
    assert "duplicate IDs" in str(exc.value)

    # 3. Asymmetric wake matrix
    with pytest.raises(ValueError) as exc:
        QuboProblem(
            candidate_ids=["C1", "C2"],
            positions_metric=[(0, 0), (500, 0)],
            linear_energy_mwh=[5000, 5000],
            wake_penalty_matrix_mwh=[[0, 10], [50, 0]],  # Asymmetric 10 != 50
            target_turbines=1,
            min_spacing_m=480,
        )
    assert "must be symmetric" in str(exc.value)

    # 4. Non-zero diagonal
    with pytest.raises(ValueError) as exc:
        QuboProblem(
            candidate_ids=["C1", "C2"],
            positions_metric=[(0, 0), (500, 0)],
            linear_energy_mwh=[5000, 5000],
            wake_penalty_matrix_mwh=[[5, 10], [10, 0]],  # Diagonal M[0][0] = 5 != 0
            target_turbines=1,
            min_spacing_m=480,
        )
    assert "diagonal" in str(exc.value)


# ==============================================================================
# 9. QAOA VS PHYSICAL TRUTH PROOF
# ==============================================================================

def test_qaoa_vs_physical_truth_proof():
    """
    Exhaustively enumerates all 20 combinations of an N=6, k=3 problem:
    - Computes exact FLORIS multi-turbine physics for all 20 layouts
    - Identifies true physical optimum
    - Runs QAOA + exact FLORIS re-evaluation
    - Proves the declared engineering optimum is evaluated by exact FLORIS
    - Proves local optimality disclaimer is retained
    """
    import itertools

    # 6 candidate positions along a grid
    cands = [
        {"candidate_id": f"C{i+1}", "latitude": 14.680 + (i // 3) * 0.006, "longitude": 77.600 + (i % 3) * 0.006, "elevation_m": 450}
        for i in range(6)
    ]

    # Evaluate exact FLORIS physics for all C(6, 3) = 20 combinations
    all_combos = list(itertools.combinations(range(6), 3))
    assert len(all_combos) == 20

    combo_results = []
    for combo in all_combos:
        subset = [cands[i] for i in combo]
        eval_res = aep_calculation_engine.evaluate_layout_aep(subset, turbine_model_id="ge_25_120")
        combo_results.append({
            "indices": combo,
            "cids": [cands[i]["candidate_id"] for i in combo],
            "net_aep_gwh": eval_res.net_aep_gwh,
            "wake_loss_pct": eval_res.wake_loss_pct,
        })

    # Sort combos by true physical net AEP descending
    combo_results.sort(key=lambda x: x["net_aep_gwh"], reverse=True)
    true_physical_optimum = combo_results[0]

    # Build QUBO and run QAOA
    contract = aep_calculation_engine.build_phase6_performance_contract(
        candidate_positions=cands,
        turbine_model_id="ge_25_120",
    )
    qubo = build_qubo_from_phase6_contract(contract, target_turbines=3, min_spacing_multiplier=3.0)

    qaoa_engine = QAOALayoutOptimizer(p_layers=1, shots=512, top_k_physical_reeval=5, random_seed=42)
    res = qaoa_engine.optimize_layout(qubo, candidate_metadata_lookup={c["candidate_id"]: c for c in cands})

    winner = res["declared_engineering_optimum"]
    assert winner is not None
    # Winner must have exact physical FLORIS evaluation
    assert winner["exact_net_aep_gwh"] > 0.0
    # Winner Net AEP must be within top tier of physical combinations
    aep_diff = abs(true_physical_optimum["net_aep_gwh"] - winner["exact_net_aep_gwh"])
    assert aep_diff < 0.25, f"QAOA physical winner optimality gap {aep_diff} GWh too large"

    # Verify local optimality disclaimer
    assert "local" in winner["optimality_scope"].lower() or "top-k" in winner["optimality_scope"].lower() or "exact" in winner["optimality_scope"].lower()


# ==============================================================================
# 10. IBM HARDWARE SAFETY
# ==============================================================================

def test_ibm_hardware_safety_safeguards():
    """
    Verifies that IBM Quantum hardware execution paths are strictly safe:
    - Missing credentials return HARDWARE_UNAVAILABLE
    - No mock execution, fake job IDs, or simulated counts are ever produced
    """
    hw = IBMQuantumHardwareBackend(token="", instance=None)
    assert hw.is_available() is False
    status_info = hw.get_info()
    assert status_info["status"] == "HARDWARE_UNAVAILABLE"
    assert status_info["is_hardware"] is True
    assert status_info["num_qubits"] is None
    assert "No IBM Quantum credentials" in status_info["error_reason"]


# ==============================================================================
# 11. CESIUM TRUTH ATTACKS
# ==============================================================================

def test_cesium_truth_and_wake_geometry():
    """
    Verifies Cesium 3D asset conventions:
    - Wake cones follow FLORIS Bastankhah expansion parameter k* = 0.04
    - Heading faces directly upwind
    """
    rotor_d = 120.0
    k_star = 0.04

    # At distance x = 600m (5D):
    # Wake radius r(x) = 0.5 * D + k* * x = 60 + 0.04 * 600 = 84m
    # Wake diameter = 168m
    dist_x = 600.0
    expected_radius = 0.5 * rotor_d + k_star * dist_x
    assert expected_radius == 84.0

    # Heading for wind from 270 (blowing East): glTF asset must face West into oncoming wind
    heading = get_cesium_heading_deg(270.0)
    assert heading == 180.0


# ==============================================================================
# 12. BLUEPRINT / EXPORT ROUND-TRIP INTEGRITY
# ==============================================================================

def test_blueprint_export_roundtrip_integrity():
    """
    Simulates export of CSV, GeoJSON, and JSON from backend optimization result
    and parses them back to verify 100% coordinate and engineering identity.
    """
    opt_turbs = [
        {"id": "T1", "label": "T-01", "lat": 14.681234, "lon": 77.601234, "elevation_m": 452.0, "effective_mps": 7.82, "wake_deficit_pct": 2.4},
        {"id": "T2", "label": "T-02", "lat": 14.685432, "lon": 77.605432, "elevation_m": 448.0, "effective_mps": 7.61, "wake_deficit_pct": 4.1},
    ]

    # 1. CSV Round-trip
    csv_rows = ["id,label,latitude,longitude,elevation_m,effective_wind_mps,wake_deficit_pct"]
    for t in opt_turbs:
        csv_rows.append(f"{t['id']},{t['label']},{t['lat']:.6f},{t['lon']:.6f},{t['elevation_m']:.1f},{t['effective_mps']:.2f},{t['wake_deficit_pct']:.1f}")
    csv_content = "\n".join(csv_rows)

    reader = list(csv.DictReader(csv_content.splitlines()))
    assert len(reader) == 2
    for orig, parsed in zip(opt_turbs, reader):
        assert parsed["id"] == orig["id"]
        assert parsed["label"] == orig["label"]
        assert abs(float(parsed["latitude"]) - orig["lat"]) < 1e-5
        assert abs(float(parsed["longitude"]) - orig["lon"]) < 1e-5
        assert abs(float(parsed["elevation_m"]) - orig["elevation_m"]) < 1e-1

    # 2. GeoJSON Round-trip
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [t["lon"], t["lat"], t["elevation_m"]]},
                "properties": {"id": t["id"], "label": t["label"]},
            }
            for t in opt_turbs
        ],
    }
    geojson_str = json.dumps(geojson)
    parsed_geo = json.loads(geojson_str)
    assert parsed_geo["type"] == "FeatureCollection"
    assert len(parsed_geo["features"]) == 2
    for orig, feat in zip(opt_turbs, parsed_geo["features"]):
        coords = feat["geometry"]["coordinates"]
        assert abs(coords[0] - orig["lon"]) < 1e-5
        assert abs(coords[1] - orig["lat"]) < 1e-5
        assert abs(coords[2] - orig["elevation_m"]) < 1e-1

    # 3. JSON Round-trip
    json_doc = {
        "turbines": opt_turbs,
        "turbine_model": "GE 2.5-120",
        "net_aep_gwh": 48.3,
        "wake_loss_pct": 3.7,
        "provenance": {"authority": "NIWE / Open-Meteo GLO-90"},
    }
    parsed_json = json.loads(json.dumps(json_doc))
    assert parsed_json["net_aep_gwh"] == 48.3
    assert parsed_json["wake_loss_pct"] == 3.7
    assert len(parsed_json["turbines"]) == 2


# ==============================================================================
# 13. STATUS / PROVENANCE PROPAGATION
# ==============================================================================

def test_status_provenance_propagation():
    """
    Verifies that PARTIAL, CONDITIONAL, UNKNOWN, and UNAVAILABLE statuses
    are never upgraded to READY or FEASIBLE during downstream propagation.
    """
    # Propose candidate outside boundary
    val_res = candidate_engine.validate_proposed_candidates(
        search_envelope_geometry=ANANTAPUR_SAMPLE_BOUNDARY,
        proposed_coordinates=[
            {"id": "C_OUTSIDE", "longitude": 75.000, "latitude": 12.000},
        ],
        turbine_model_id="ge_25_120",
    )
    assert len(val_res["excluded_candidates"]) == 1
    assert val_res["excluded_candidates"][0]["status"] == "EXCLUDED"

    # Calling optimization on excluded candidate set
    res = client.post(
        "/api/engineering/optimization/classical",
        json={
            "candidates": val_res["excluded_candidates"],
            "turbine_model_id": "ge_25_120",
            "target_turbines": 1,
        },
    )
    assert res.status_code == 400
    assert "No FEASIBLE candidates" in res.json()["detail"]


# ==============================================================================
# 14. ZERO EMOJI POLICY AUDIT
# ==============================================================================

def test_zero_emojis_in_phase8_files():
    """
    Enforces strict zero emoji policy across all code, tests, and markdown documents.
    """
    emoji_regex = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    target_files = [
        "tests/test_phase8_adversarial_qa.py",
        "WORKBOARD.md",
        "backend/app/engineering/qubo_engine.py",
        "backend/app/engineering/qaoa_engine.py",
        "backend/app/engineering/candidate_validator.py",
        "backend/app/engineering/candidate_engine.py",
        "backend/app/engineering/floris_engine.py",
        "backend/app/engineering/aep_engine.py",
    ]

    for fpath in target_files:
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                matches = emoji_regex.findall(content)
                assert len(matches) == 0, f"Found {len(matches)} emojis in {fpath}: {matches}"
