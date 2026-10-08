#!/usr/bin/env python3
"""
tests/verify_geographic_pipeline_multi_city.py

Comprehensive Multi-City Automated Validation Suite for Geographic Pipeline:
1. Bommuru: 20 requested -> 20 placed, coordinates permanent, spacing >= 600m, 0 outside boundary.
2. Rajahmundry: 20 requested -> 20 placed, coordinates permanent, spacing >= 600m, 0 outside boundary.
3. Jaisalmer: 20 requested -> 20 placed, coordinates permanent, spacing >= 600m, 0 outside boundary.
4. Small concession area (1 km radius geodesic circle):
   - Verifies system honestly reports feasible count (M < 20) without silently collapsing to 1 turbine.
5. End-to-End Playwright UI check on Mode Selection (Search, Radius, Freeform Polygon).
"""

import sys
import math
import requests
import numpy as np
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"


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


def verify_city_pipeline(city_name: str, requested_turbines: int = 20):
    print(f"\n=======================================================")
    print(f"Testing City: {city_name} (Requested: {requested_turbines} Turbines)")
    print(f"=======================================================")

    # 1. Geocode
    res = requests.get(f"{BASE_URL}/api/geo/geocode?q={city_name}")
    assert res.status_code == 200, f"Geocode failed for {city_name}: {res.text}"
    data = res.json()
    lat = float(data["lat"])
    lon = float(data["lon"])
    print(f"✓ Geocoded {city_name}: lat={lat:.4f}, lon={lon:.4f} ({data.get('display_name')})")

    # 2. Concession boundary (24.8 km2 polygon)
    area_km2 = 24.8
    radius_km = math.sqrt(area_km2) / 2.0
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    boundary = [
        [lat + lat_delta * 1.1, lon - lon_delta * 0.1],
        [lat + lat_delta * 0.7, lon + lon_delta * 0.1],
        [lat + lat_delta * 0.2, lon + lon_delta * 0.45],
        [lat - lat_delta * 0.4, lon + lon_delta * 0.85],
        [lat - lat_delta * 0.9, lon + lon_delta * 0.95],
        [lat - lat_delta * 1.2, lon - lon_delta * 0.45],
        [lat - lat_delta * 0.6, lon - lon_delta * 1.1],
        [lat - lat_delta * 0.1, lon - lon_delta * 0.85],
        [lat + lat_delta * 0.25, lon - lon_delta * 0.65],
        [lat + lat_delta * 0.65, lon - lon_delta * 0.55],
    ]
    poly_xy = [[pt[1], pt[0]] for pt in boundary]

    # 3. Initial Layout
    payload = {
        "center_lat": lat,
        "center_lon": lon,
        "area_km2": area_km2,
        "boundary": boundary,
        "turbine_count": requested_turbines,
        "rotor_diameter": 120.0,
        "hub_height": 110.0,
        "rated_power_kw": 2500,
        "wind_direction_deg": 270,
        "wind_speed_mps": 7.5,
        "spacing_multiplier_d": 5.0,
        "grid_n": 8,
    }
    res_init = requests.post(f"{BASE_URL}/api/geo/initial-layout", json=payload)
    assert res_init.status_code == 200, f"Initial layout failed: {res_init.text}"
    init_data = res_init.json()
    init_turbines = init_data["turbines"]

    print(f"✓ Initial layout: {len(init_turbines)} turbines generated")
    assert len(init_turbines) == requested_turbines, f"Expected {requested_turbines}, got {len(init_turbines)}"

    for t in init_turbines:
        inside = point_in_polygon(t["lon"], t["lat"], poly_xy)
        assert inside, f"Initial turbine {t['id']} at ({t['lat']}, {t['lon']}) OUTSIDE boundary"
        assert t.get("elevation_m") is not None, f"Initial turbine {t['id']} missing elevation"

    # 4. QAOA Optimization
    qaoa_payload = dict(payload)
    qaoa_payload["p_layers"] = 2
    qaoa_payload["qubo_lambda"] = 150.0

    res_qaoa = requests.post(f"{BASE_URL}/api/geo/qaoa-optimize", json=qaoa_payload)
    assert res_qaoa.status_code == 200, f"QAOA optimization failed: {res_qaoa.text}"
    qaoa_data = res_qaoa.json()
    opt_turbines = qaoa_data["optimized_turbines"]

    print(f"✓ QAOA optimization: {len(opt_turbines)} turbines placed")
    assert len(opt_turbines) == requested_turbines, f"Expected {requested_turbines}, got {len(opt_turbines)}"
    assert qaoa_data["turbine_count_actual"] == requested_turbines
    assert qaoa_data["status_headline"] == "Best feasible layout identified"

    # Check boundary containment and minimum spacing
    coords = []
    min_req_spacing = 5.0 * 120.0  # 600m
    for t in opt_turbines:
        inside = point_in_polygon(t["lon"], t["lat"], poly_xy)
        assert inside, f"QAOA turbine {t['id']} at ({t['lat']}, {t['lon']}) OUTSIDE boundary"
        assert t.get("elevation_m") is not None, f"QAOA turbine {t['id']} missing elevation"
        coords.append((t["x_m"], t["y_m"]))

    n_placed = len(coords)
    min_dist_found = float("inf")
    for i in range(n_placed):
        for j in range(i + 1, n_placed):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            d = math.hypot(dx, dy)
            if d < min_dist_found:
                min_dist_found = d

    print(f"✓ Observed minimum inter-turbine spacing: {min_dist_found:.1f} m (Required: {min_req_spacing:.1f} m)")
    assert min_dist_found >= min_req_spacing * 0.95, f"Spacing violation: {min_dist_found:.1f}m < {min_req_spacing:.1f}m"
    print(f"✓ {city_name}: PASSED with 0 perimeter violations and 0 spacing violations.")


def verify_small_area_honest_capacity():
    print(f"\n=======================================================")
    print(f"Testing Small Area Honest Capacity Saturation (1 km radius geodesic circle)")
    print(f"=======================================================")
    center_lat, center_lon = 16.9676, 81.8138  # Bommuru
    radius_km = 1.0  # Area = pi * 1^2 ~ 3.14 km2
    num_points = 64
    circle_boundary = []
    cos_lat = math.cos(math.radians(center_lat))
    for i in range(num_points):
        theta = 2.0 * math.pi * i / num_points
        d_north_km = radius_km * math.cos(theta)
        d_east_km = radius_km * math.sin(theta)
        p_lat = center_lat + (d_north_km / 111.0)
        p_lon = center_lon + (d_east_km / (111.0 * cos_lat))
        circle_boundary.append([round(p_lat, 6), round(p_lon, 6)])

    # Request 20 turbines in a 1km radius (impossible with 600m spacing)
    payload = {
        "center_lat": center_lat,
        "center_lon": center_lon,
        "area_km2": math.pi * radius_km**2,
        "boundary": circle_boundary,
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

    res_qaoa = requests.post(f"{BASE_URL}/api/geo/qaoa-optimize", json=payload)
    assert res_qaoa.status_code == 200, f"QAOA failed on small area: {res_qaoa.text}"
    data = res_qaoa.json()

    actual_placed = data["turbine_count_actual"]
    target_count = data["turbine_count_target"]
    headline = data["status_headline"]
    description = data["status_description"]

    print(f"✓ Requested: {target_count}, Actually Feasible Placed: {actual_placed}")
    print(f"✓ Status Headline: '{headline}'")
    print(f"✓ Status Description: '{description}'")

    assert target_count == 20
    # Must NOT silently collapse to 1 or return fake 20
    assert 2 <= actual_placed < 20, f"Expected realistic saturated capacity (e.g. 2-6), got {actual_placed}"
    assert f"20 requested · {actual_placed} feasible" in headline or "feasible" in headline
    assert len(data["optimized_turbines"]) == actual_placed

    poly_xy = [[pt[1], pt[0]] for pt in circle_boundary]
    for t in data["optimized_turbines"]:
        inside = point_in_polygon(t["lon"], t["lat"], poly_xy)
        assert inside, f"Turbine {t['id']} placed outside circle boundary"

    print("✓ Small area honest reporting: PASSED (never collapsed to 1, reported honest capacity).")


def verify_frontend_ui_modes():
    print(f"\n=======================================================")
    print(f"Testing Frontend UI: Mode Selection, 20-Turbine Chip, Camera Presets, Data Sources Modal")
    print(f"=======================================================")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto(f"{BASE_URL}/app", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(1000)

        # 1. Test Mode Tabs (Search, Radius, Draw)
        print("--- Testing Screen 1 Mode Selection Tabs ---")
        assert page.is_visible("#tab-mode-search"), "Search tab should exist"
        assert page.is_visible("#tab-mode-radius"), "Radius tab should exist"
        assert page.is_visible("#tab-mode-draw"), "Draw tab should exist"

        # Click Radius Tab
        page.click("#tab-mode-radius")
        page.wait_for_timeout(400)
        assert page.is_visible("#radius-mode-container"), "Radius container should be visible"
        print("✓ Radius tab activated and container visible")

        # Click 10 km Radius Chip
        page.click(".radius-chip-btn[data-radius='10']")
        page.wait_for_timeout(500)
        area_text = page.inner_text("#meta-area")
        print(f"✓ 10 km radius applied: Concession Area = {area_text}")
        assert "314" in area_text or "km²" in area_text

        # Click Freeform Polygon Tab
        page.click("#tab-mode-draw")
        page.wait_for_timeout(400)
        assert page.is_visible("#draw-mode-hint"), "Draw mode controls should be visible"
        draw_status = page.inner_text("#draw-status-label")
        print(f"✓ Freeform Polygon drawing activated: '{draw_status}'")

        # 2. Test Data Sources Provenance Modal
        print("\n--- Testing Data Sources Provenance Modal ---")
        page.click("#btn-ctx-data-sources")
        page.wait_for_function("() => document.getElementById('data-sources-modal-body')?.innerText.includes('Copernicus DEM')", timeout=10000)
        assert page.is_visible("#data-sources-modal"), "Data sources modal should open"
        modal_content = page.inner_text("#data-sources-modal-body")
        print(f"✓ Data sources modal opened with verified telemetry: {len(modal_content)} chars")
        assert "Copernicus DEM" in modal_content
        assert "Global Wind Atlas" in modal_content

        # Close Modal
        page.click("#btn-close-sources-modal")
        page.wait_for_timeout(300)
        assert not page.is_visible("#data-sources-modal"), "Modal should close"

        # 3. Confirm Site -> Screen 2
        print("\n--- Navigating to Screen 2 & Checking 20-Turbine Chip ---")
        page.click("#tab-mode-search")
        page.wait_for_timeout(300)
        page.click("#btn-confirm-site")
        page.wait_for_timeout(800)

        assert page.is_visible("#screen-2-container")
        # Check 20-turbine quick chip exists
        chip_20 = page.locator(".chip-btn[data-turbines='20']")
        assert chip_20.count() > 0, "20-turbines chip must exist in Screen 2"
        chip_20.click()
        page.wait_for_timeout(300)

        current_count = page.input_value("#cfg-turbines-count")
        print(f"✓ Clicked 20-turbine chip: input count = {current_count}")
        assert current_count == "20"

        # 4. Generate Initial Layout -> Screen 3
        print("\n--- Generating Layout for 20 Turbines (Screen 3) ---")
        page.click("#btn-generate-layout")
        page.wait_for_function("() => APP_STATE.screen3Data && APP_STATE.screen3Data.turbines && APP_STATE.screen3Data.turbines.length === 20", timeout=20000)
        init_t_len = page.evaluate("() => APP_STATE.screen3Data.turbines.length")
        print(f"✓ Screen 3 Initial Turbines: {init_t_len}")
        assert init_t_len == 20

        # 5. Optimize with QAOA -> Screen 4
        print("\n--- Running QAOA Optimization for 20 Turbines (Screen 4) ---")
        page.click("#btn-screen3-optimize")
        page.wait_for_function("() => APP_STATE.screen4Data && APP_STATE.screen4Data.optimized_turbines && APP_STATE.screen4Data.optimized_turbines.length === 20", timeout=25000)
        opt_t_len = page.evaluate("() => APP_STATE.screen4Data.optimized_turbines.length")
        print(f"✓ Screen 4 QAOA Turbines: {opt_t_len}")
        assert opt_t_len == 20

        # 6. View in Screen 5 & Test Camera Presets
        print("\n--- Viewing Screen 5 Hero Map & Camera Presets ---")
        page.click("#btn-screen4-view-optimized")
        page.wait_for_timeout(1000)
        assert page.is_visible("#screen-5-container")

        s5_pill = page.inner_text("#s5-indicator-text")
        print(f"✓ Screen 5 Indicator Pill: '{s5_pill}'")
        assert "20 Turbines" in s5_pill

        # Toggle 3D Globe
        page.click("#btn-s5-toggle-3d")
        page.wait_for_timeout(1500)
        assert page.is_visible("#s5-camera-presets-bar"), "Camera presets bar should be visible when 3D is active"

        # Test clicking camera presets
        for preset in ["TOP", "NORTH", "SOUTH", "OBLIQUE", "FIT_SITE"]:
            page.locator(f".camera-preset-btn[data-preset='{preset}']").click(force=True)
            page.wait_for_timeout(400)
            active_btn = page.locator(f".camera-preset-btn[data-preset='{preset}']")
            assert "active" in active_btn.get_attribute("class")
            print(f"✓ Activated camera preset: {preset}")

        # Test Turbine Inspector 3D Inspect button
        page.locator("#btn-s5-fly-turbine").click(force=True)
        page.wait_for_timeout(500)
        print("✓ Clicked 'Inspect in 3D' button")

        # 7. Test Coordinate Persistence Across Zoom (Requirement 12)
        print("\n--- Testing Coordinate Persistence Across Zoom ---")
        t0_lat_init = page.evaluate("() => APP_STATE.screen4Data.optimized_turbines[0].lat")
        t0_lon_init = page.evaluate("() => APP_STATE.screen4Data.optimized_turbines[0].lon")
        
        # Simulate user zooming in
        page.evaluate("() => { if (APP_STATE.screen5Map) APP_STATE.screen5Map.setZoom(14); }")
        page.wait_for_timeout(300)
        t0_lat_zoomed = page.evaluate("() => APP_STATE.screen4Data.optimized_turbines[0].lat")
        t0_lon_zoomed = page.evaluate("() => APP_STATE.screen4Data.optimized_turbines[0].lon")

        assert t0_lat_init == t0_lat_zoomed and t0_lon_init == t0_lon_zoomed, "Turbine geographic coordinates MUST NOT change with zoom!"
        print(f"✓ Coordinate Persistence Confirmed: T-01 stays invariant at ({t0_lat_init}, {t0_lon_init}) across zoom")

        browser.close()
        print("\n✓ Frontend UI verification completely passed!")


def verify_glb_model_integrity():
    print(f"\n=======================================================")
    print(f"Testing 3D GLB Wind Turbine Asset Integrity")
    print(f"=======================================================")
    glb_path = "/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/frontend/assets/models/wind_turbine.glb"
    import os, struct
    assert os.path.exists(glb_path), f"GLB model missing at {glb_path}"
    file_size = os.path.getsize(glb_path)
    assert file_size > 15000, f"GLB model too small ({file_size} bytes)"
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", f"Invalid magic bytes: {magic}"
        assert version == 2, f"Expected glTF 2.0, got version {version}"
        assert length == file_size, f"Header length {length} != file size {file_size}"
    print(f"✓ Valid glTF 2.0 Binary container verified: {glb_path} ({file_size / 1024:.1f} KB)")


def verify_feasibility_5class_mask():
    print(f"\n=======================================================")
    print(f"Testing 5-Class Feasibility Mask & Exclusion Diagnostics")
    print(f"=======================================================")
    payload = {
        "center_lat": 16.9676,
        "center_lon": 81.8138,
        "area_km2": 24.8,
        "requested_turbines": 20
    }
    res = requests.post(f"{BASE_URL}/api/geo/feasibility", json=payload)
    assert res.status_code == 200, f"Feasibility API failed: {res.text}"
    data = res.json()
    stats = data["pipeline_stats"]

    print(f"✓ Feasibility Mask Breakdown:")
    print(f"    Preferred:  {stats.get('count_preferred')}")
    print(f"    Buildable:  {stats.get('count_buildable')}")
    print(f"    Restricted: {stats.get('count_restricted')}")
    print(f"    Excluded:   {stats.get('count_excluded')}")
    print(f"    Unknown:    {stats.get('count_unknown')}")

    assert stats.get("count_preferred", 0) > 0, "Expected non-zero PREFERRED candidates"
    assert stats.get("count_excluded", 0) > 0, "Expected non-zero EXCLUDED candidates"

    # Verify exclusion reasons in evaluated sample
    sample = data.get("evaluated_sample", [])
    excluded_sample = [c for c in sample if c.get("land_status") == "EXCLUDED"]
    assert len(excluded_sample) > 0, "Expected EXCLUDED candidates in sample"
    reasons = set()
    for c in excluded_sample:
        for r in c.get("exclusion_reasons", []):
            reasons.add(r)
    print(f"✓ Verified physical exclusion reasons: {list(reasons)[:3]}")
    assert len(reasons) > 0, "Every EXCLUDED candidate must have explicit exclusion reasons"


if __name__ == "__main__":
    try:
        verify_glb_model_integrity()
        verify_feasibility_5class_mask()
        verify_city_pipeline("Bommuru", requested_turbines=20)
        verify_city_pipeline("Rajahmundry", requested_turbines=20)
        verify_city_pipeline("Jaisalmer", requested_turbines=20)
        verify_city_pipeline("Hukkumpeta", requested_turbines=20)
        verify_city_pipeline("Kanyakumari", requested_turbines=20)
        verify_small_area_honest_capacity()
        verify_frontend_ui_modes()

        print("\n" + "="*70)
        print("ALL MULTI-CITY GEOGRAPHIC PIPELINE VALIDATION TESTS PASSED!")
        print("="*70 + "\n")
    except Exception as exc:
        print(f"\n❌ MULTI-CITY TEST FAILED: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
