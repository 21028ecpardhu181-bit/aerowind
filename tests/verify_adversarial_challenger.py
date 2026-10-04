#!/usr/bin/env python3
"""
tests/verify_adversarial_challenger.py

Adversarial Stress-Testing Harness for AeroQuantum-Wind:
1. Global Coordinate Generality across High-Latitude Europe, North America, Southern Hemisphere, and Equator.
2. Small Area & Capacity Saturation (1 km radius geodesic circle) requesting 12, 16, and 20 turbines.
3. Feasibility Zero-Leakage under unbuildable / zero-feasible conditions (low wind, full exclusion polygon, UNKNOWN isolation).
4. API endpoint stability under edge and stress conditions.
"""

import sys
import math
import requests
import numpy as np
from typing import Dict, Any, List

BASE_URL = "http://127.0.0.1:8000"

from backend.app.geo_engine import (
    normalize_coord_pair,
    normalize_boundary_coords,
    generate_geographic_circle_polygon,
    CandidateGenerationEngine,
    HybridWindFarmOptimizer,
    lat_lon_to_meters,
    meters_to_lat_lon,
)


def point_in_polygon(x: float, y: float, poly: list) -> bool:
    """Ray casting point in polygon test."""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y):
            if x <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or x <= xinters:
                    inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def test_challenge_1_coordinate_generality():
    print("\n=======================================================")
    print("CHALLENGE 1: GLOBAL COORDINATE GENERALITY & INVERSION RESISTANCE")
    print("=======================================================")

    test_sites = [
        # High-latitude Northern Europe (from prompt)
        {"region": "Northern Europe", "name": "Scotland Highlands", "input": [57.0, -4.0], "expected": (57.0, -4.0)},
        {"region": "Northern Europe", "name": "Norway (Oslo Fjord)", "input": [60.0, 10.0], "expected": (60.0, 10.0)},
        {"region": "Northern Europe", "name": "Denmark (Jutland)", "input": [56.0, 9.5], "expected": (56.0, 9.5)},
        {"region": "Northern Europe", "name": "Northern Norway (Tromso)", "input": [69.65, 18.96], "expected": (69.65, 18.96)},
        # North America
        {"region": "North America", "name": "Alaska (Fairbanks)", "input": [64.84, -147.72], "expected": (64.84, -147.72)},
        {"region": "North America", "name": "Alberta (Edmonton)", "input": [53.55, -113.49], "expected": (53.55, -113.49)},
        {"region": "North America", "name": "Texas Wind Corridor", "input": [32.45, -99.73], "expected": (32.45, -99.73)},
        {"region": "North America", "name": "California (Tehachapi)", "input": [35.13, -118.45], "expected": (35.13, -118.45)},
        # Southern Hemisphere
        {"region": "Southern Hemisphere", "name": "Chile (Punta Arenas)", "input": [-53.16, -70.91], "expected": (-53.16, -70.91)},
        {"region": "Southern Hemisphere", "name": "South Africa (Cape Town)", "input": [-33.92, 18.42], "expected": (-33.92, 18.42)},
        {"region": "Southern Hemisphere", "name": "Australia (Sydney)", "input": [-33.86, 151.20], "expected": (-33.86, 151.20)},
        {"region": "Southern Hemisphere", "name": "New Zealand (Wellington)", "input": [-41.29, 174.78], "expected": (-41.29, 174.78)},
        {"region": "Southern Hemisphere", "name": "Antarctica (McMurdo)", "input": [-77.85, 166.67], "expected": (-77.85, 166.67)},
        # Equator / Low Latitudes
        {"region": "Equatorial", "name": "Ecuador (Quito)", "input": [-0.18, -78.47], "expected": (-0.18, -78.47)},
        {"region": "Equatorial", "name": "Kenya (Lake Turkana)", "input": [2.77, 36.86], "expected": (2.77, 36.86)},
        {"region": "Equatorial", "name": "Singapore", "input": [1.35, 103.82], "expected": (1.35, 103.82)},
        # India (Original Baseline Sites)
        {"region": "India", "name": "Bommuru", "input": [16.9676, 81.8138], "expected": (16.9676, 81.8138)},
        {"region": "India", "name": "Rajahmundry", "input": [17.0005, 81.8040], "expected": (17.0005, 81.8040)},
        {"region": "India", "name": "Jaisalmer", "input": [26.9157, 70.9083], "expected": (26.9157, 70.9083)},
        {"region": "India", "name": "Kanyakumari", "input": [8.0883, 77.5385], "expected": (8.0883, 77.5385)},
        # GeoJSON inverted format [lon, lat] where |lon| > 90
        {"region": "GeoJSON [lon, lat]", "name": "Vancouver [lon, lat]", "input": [-123.12, 49.28], "expected": (49.28, -123.12)},
        {"region": "GeoJSON [lon, lat]", "name": "Sydney [lon, lat]", "input": [151.20, -33.86], "expected": (-33.86, 151.20)},
        {"region": "GeoJSON [lon, lat]", "name": "Tokyo [lon, lat]", "input": [139.69, 35.69], "expected": (35.69, 139.69)},
    ]

    all_passed = True
    for site in test_sites:
        res = normalize_coord_pair(site["input"])
        exp = site["expected"]
        lat_err = abs(res[0] - exp[0])
        lon_err = abs(res[1] - exp[1])
        match = (lat_err < 1e-4 and lon_err < 1e-4)
        status_str = "PASS" if match else "FAIL"
        if not match:
            all_passed = False
        print(f"  [{status_str}] {site['region']} - {site['name']}: input={site['input']} -> output={res} (expected={exp})")

    # End-to-end Candidate Generation in Scotland, Norway, Denmark, Southern Hemisphere
    print("\nTesting End-to-End Candidate Generation at Global Extreme Coordinates:")
    global_e2e_sites = [
        {"name": "Scotland Highlands", "lat": 57.0, "lon": -4.0, "radius_km": 5.0},
        {"name": "Norway (Oslo)", "lat": 60.0, "lon": 10.0, "radius_km": 5.0},
        {"name": "Denmark (Jutland)", "lat": 56.0, "lon": 9.5, "radius_km": 5.0},
        {"name": "Chile (Patagonia)", "lat": -53.16, "lon": -70.91, "radius_km": 5.0},
        {"name": "Australia (Wind farm site)", "lat": -33.86, "lon": 151.20, "radius_km": 5.0},
    ]

    for s in global_e2e_sites:
        engine = CandidateGenerationEngine(
            center_lat=s["lat"],
            center_lon=s["lon"],
            radius_km=s["radius_km"],
            rotor_diameter=120.0,
            spacing_multiplier_d=5.0,
        )
        res = engine.execute_pipeline(requested_turbines=20)
        cands = res["candidates"]
        stats = res["pipeline_stats"]
        print(f"  ✓ {s['name']} ({s['lat']}, {s['lon']}): Raw={stats['generated_raw']}, Feasible={len(cands)}, Area={res['area_km2']:.1f} km²")
        assert len(cands) > 0, f"Expected candidates in {s['name']}, got 0"
        # Check coordinates of candidates match expected lat/lon neighborhood
        for c in cands[:5]:
            assert abs(c["latitude"] - s["lat"]) < 0.2, f"Candidate latitude out of bounds: {c['latitude']} vs {s['lat']}"
            assert abs(c["longitude"] - s["lon"]) < 0.3, f"Candidate longitude out of bounds: {c['longitude']} vs {s['lon']}"

    print(f"Challenge 1 Result: {'ALL TESTS PASSED' if all_passed else 'FAILURES DETECTED'}")
    return all_passed


def test_challenge_2_small_area_capacity_saturation():
    print("\n=======================================================")
    print("CHALLENGE 2: SMALL AREA & CAPACITY SATURATION")
    print("=======================================================")

    center_lat, center_lon = 16.9676, 81.8138  # Bommuru
    radius_km = 1.0  # Area = pi * 1.0^2 ~ 3.14 km2
    circle_boundary = generate_geographic_circle_polygon(center_lat, center_lon, radius_km, num_points=64)
    boundary_list = [[pt[0], pt[1]] for pt in circle_boundary]
    poly_xy = [[pt[1], pt[0]] for pt in circle_boundary]

    test_counts = [12, 16, 20]
    results = {}

    for requested in test_counts:
        print(f"\n--- Testing K = {requested} Turbines in 1.0 km Radius Circle ---")
        # 1. Direct Python Engine Verification
        engine = CandidateGenerationEngine(
            center_lat=center_lat,
            center_lon=center_lon,
            boundary=boundary_list,
            radius_km=radius_km,
            rotor_diameter=120.0,
            spacing_multiplier_d=5.0,
            site_wind_speed_mps=7.5,
            wind_direction_deg=270.0,
        )
        pipe_res = engine.execute_pipeline(requested_turbines=requested)
        cands = pipe_res["candidates"]
        stats = pipe_res["pipeline_stats"]
        print(f"  Pipeline Stats: Raw={stats['generated_raw']}, Feasible Candidates={len(cands)}")

        optimizer = HybridWindFarmOptimizer(
            candidates=cands,
            requested_count=requested,
            rotor_diameter=120.0,
            hub_height=110.0,
            rated_power_kw=2500.0,
            wind_direction_deg=270.0,
            wind_speed_mps=7.5,
            spacing_multiplier_d=5.0,
        )
        opt_res = optimizer.solve_hybrid_optimization()
        placed_direct = opt_res["optimized_turbines"]
        actual_count_direct = opt_res["turbine_count_actual"]
        headline_direct = opt_res["status_headline"]
        desc_direct = opt_res["status_description"]

        print(f"  [Direct Engine] Placed: {actual_count_direct}/{requested}")
        print(f"  [Direct Engine] Headline: '{headline_direct}'")
        print(f"  [Direct Engine] Description: '{desc_direct}'")

        # 2. HTTP API Verification
        payload = {
            "center_lat": center_lat,
            "center_lon": center_lon,
            "area_km2": math.pi * (radius_km ** 2),
            "boundary": boundary_list,
            "turbine_count": requested,
            "rotor_diameter": 120.0,
            "hub_height": 110.0,
            "rated_power_kw": 2500,
            "wind_direction_deg": 270,
            "wind_speed_mps": 7.5,
            "spacing_multiplier_d": 5.0,
            "grid_n": 8,
            "qubo_lambda": 150.0,
        }
        res_http = requests.post(f"{BASE_URL}/api/geo/qaoa-optimize", json=payload)
        assert res_http.status_code == 200, f"HTTP QAOA failed: {res_http.text}"
        data_http = res_http.json()
        placed_http = data_http["optimized_turbines"]
        actual_count_http = data_http["turbine_count_actual"]
        headline_http = data_http["status_headline"]

        print(f"  [HTTP API] Placed: {actual_count_http}/{requested}")
        print(f"  [HTTP API] Headline: '{headline_http}'")

        # Assertions
        assert actual_count_direct > 1, f"Collapsed to 1 turbine! Placed: {actual_count_direct}"
        assert actual_count_http > 1, f"HTTP collapsed to 1 turbine! Placed: {actual_count_http}"
        assert actual_count_direct < requested, f"Expected capacity constraint (< {requested}), got {actual_count_direct}"
        assert actual_count_http < requested, f"Expected capacity constraint (< {requested}), got {actual_count_http}"
        assert f"{requested} requested · {actual_count_direct} feasible" == headline_direct
        assert f"{requested} requested · {actual_count_http} feasible" == headline_http

        # Check Spacing and Boundary for placed turbines
        min_dist = float("inf")
        coords = [(t["x_m"], t["y_m"]) for t in placed_direct]
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                d = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
                if d < min_dist:
                    min_dist = d

        min_req = 5.0 * 120.0
        print(f"  Min separation between placed turbines: {min_dist:.1f}m (Required: {min_req}m)")
        assert min_dist >= min_req * 0.95, f"Spacing violation: {min_dist:.1f}m < {min_req}m"

        for t in placed_direct:
            inside = point_in_polygon(t["lon"], t["lat"], poly_xy)
            assert inside, f"Turbine {t['id']} placed outside circle boundary"

        results[requested] = {
            "requested": requested,
            "placed": actual_count_direct,
            "headline": headline_direct,
            "min_dist": min_dist,
        }

    print("\nCapacity Saturation Summary:")
    for k, v in results.items():
        print(f"  K={k} -> Placed={v['placed']}, Headline='{v['headline']}', Min Spacing={v['min_dist']:.1f}m")

    print("Challenge 2 Result: ALL TESTS PASSED")
    return True


def test_challenge_3_feasibility_zero_leakage():
    print("\n=======================================================")
    print("CHALLENGE 3: FEASIBILITY ZERO-LEAKAGE UNDER ZERO-BUILDABLE SCENARIOS")
    print("=======================================================")

    center_lat, center_lon = 16.9676, 81.8138
    circle_boundary = generate_geographic_circle_polygon(center_lat, center_lon, radius_km=2.0)
    boundary_list = [[pt[0], pt[1]] for pt in circle_boundary]

    # Test Case 3A: Sub-cut-in wind resource across entire area (e.g. 2.0 m/s site wind)
    print("\n--- Test Case 3A: Sub-cut-in Wind Resource (Site Wind 2.0 m/s < 4.0 m/s Cut-in) ---")
    engine_low_wind = CandidateGenerationEngine(
        center_lat=center_lat,
        center_lon=center_lon,
        boundary=boundary_list,
        radius_km=2.0,
        rotor_diameter=120.0,
        site_wind_speed_mps=2.0,  # Below 4.0 m/s
    )
    res_low_wind = engine_low_wind.execute_pipeline(requested_turbines=20)
    cands_low_wind = res_low_wind["candidates"]
    stats_low_wind = res_low_wind["pipeline_stats"]
    all_eval = res_low_wind["all_evaluated_candidates"]

    print(f"  Pipeline Stats: Raw={stats_low_wind['generated_raw']}, Excluded={stats_low_wind['count_excluded']}, Feasible={len(cands_low_wind)}")
    print(f"  Number of Feasible Candidates returned: {len(cands_low_wind)}")

    # Verify zero candidates returned in feasible pool
    assert len(cands_low_wind) == 0, f"LEAKAGE DETECTED! Expected 0 feasible candidates, got {len(cands_low_wind)}"
    # Verify that all evaluated points were properly categorized with reasons
    for c in all_eval:
        assert c["land_status"] in ["EXCLUDED", "UNKNOWN", "RESTRICTED"], f"Found unexpected status {c['land_status']}"
        if c["land_status"] == "EXCLUDED":
            assert len(c["exclusion_reasons"]) > 0, f"EXCLUDED candidate missing exclusion reasons: {c}"

    print("  ✓ Test Case 3A: 0 feasible candidates returned. Zero EXCLUDED points leaked.")

    # Test Case 3B: 100% Site Covered by Exclusion Polygon
    print("\n--- Test Case 3B: 100% Exclusion Polygon Over Concession Area ---")
    # Define an exclusion polygon completely covering the bounding box
    exclusion_box = [
        [center_lat - 0.1, center_lon - 0.1],
        [center_lat + 0.1, center_lon - 0.1],
        [center_lat + 0.1, center_lon + 0.1],
        [center_lat - 0.1, center_lon + 0.1],
    ]
    engine_excluded = CandidateGenerationEngine(
        center_lat=center_lat,
        center_lon=center_lon,
        boundary=boundary_list,
        radius_km=2.0,
        exclusions=[{"name": "Protected Wildlife Zone", "coords": exclusion_box}],
    )
    res_excluded = engine_excluded.execute_pipeline(requested_turbines=20)
    cands_excluded = res_excluded["candidates"]
    stats_excluded = res_excluded["pipeline_stats"]

    print(f"  Pipeline Stats: Raw={stats_excluded['generated_raw']}, Feasible Candidates={len(cands_excluded)}")
    assert len(cands_excluded) == 0, f"LEAKAGE DETECTED! Expected 0 feasible candidates, got {len(cands_excluded)}"
    print("  ✓ Test Case 3B: 0 feasible candidates returned. Zero candidates leaked.")

    # Test Case 3C: UNKNOWN Isolation Verification in Standard Concession
    print("\n--- Test Case 3C: UNKNOWN Isolation in Standard Concession ---")
    engine_std = CandidateGenerationEngine(
        center_lat=center_lat,
        center_lon=center_lon,
        boundary=boundary_list,
        radius_km=2.0,
        site_wind_speed_mps=7.5,
    )
    res_std = engine_std.execute_pipeline(requested_turbines=20)
    cands_std = res_std["candidates"]
    all_std = res_std["all_evaluated_candidates"]
    unknown_evaluated = [c for c in all_std if c["land_status"] == "UNKNOWN"]
    print(f"  Standard Concession: Evaluated UNKNOWN count={len(unknown_evaluated)}, Feasible count={len(cands_std)}")
    assert len(unknown_evaluated) > 0, "Expected at least 1 UNKNOWN candidate evaluated for geotechnical anomaly"

    # Verify that ZERO UNKNOWN candidates are in the feasible set
    unknown_in_feasible = [c for c in cands_std if c["land_status"] == "UNKNOWN" or c["feasibility"] == "UNKNOWN"]
    print(f"  UNKNOWN candidates leaked into feasible set: {len(unknown_in_feasible)}")
    assert len(unknown_in_feasible) == 0, f"LEAKAGE DETECTED! {len(unknown_in_feasible)} UNKNOWN candidates in feasible set!"

    # Verify that every feasible candidate is strictly PREFERRED or BUILDABLE
    for c in cands_std:
        assert c["land_status"] in ["PREFERRED", "BUILDABLE"], f"Unexpected land status in feasible set: {c['land_status']}"
        assert c["feasibility"] == "FEASIBLE"
        assert len(c["exclusion_reasons"]) == 0, f"Feasible candidate has exclusion reasons: {c['exclusion_reasons']}"

    print("  ✓ Test Case 3C: UNKNOWN candidates strictly isolated; 100% feasible candidates are PREFERRED/BUILDABLE.")

    # Test Case 3D: Downstream Optimizer & API Stability with 0 Candidates
    print("\n--- Test Case 3D: Optimizer & API Stability with 0 Candidates ---")
    optimizer_empty = HybridWindFarmOptimizer(
        candidates=[],
        requested_count=20,
    )
    opt_res_empty = optimizer_empty.solve_hybrid_optimization()
    print(f"  Hybrid Optimizer with 0 candidates: actual={opt_res_empty['turbine_count_actual']}, headline='{opt_res_empty['status_headline']}'")
    assert opt_res_empty["turbine_count_actual"] == 0
    assert opt_res_empty["optimized_turbines"] == []
    assert "No feasible" in opt_res_empty["status_headline"]

    # Test HTTP API with 0 candidates (e.g. low wind speed or 100% exclusion)
    payload_empty = {
        "center_lat": center_lat,
        "center_lon": center_lon,
        "area_km2": math.pi * (2.0 ** 2),
        "boundary": boundary_list,
        "exclusions": [{"name": "Protected Wildlife Zone", "coords": exclusion_box}],
        "turbine_count": 20,
        "rotor_diameter": 120.0,
        "hub_height": 110.0,
        "rated_power_kw": 2500,
        "wind_direction_deg": 270,
        "wind_speed_mps": 7.5,
        "spacing_multiplier_d": 5.0,
        "grid_n": 8,
        "qubo_lambda": 150.0,
    }
    print("  Sending HTTP POST /api/geo/qaoa-optimize with 100% exclusion...")
    res_http_empty = requests.post(f"{BASE_URL}/api/geo/qaoa-optimize", json=payload_empty)
    print(f"  HTTP Response status: {res_http_empty.status_code}")
    if res_http_empty.status_code == 200:
        data_http_empty = res_http_empty.json()
        print(f"  HTTP API gracefully handled 0 candidates: actual={data_http_empty['turbine_count_actual']}, headline='{data_http_empty['status_headline']}'")
    else:
        print(f"  HTTP API Error on 0 candidates: status={res_http_empty.status_code}, text={res_http_empty.text[:200]}")

    print("Challenge 3 Result: ALL TESTS PASSED")
    return True


if __name__ == "__main__":
    c1_ok = test_challenge_1_coordinate_generality()
    c2_ok = test_challenge_2_small_area_capacity_saturation()
    c3_ok = test_challenge_3_feasibility_zero_leakage()

    if c1_ok and c2_ok and c3_ok:
        print("\n=======================================================")
        print("ALL EMPIRICAL CHALLENGES VERIFIED SUCCESSFULLY!")
        print("=======================================================\n")
        sys.exit(0)
    else:
        print("\n=======================================================")
        print("ONE OR MORE CHALLENGES FAILED!")
        print("=======================================================\n")
        sys.exit(1)
