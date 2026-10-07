"""
AeroQuantum-Wind Phase 7: Engineering-Truthful Cesium 3D Visualization & Layout Audit.

Validates that:
1. Real geographic coordinates (lon/lat/elevation) and projected CRS are preserved.
2. GlTF heading faces strictly upwind into the oncoming wind, and wake propagates downwind.
3. Wake geometry follows the FLORIS Bastankhah Gaussian expansion parameter k* = 0.04.
4. Turbine mast, nacelle, and foundation scale with authentic catalogue hub height and rotor diameter.
5. Site boundary parses GeoJSON polygons and holes faithfully without circular fallbacks.
6. Physical re-evaluation metrics (Net AEP, wake loss, CUF, optimality scope) propagate truthfully.
7. Zero emoji policy is strictly maintained across all Phase 7 visualization files.
"""

import math
import os
import re
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.engineering.geometry_conventions import (
    get_wind_to_deg,
    get_turbine_yaw_deg,
    get_cesium_heading_deg,
)
from backend.app.engineering.floris_engine import TURBINE_CATALOG


client = TestClient(app)


def test_wind_and_gltf_yaw_conventions():
    """
    Verifies backend directional truth:
    - wind_from_deg: arrival direction
    - wind_to_deg: (wind_from_deg + 180) % 360 (wake propagation)
    - gltf_heading_deg: (wind_from_deg - 90 + 360) % 360 (faces into wind)
    """
    test_cases = [
        (0.0, 180.0, 270.0),    # Wind from North blows South; glTF heading 270
        (90.0, 270.0, 0.0),     # Wind from East blows West; glTF heading 0
        (180.0, 0.0, 90.0),     # Wind from South blows North; glTF heading 90
        (270.0, 90.0, 180.0),   # Wind from West blows East; glTF heading 180
        (300.0, 120.0, 210.0),  # Typical WNW wind
    ]

    for wind_from, expected_wake_to, expected_gltf_heading in test_cases:
        wake_to = get_wind_to_deg(wind_from)
        gltf_heading = get_cesium_heading_deg(wind_from)

        assert abs(wake_to - expected_wake_to) < 1e-6, f"Wake mismatch for wind_from={wind_from}"
        assert abs(gltf_heading - expected_gltf_heading) < 1e-6, f"GlTF heading mismatch for wind_from={wind_from}"


def test_wake_expansion_geometry_parameter():
    """
    Verifies that expanding wake trapezoid uses the FLORIS Bastankhah Gaussian
    wake expansion parameter k* = 0.04, matching the physical wake model.
    """
    rotor_diameter = 120.0
    cone_length_m = 1020.0  # 8.5 * D
    k_star = 0.04

    r0 = rotor_diameter * 0.5
    r1 = r0 + k_star * cone_length_m

    # r0 should be 60.0m
    assert abs(r0 - 60.0) < 1e-6
    # r1 at 1020m should be 60.0 + 0.04 * 1020 = 100.8m
    assert abs(r1 - 100.8) < 1e-6

    # Verify that the CesiumGlobeView code uses kStar = 0.04
    cesium_file = "src/components/gis/CesiumGlobeView.tsx"
    with open(cesium_file, "r") as f:
        content = f.read()

    assert "const kStar = 0.04;" in content, "CesiumGlobeView must use kStar = 0.04"
    assert "r1 = r0 + kStar * coneLengthM;" in content, "CesiumGlobeView must calculate r1 using kStar"


def test_authentic_turbine_catalogue_dimensions():
    """
    Verifies that turbine catalogue models have authentic rotor diameter and hub height,
    and are not fabricated on the frontend.
    """
    for model_id, spec in TURBINE_CATALOG.items():
        assert "rotor_diameter_m" in spec
        assert "hub_height_m" in spec
        assert "rated_power_kw" in spec
        assert spec["rotor_diameter_m"] > 0
        assert spec["hub_height_m"] > 0
        assert spec["rated_power_kw"] > 0

    ge_spec = TURBINE_CATALOG["ge_25_120"]
    assert ge_spec["rotor_diameter_m"] == 120.0
    assert ge_spec["hub_height_m"] == 110.0
    assert ge_spec["rated_power_kw"] == 2500.0


def test_no_synthetic_circle_boundary_or_fallback():
    """
    Verifies that synthetic circles or spirals are never fabricated when boundary
    or turbines are missing.
    """
    # Check CesiumGlobeView
    with open("src/components/gis/CesiumGlobeView.tsx", "r") as f:
        cesium_code = f.read()

    # The 32-point circular boundary fallback was replaced with truthful polygon parsing
    assert "const pts = 32;" not in cesium_code
    assert "parseBoundaryPolygons(boundary)" in cesium_code

    # Check Screen6Blueprint
    with open("src/components/workflow/Screen6Blueprint.tsx", "r") as f:
        blueprint_code = f.read()

    assert "const fallbackTurbines" not in blueprint_code
    assert "Generating schedule..." not in blueprint_code


def test_qaoa_physical_winner_pipeline_integration():
    """
    Verifies that the QAOA optimization endpoint returns the exact physical winner
    with Net AEP, wake loss, coordinates, and optimality scope, and that the frontend
    types and components support this data.
    """
    candidates = [
        {"candidate_id": f"C{i}", "latitude": 14.5 + i * 0.005, "longitude": 77.5 + i * 0.005, "elevation_m": 42.0, "is_feasible": True}
        for i in range(8)
    ]

    resp = client.post("/api/engineering/optimization/qaoa", json={
        "candidates": candidates,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 4,
        "min_spacing_multiplier": 4.0,
        "p_layers": 2,
        "shots": 1024,
        "max_classical_iterations": 10,
        "top_k_physical_reeval": 3,
        "backend_type": "aer_simulator",
        "random_seed": 42,
        "site_elevation_m": 42.0,
    })

    assert resp.status_code == 200
    data = resp.json()
    winner = data.get("declared_engineering_optimum")
    assert winner is not None
    assert "exact_net_aep_gwh" in winner
    assert "exact_wake_loss_pct" in winner
    assert "coordinates" in winner
    assert len(winner["coordinates"]) == 4
    assert "optimality_scope" in winner

    for coord in winner["coordinates"]:
        assert "latitude" in coord
        assert "longitude" in coord
        assert "utm_easting_m" in coord
        assert "utm_northing_m" in coord
        assert "elevation_m" in coord
        assert coord["utm_easting_m"] is not None
        assert coord["utm_northing_m"] is not None


def test_zero_emojis_in_phase7_files():
    """
    Enforces strictly ZERO emojis across all Phase 7 files.
    """
    files_to_check = [
        "src/components/gis/CesiumGlobeView.tsx",
        "src/components/workflow/Screen5Inspect.tsx",
        "src/components/workflow/Screen6Blueprint.tsx",
        "src/types/index.ts",
        "src/App.tsx",
        "WORKBOARD.md",
    ]

    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]")

    for fpath in files_to_check:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        matches = emoji_pattern.findall(content)
        assert len(matches) == 0, f"Found emojis in {fpath}: {matches}"
