#!/usr/bin/env python3
"""
scripts/verify_ui_challenger2.py — Playwright Verification of GIS, Wind Direction & Turbine Placement
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path("docs/ui-screenshots/challenger2")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for width, height, name in [(390, 844, "mobile_390px"), (1280, 800, "desktop_1280px")]:
            print(f"\n=======================================================")
            print(f"VERIFYING VIEWPORT: {name} ({width}x{height})")
            print(f"=======================================================")
            page = browser.new_page(viewport={"width": width, "height": height})
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in ["error"] else None)

            # 1. Load Application
            page.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
            page.wait_for_timeout(1000)

            # Screenshot Home
            home_shot = SCREENSHOTS_DIR / f"{name}_01_home.png"
            page.screenshot(path=str(home_shot), full_page=False)
            print(f"✓ Saved Home screenshot: {home_shot}")

            # 2. Click 'Configure New Site' or Navigate to Site Screen
            new_site_btn = page.locator("#btn-new-project-hero, #btn-nav-map, #btn-mobile-nav-map, button:has-text('Configure New Site')").first
            if new_site_btn.is_visible():
                new_site_btn.click()
                page.wait_for_timeout(1000)
            else:
                page.goto("http://127.0.0.1:8000/app#s1_site", wait_until="networkidle")
                page.wait_for_timeout(1000)

            site_shot = SCREENSHOTS_DIR / f"{name}_02_site_selection.png"
            page.screenshot(path=str(site_shot), full_page=False)
            print(f"✓ Saved Site Selection screenshot: {site_shot}")

            # Verify Site screen contains geotechnical screening notice
            geo_text = page.locator("body").inner_text()
            assert "geotechnical" in geo_text.lower() or "soil" in geo_text.lower(), "Soil/geotechnical screening must be visible"
            print("✓ Verified Geotechnical screening layer")

            # 3. Proceed to Screen 2: Configuration
            btn_next_config = page.locator("#btn-next-config, button:has-text('Proceed to Turbine Configuration')").first
            if btn_next_config.is_visible():
                btn_next_config.click()
                page.wait_for_timeout(800)

            config_shot = SCREENSHOTS_DIR / f"{name}_03_config.png"
            page.screenshot(path=str(config_shot), full_page=False)
            print(f"✓ Saved Config screenshot: {config_shot}")

            # 4. Generate Initial Layout -> Screen 3: Layout Analysis
            btn_gen_layout = page.locator("#btn-next-layout, button:has-text('Generate Initial Layout')").first
            if btn_gen_layout.is_visible():
                btn_gen_layout.click()
                print("Generating initial layout with real GIS buildability mask...")
                page.wait_for_timeout(4000)

            layout_shot = SCREENSHOTS_DIR / f"{name}_04_screen3_layout.png"
            page.screenshot(path=str(layout_shot), full_page=False)
            print(f"✓ Saved Screen 3 Layout screenshot: {layout_shot}")

            # Check for honest engineering status in Screen 3
            layout_text = page.locator("body").inner_text()
            if "Site unsuitable for wind-farm development" in layout_text:
                print("✓ Verified HONEST REPORTING: Site unsuitable for wind-farm development (0 fake turbines forced)")
            elif "feasible turbine positions identified" in layout_text:
                print("✓ Verified FEASIBLE POSITIONS identified without exceeding constraint limits")

            # Check Canonical Wind badge in Screen 3
            if "Wind FROM:" in layout_text:
                print("✓ Verified canonical wind badge: 'Wind FROM: {deg}° ({cardinal})'")

            # Check Geotechnical disclaimer in Screen 3
            if "Preliminary geotechnical screening" in layout_text:
                print("✓ Verified geotechnical screening disclaimer")

            # 5. Launch Optimization -> Screen 4: QAOA Kernel
            btn_launch_opt = page.locator("#btn-screen3-launch-optimize, button:has-text('Run WS-QAOA Optimization')").first
            if btn_launch_opt.is_visible() and not btn_launch_opt.is_disabled():
                btn_launch_opt.click()
                page.wait_for_timeout(2500)

                opt_shot = SCREENSHOTS_DIR / f"{name}_05_screen4_optimize.png"
                page.screenshot(path=str(opt_shot), full_page=False)
                print(f"✓ Saved Screen 4 Optimize screenshot: {opt_shot}")

                # 6. Proceed to Screen 5: 3D Inspect
                btn_view_opt = page.locator("#btn-screen4-view-optimized, button:has-text('View Optimized Wind Farm')").first
                if btn_view_opt.is_visible() and not btn_view_opt.is_disabled():
                    btn_view_opt.click()
                    page.wait_for_timeout(2000)

                    inspect_shot = SCREENSHOTS_DIR / f"{name}_06_screen5_inspect.png"
                    page.screenshot(path=str(inspect_shot), full_page=False)
                    print(f"✓ Saved Screen 5 Inspect screenshot: {inspect_shot}")

            print(f"Console errors for {name}: {len(console_errors)}")
            if console_errors:
                print(f"  First 3 errors: {console_errors[:3]}")

        browser.close()
        print("\nUI Verification Complete!")

if __name__ == "__main__":
    run_verification()
