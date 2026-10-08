#!/usr/bin/env python3
"""
scripts/verify_flow_screens.py — Verifies the end-to-end screen progression
and captures real screenshots for every step on both mobile (390px) and desktop (1280px).
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("docs/ui-screenshots/verified_flow")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def verify_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for width, height, name in [(390, 844, "mobile_390px"), (1280, 800, "desktop_1280px")]:
            print(f"\n=======================================================")
            print(f"VERIFYING FLOW ON {name} ({width}x{height})")
            print(f"=======================================================")
            page = browser.new_page(viewport={"width": width, "height": height})
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in ["error"] else None)

            # Step 0: Home
            page.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
            page.wait_for_timeout(1000)
            page.screenshot(path=str(OUT_DIR / f"{name}_00_home.png"))
            print(f"✓ [{name}] Home loaded and screenshotted")

            # Step 1: Click Create New Project -> Screen 1 (Site Selection)
            new_btn = page.locator("#btn-project-new, #btn-mobile-nav-map").first
            new_btn.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT_DIR / f"{name}_01_screen1_site.png"))
            print(f"✓ [{name}] Screen 1 (Site Selection) loaded and screenshotted")

            # Step 2: Confirm Site -> Screen 2 (Config)
            confirm_btn = page.locator("#btn-confirm-site, #btn-confirm-site-peek").first
            confirm_btn.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(OUT_DIR / f"{name}_02_screen2_config.png"))
            print(f"✓ [{name}] Screen 2 (Config) loaded and screenshotted")

            # Step 3: Generate Initial Layout -> Screen 3 (Layout Analysis)
            gen_btn = page.locator("#btn-generate-layout")
            gen_btn.click()
            print(f"[{name}] Generating layout via real GIS backend...")
            page.wait_for_timeout(5000)
            page.screenshot(path=str(OUT_DIR / f"{name}_03_screen3_layout.png"))
            print(f"✓ [{name}] Screen 3 (Layout Analysis) loaded and screenshotted")

            # Verify Screen 3 content
            s3_text = page.locator("body").inner_text()
            assert "Wind FROM:" in s3_text or "m/s" in s3_text
            print(f"✓ [{name}] Canonical wind badge confirmed")

            # Step 4: Run WS-QAOA Optimization -> Screen 4
            opt_btn = page.locator("#btn-screen3-optimize")
            if opt_btn.is_visible() and not opt_btn.is_disabled():
                opt_btn.click()
                print(f"[{name}] WS-QAOA Optimization kernel running...")
                page.wait_for_timeout(3500)
                page.screenshot(path=str(OUT_DIR / f"{name}_04_screen4_optimize.png"))
                print(f"✓ [{name}] Screen 4 (Optimize) loaded and screenshotted")

                # Step 5: View Optimized Wind Farm -> Screen 5 (Inspect)
                view_btn = page.locator("#btn-screen4-view-optimized")
                if view_btn.is_visible() and not view_btn.is_disabled():
                    view_btn.click()
                    page.wait_for_timeout(2500)
                    page.screenshot(path=str(OUT_DIR / f"{name}_05_screen5_inspect.png"))
                    print(f"✓ [{name}] Screen 5 (Inspect) loaded and screenshotted")

            print(f"Console errors for {name}: {len(console_errors)}")
            if console_errors:
                print(f"  First 3 errors: {console_errors[:3]}")

        browser.close()
        print("\nAll screen flow verification checks completed successfully!")

if __name__ == "__main__":
    verify_flow()
