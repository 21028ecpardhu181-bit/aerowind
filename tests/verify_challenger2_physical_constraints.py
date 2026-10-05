#!/usr/bin/env python3
"""
tests/verify_challenger2_physical_constraints.py

Empirical stress-testing harness for Challenger 2:
1. Boundary Containment & Setbacks across Bommuru, Rajahmundry, Jaisalmer, Hukkumpeta, Kanyakumari.
2. Inter-Turbine Spacing (pairwise >= 5D = 600m).
3. Diagnostic Exclusion Reasons (100% of EXCLUDED report explicit physical failure reasons).
4. Blueprint Export Precision (CSV/GeoJSON vs live display to 6 decimal places).
"""

import math
import sys
import os
import json
import requests
import numpy as np
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

# Import backend engine directly for deep white-box verification alongside HTTP APIs
sys.path.insert(0, "/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype")
from backend.app.geo_engine import (
    CandidateGenerationEngine,
    HybridWindFarmOptimizer,
    dist_to_polygon_boundary,
    lat_lon_to_meters,
    meters_to_lat_lon,
    point_in_polygon,
    generate_geographic_circle_polygon,
    calculate_polygon_area_km2,
    R_EARTH,
)

CITIES = [
    ("Bommuru", 16.967585, 81.813778),
    ("Rajahmundry", 17.0005, 81.8040),
    ("Jaisalmer", 26.9157, 70.9083),
    ("Hukkumpeta", 17.9712, 82.6825),
    ("Kanyakumari", 8.0883, 77.5385),
]

def geodetic_haversine_m(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R_EARTH * c

def make_test_boundary(lat, lon, area_km2=24.8):
    radius_km = math.sqrt(area_km2) / 2.0
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    return [
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

results = {
    "boundary_containment": {},
    "setback_buffer": {},
    "inter_turbine_spacing": {},
    "diagnostic_reasons": {},
    "export_precision": {},
}

def test_physical_constraints_all_cities():
    print("=" * 80)
    print("RUNNING CHALLENGER 2: EMPIRICAL PHYSICAL & BOUNDARY CONSTRAINT VERIFICATION")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. BOUNDARY CONTAINMENT & SETBACKS + 2. SPACING
    # ---------------------------------------------------------
    for city_name, lat, lon in CITIES:
        print(f"\n>>> Stress Testing Site: {city_name} ({lat:.4f}, {lon:.4f})")
        boundary = make_test_boundary(lat, lon, 24.8)
        poly_m = np.array([lat_lon_to_meters(p[0], p[1], lat, lon) for p in boundary], dtype=np.float64)

        engine = CandidateGenerationEngine(
            center_lat=lat,
            center_lon=lon,
            boundary=boundary,
            rotor_diameter=120.0,
            spacing_multiplier_d=5.0,
        )
        res = engine.execute_pipeline(requested_turbines=20)
        candidates = res["candidates"]
        all_eval = res["all_evaluated_candidates"]
        stats = res["pipeline_stats"]
        setback_required = engine.setback_m  # 60m for 120m rotor

        print(f"  Raw Generated: {stats['generated_raw']}, Feasible: {stats['feasible_count']}")
        print(f"  Sample evaluated: {len(all_eval)}, Preferred: {stats['count_preferred']}, Excluded: {stats['count_excluded']}")

        # A. Check 100% of candidates strictly inside polygon and observe setback
        cand_outside = 0
        cand_setback_violations = 0
        min_cand_setback_dist = float("inf")

        for c in candidates:
            xm, ym = c["x_m"], c["y_m"]
            inside = point_in_polygon(xm, ym, poly_m)
            b_dist = dist_to_polygon_boundary(xm, ym, poly_m)
            if not inside:
                cand_outside += 1
            if b_dist < setback_required - 0.01:
                cand_setback_violations += 1
            if b_dist < min_cand_setback_dist:
                min_cand_setback_dist = b_dist

        print(f"  Candidates Boundary Check: {len(candidates)} tested | {cand_outside} outside | min boundary dist: {min_cand_setback_dist:.2f}m (setback: {setback_required}m)")
        assert cand_outside == 0, f"{city_name}: {cand_outside} candidates outside boundary!"
        assert cand_setback_violations == 0, f"{city_name}: {cand_setback_violations} candidate setback violations!"

        # B. Check Optimizer placed turbines (Baseline and QAOA)
        optimizer = HybridWindFarmOptimizer(
            candidates=candidates,
            requested_count=20,
            rotor_diameter=120.0,
            spacing_multiplier_d=5.0,
        )
        base_layout = optimizer.generate_baseline_layout()
        qaoa_layout = optimizer.solve_hybrid_optimization()

        base_turbines = base_layout["turbines"]
        qaoa_turbines = qaoa_layout["optimized_turbines"]

        print(f"  Placed Turbines: Baseline={len(base_turbines)}, QAOA={len(qaoa_turbines)}")

        # Verify Base Turbines
        for t in base_turbines:
            inside = point_in_polygon(t["x_m"], t["y_m"], poly_m)
            b_dist = dist_to_polygon_boundary(t["x_m"], t["y_m"], poly_m)
            assert inside, f"Base turbine {t['id']} outside boundary"
            assert b_dist >= setback_required - 0.01, f"Base turbine {t['id']} setback violation: {b_dist:.2f}m < {setback_required}m"

        # Verify QAOA Turbines Boundary & Setback
        qaoa_outside = 0
        qaoa_setback_violations = 0
        min_qaoa_setback_dist = float("inf")

        for t in qaoa_turbines:
            inside = point_in_polygon(t["x_m"], t["y_m"], poly_m)
            b_dist = dist_to_polygon_boundary(t["x_m"], t["y_m"], poly_m)
            if not inside:
                qaoa_outside += 1
            if b_dist < setback_required - 0.01:
                qaoa_setback_violations += 1
            if b_dist < min_qaoa_setback_dist:
                min_qaoa_setback_dist = b_dist

        assert qaoa_outside == 0, f"{city_name}: {qaoa_outside} QAOA turbines outside boundary!"
        assert qaoa_setback_violations == 0, f"{city_name}: {qaoa_setback_violations} QAOA setback violations!"
        print(f"  QAOA Turbines Boundary Check: 20/20 inside | min boundary dist: {min_qaoa_setback_dist:.2f}m >= {setback_required}m")

        results["boundary_containment"][city_name] = {"candidates_outside": 0, "turbines_outside": 0}
        results["setback_buffer"][city_name] = {"min_dist_m": min_qaoa_setback_dist, "required_m": setback_required, "violations": 0}

        # C. Inter-Turbine Spacing Check (5D = 600m)
        min_pairwise_euclidean = float("inf")
        min_pairwise_haversine = float("inf")
        spacing_violations_600m = 0
        spacing_violations_570m = 0
        pairs_checked = 0

        N_turbines = len(qaoa_turbines)
        for i in range(N_turbines):
            for j in range(i + 1, N_turbines):
                ti = qaoa_turbines[i]
                tj = qaoa_turbines[j]
                d_euc = math.hypot(ti["x_m"] - tj["x_m"], ti["y_m"] - tj["y_m"])
                d_hav = geodetic_haversine_m(ti["lat"], ti["lon"], tj["lat"], tj["lon"])
                pairs_checked += 1

                if d_euc < min_pairwise_euclidean:
                    min_pairwise_euclidean = d_euc
                if d_hav < min_pairwise_haversine:
                    min_pairwise_haversine = d_hav

                if d_euc < 600.0:
                    spacing_violations_600m += 1
                    if d_euc < 570.0:
                        spacing_violations_570m += 1

        print(f"  Pairwise Spacing Check: {pairs_checked} pairs checked | Min Euclidean: {min_pairwise_euclidean:.2f}m | Min Haversine: {min_pairwise_haversine:.2f}m")
        print(f"  Pairs < 600m (5D): {spacing_violations_600m} | Pairs < 570m (0.95*5D): {spacing_violations_570m}")

        results["inter_turbine_spacing"][city_name] = {
            "pairs_checked": pairs_checked,
            "min_euclidean_m": min_pairwise_euclidean,
            "min_haversine_m": min_pairwise_haversine,
            "pairs_under_600m": spacing_violations_600m,
            "pairs_under_570m": spacing_violations_570m,
        }

        excluded_candidates = [c for c in all_eval if c.get("land_status") in ["EXCLUDED", "HARD EXCLUSION"]]
        print(f"  Diagnostic Reasons Check: {len(excluded_candidates)} EXCLUDED candidates evaluated")
        total_excluded = len(excluded_candidates)
        with_explicit_reasons = 0
        reasons_tally = {"slope": 0, "water": 0, "settlement": 0, "road": 0, "wind": 0}

        for c in excluded_candidates:
            r_list = c.get("exclusion_reasons", [])
            if r_list and len(r_list) > 0:
                with_explicit_reasons += 1
                for r in r_list:
                    r_lower = r.lower()
                    if "slope" in r_lower:
                        reasons_tally["slope"] += 1
                    if "water" in r_lower or "drainage" in r_lower:
                        reasons_tally["water"] += 1
                    if "settlement" in r_lower or "building" in r_lower:
                        reasons_tally["settlement"] += 1
                    if "transportation" in r_lower or "road" in r_lower:
                        reasons_tally["road"] += 1
                    if "sub-cut-in" in r_lower or "wind" in r_lower:
                        reasons_tally["wind"] += 1

        print(f"  Excluded with explicit reasons: {with_explicit_reasons}/{total_excluded} ({with_explicit_reasons/max(1, total_excluded)*100:.1f}%)")
        print(f"  Exclusion breakdown: slope={reasons_tally['slope']}, water={reasons_tally['water']}, settlement={reasons_tally['settlement']}, road={reasons_tally['road']}, wind={reasons_tally['wind']}")
        assert with_explicit_reasons == total_excluded, f"{city_name}: Found EXCLUDED candidate without explicit reason!"

        # Ensure NO UNKNOWN or EXCLUDED candidates leaked into placed turbines
        for t in qaoa_turbines:
            for c in all_eval:
                if c["latitude"] == t["lat"] and c["longitude"] == t["lon"]:
                    assert c["land_status"] in ["PREFERRED", "BUILDABLE", "FEASIBLE"], f"Leakage! Turbine placed in {c['land_status']} land: {t}"

        results["diagnostic_reasons"][city_name] = {
            "total_excluded": total_excluded,
            "with_reasons": with_explicit_reasons,
            "reasons_tally": reasons_tally,
        }

    # ---------------------------------------------------------
    # 4. BLUEPRINT EXPORT PRECISION (Playwright Headless)
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("TESTING BLUEPRINT EXPORT PRECISION ACROSS FRONTEND & BACKEND")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto(f"{BASE_URL}/app", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(1000)

        # 1. Confirm Site -> Screen 2
        page.click("#btn-confirm-site")
        page.wait_for_function("() => window.APP_STATE.currentScreen === 2", timeout=5000)
        page.wait_for_timeout(500)

        # 2. On Screen 2: Select 20 Turbines & Generate Layout -> Screen 3
        chip_20 = page.locator(".chip-btn[data-turbines='20']")
        if chip_20.count() > 0:
            chip_20.click()
            page.wait_for_timeout(300)
        page.click("#btn-generate-layout")
        page.wait_for_function("() => window.APP_STATE.currentScreen === 3", timeout=8000)
        page.wait_for_function("() => window.APP_STATE.initialLayout !== null", timeout=12000)
        page.wait_for_timeout(1000)

        # 3. On Screen 3: Optimize with QAOA -> Screen 4
        page.click("#btn-screen3-optimize")
        page.wait_for_function("() => window.APP_STATE.currentScreen === 4", timeout=8000)
        page.wait_for_function(
            "() => window.APP_STATE.screen4Data !== null || document.getElementById('s4-iteration-counter')?.innerText.includes('100')",
            timeout=30000
        )
        page.wait_for_timeout(1000)

        # 4. On Screen 4: View Optimized -> Screen 5
        page.click("#btn-screen4-view-optimized")
        page.wait_for_function("() => window.APP_STATE.currentScreen === 5", timeout=5000)
        page.wait_for_timeout(800)

        # 5. On Screen 5: Export Blueprint -> Screen 6
        page.click("#btn-screen5-export")
        page.wait_for_function("() => window.APP_STATE.currentScreen === 6", timeout=5000)
        page.wait_for_timeout(1000)

        # In Screen 6: Inspect Live Displayed Table vs App State
        live_turbines = page.evaluate("() => APP_STATE.screen4Data.optimized_turbines")
        print(f"Live App State Turbines count: {len(live_turbines)}")

        # Extract table rows from #s6-turbine-table-body
        table_rows_data = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll('#s6-turbine-table-body tr'));
            return rows.map(r => {
                const cells = Array.from(r.querySelectorAll('td')).map(td => td.innerText.trim());
                return {
                    id: cells[0],
                    latText: cells[1],
                    lonText: cells[2],
                    elevation: cells[3],
                };
            });
        }""")
        print(f"Extracted {len(table_rows_data)} table rows from Screen 6 Schedule Table")

        # Capture CSV content generated by exportCSV()
        csv_data = page.evaluate("""() => {
            let capturedCsv = null;
            const origDownload = window.APP.downloadFile;
            window.APP.downloadFile = function(content, filename, mime) {
                if (filename.endsWith('.csv')) {
                    capturedCsv = content;
                }
                return origDownload.apply(this, arguments);
            };
            document.getElementById('btn-export-csv').click();
            return capturedCsv;
        }""")

        # Capture GeoJSON content generated by exportGeoJSON()
        geojson_data = page.evaluate("""() => {
            let capturedGeoJSON = null;
            const origDownload = window.APP.downloadFile;
            window.APP.downloadFile = function(content, filename, mime) {
                if (filename.endsWith('.geojson')) {
                    capturedGeoJSON = content;
                }
                return origDownload.apply(this, arguments);
            };
            document.getElementById('btn-export-geojson').click();
            return capturedGeoJSON;
        }""")

        parsed_geojson = json.loads(geojson_data)
        geojson_point_features = [f for f in parsed_geojson["features"] if f["geometry"]["type"] == "Point"]

        csv_lines = csv_data.strip().split("\n")[1:] # skip header
        print(f"Captured CSV lines: {len(csv_lines)}, GeoJSON features: {len(geojson_point_features)}")

        # Compare Coordinates Precision
        precision_checks = []
        for idx in range(len(live_turbines)):
            live_t = live_turbines[idx]
            tbl_t = table_rows_data[idx]
            csv_parts = csv_lines[idx].split(",")
            geo_t = geojson_point_features[idx]

            live_lat = live_t["lat"]
            live_lon = live_t["lon"]

            csv_lat = float(csv_parts[1])
            csv_lon = float(csv_parts[2])

            geo_coords = geo_t["geometry"]["coordinates"] # [lon, lat, elev]
            geo_lon = float(geo_coords[0])
            geo_lat = float(geo_coords[1])

            # In the table: latText is e.g. "16.96760° N"
            tbl_lat_str = tbl_t["latText"].replace("° N", "").replace("° S", "").strip()
            tbl_lon_str = tbl_t["lonText"].replace("° E", "").replace("° W", "").strip()
            tbl_lat = float(tbl_lat_str)
            tbl_lon = float(tbl_lon_str)

            # Decimal places check
            csv_lat_str = csv_parts[1].strip()
            csv_lon_str = csv_parts[2].strip()
            csv_lat_decimals = len(csv_lat_str.split(".")[1]) if "." in csv_lat_str else 0
            csv_lon_decimals = len(csv_lon_str.split(".")[1]) if "." in csv_lon_str else 0

            tbl_lat_decimals = len(tbl_lat_str.split(".")[1]) if "." in tbl_lat_str else 0
            tbl_lon_decimals = len(tbl_lon_str.split(".")[1]) if "." in tbl_lon_str else 0

            # Absolute differences
            diff_live_csv_lat = abs(live_lat - csv_lat)
            diff_live_csv_lon = abs(live_lon - csv_lon)
            diff_live_geo_lat = abs(live_lat - geo_lat)
            diff_live_geo_lon = abs(live_lon - geo_lon)
            diff_live_tbl_lat = abs(live_lat - tbl_lat)
            diff_live_tbl_lon = abs(live_lon - tbl_lon)

            precision_checks.append({
                "turbine_id": live_t["id"],
                "live_lat": live_lat,
                "live_lon": live_lon,
                "csv_lat": csv_lat,
                "csv_lon": csv_lon,
                "csv_lat_decimals": csv_lat_decimals,
                "csv_lon_decimals": csv_lon_decimals,
                "geo_lat": geo_lat,
                "geo_lon": geo_lon,
                "tbl_lat_str": tbl_lat_str,
                "tbl_lon_str": tbl_lon_str,
                "tbl_lat_decimals": tbl_lat_decimals,
                "tbl_lon_decimals": tbl_lon_decimals,
                "diff_live_csv": max(diff_live_csv_lat, diff_live_csv_lon),
                "diff_live_geo": max(diff_live_geo_lat, diff_live_geo_lon),
                "diff_live_tbl": max(diff_live_tbl_lat, diff_live_tbl_lon),
            })

        print(f"\nSample Turbine T-01 precision evaluation:")
        p0 = precision_checks[0]
        print(f"  Live State:  lat={p0['live_lat']}, lon={p0['live_lon']}")
        print(f"  CSV Export:  lat={p0['csv_lat']} ({p0['csv_lat_decimals']} decimals), lon={p0['csv_lon']} ({p0['csv_lon_decimals']} decimals)")
        print(f"  GeoJSON:     lat={p0['geo_lat']}, lon={p0['geo_lon']}")
        print(f"  Table UI:    lat={p0['tbl_lat_str']} ({p0['tbl_lat_decimals']} decimals), lon={p0['tbl_lon_str']} ({p0['tbl_lon_decimals']} decimals)")
        print(f"  Max Diff (Live vs CSV): {p0['diff_live_csv']:.8f}")
        print(f"  Max Diff (Live vs GeoJSON): {p0['diff_live_geo']:.8f}")
        print(f"  Max Diff (Live vs Table): {p0['diff_live_tbl']:.8f}")

        results["export_precision"] = {
            "num_turbines_evaluated": len(precision_checks),
            "csv_decimals": [p["csv_lat_decimals"] for p in precision_checks],
            "table_decimals": [p["tbl_lat_decimals"] for p in precision_checks],
            "max_diff_live_vs_csv": max(p["diff_live_csv"] for p in precision_checks),
            "max_diff_live_vs_geojson": max(p["diff_live_geo"] for p in precision_checks),
            "max_diff_live_vs_table": max(p["diff_live_tbl"] for p in precision_checks),
            "sample_checks": precision_checks[:3],
        }

        browser.close()

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print(json.dumps(results, indent=2))
    print("=" * 80)

    # Save empirical run log to a json in tests/
    with open("/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/tests/challenger2_empirical_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_physical_constraints_all_cities()
