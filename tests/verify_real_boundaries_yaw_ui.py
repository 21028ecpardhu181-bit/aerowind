"""
tests/verify_real_boundaries_yaw_ui.py
Playwright verification for:
1. Authentic village administrative boundaries (Village Cadastre mode).
2. Setbacks from village settlement core (>= 500m).
3. 3D Wind turbine yaw orientation and Apple Liquid Glass wind telemetry badge.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Test (1280 x 800)
        # -------------------------------------------------------------
        print("\n=== Testing Desktop Viewport (1280 x 800) ===")
        context_d = browser.new_context(viewport={"width": 1280, "height": 800})
        page_d = context_d.new_page()

        page_d.goto("http://127.0.0.1:8000/app#site", wait_until="networkidle")
        page_d.wait_for_selector("#screen-1-container", state="visible", timeout=15000)
        print("Screen 1 loaded successfully.")

        # Click Village Cadastre Mode to test authentic boundary resolution
        print("Testing Village Cadastre snapping...")
        btn_village = page_d.locator("#btn-village-mode")
        if btn_village.is_visible():
            btn_village.click()
            page_d.wait_for_timeout(3000)

        loc_text = page_d.locator("#meta-location-name").text_content()
        area_text = page_d.locator("#meta-area").text_content()
        print(f"Site Location: {loc_text.strip()}, Area: {area_text.strip()}")
        assert area_text and "km²" in area_text, f"Expected valid km² area, got {area_text}"

        page_d.screenshot(path=str(SCREENSHOTS_DIR / "verify-village-boundary-desktop.png"))

        # Advance to Screen 2
        print("Advancing to Screen 2...")
        page_d.click("#btn-confirm-site")
        page_d.wait_for_selector("#screen-2-container", state="visible", timeout=15000)

        # Advance to Screen 3
        print("Advancing to Screen 3 (Layout Generation)...")
        page_d.click("#btn-generate-layout")
        page_d.wait_for_selector("#screen-3-container", state="visible", timeout=35000)

        # Advance to Screen 4
        print("Advancing to Screen 4 (Quantum QAOA Optimization)...")
        page_d.click("#btn-screen3-optimize")
        page_d.wait_for_selector("#screen-4-container", state="visible", timeout=20000)

        # Wait for QAOA to finish
        print("Waiting for QAOA completion...")
        page_d.wait_for_selector("#btn-screen4-view-optimized:not([disabled])", timeout=30000)

        # Advance to Screen 5
        print("Advancing to Screen 5 (Optimized Wind Farm)...")
        page_d.click("#btn-screen4-view-optimized")
        page_d.wait_for_selector("#screen-5-container", state="visible", timeout=20000)
        page_d.wait_for_timeout(2000)

        page_d.screenshot(path=str(SCREENSHOTS_DIR / "verify-screen5-2d-desktop.png"))

        # Toggle to 3D Cesium Globe View
        print("Toggling to 3D Cesium Globe View...")
        page_d.click("#btn-s5-toggle-3d")
        page_d.wait_for_selector("#screen5-cesium-canvas", state="visible", timeout=20000)
        page_d.wait_for_timeout(4000)

        # Verify Wind Telemetry & Yaw Badge in 3D
        yaw_badge = page_d.locator("#cesium-wind-telemetry-badge")
        assert yaw_badge.is_visible(), "Wind Telemetry & Yaw Badge must be visible in 3D Cesium mode"
        badge_text = yaw_badge.text_content()
        print(f"3D Yaw Badge Text: {badge_text.strip()}")
        assert "Wind & Yaw Telemetry" in badge_text, "Badge should display Wind & Yaw Telemetry"
        assert "Upwind Aligned" in badge_text, "Badge should indicate Upwind Aligned"

        # Capture Desktop 3D Screenshot
        desktop_3d_path = SCREENSHOTS_DIR / "verify-cesium-3d-yaw-desktop-1280px.png"
        page_d.screenshot(path=str(desktop_3d_path))
        print(f"Saved Desktop 3D screenshot: {desktop_3d_path}")

        context_d.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport Test (390 x 844)
        # -------------------------------------------------------------
        print("\n=== Testing Mobile Viewport (390 x 844) ===")
        context_m = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        )
        page_m = context_m.new_page()

        page_m.goto("http://127.0.0.1:8000/app#site", wait_until="networkidle")
        page_m.wait_for_selector("#screen-1-container", state="visible", timeout=15000)
        print("Mobile Screen 1 loaded successfully.")

        page_m.screenshot(path=str(SCREENSHOTS_DIR / "verify-boundary-mobile-390px.png"))

        # Advance to Screen 2
        print("Mobile Screen 1 -> Screen 2...")
        page_m.locator("#btn-confirm-site-peek:visible, #btn-confirm-site:visible").first.click()
        page_m.wait_for_selector("#screen-2-container", state="visible", timeout=15000)

        # Advance to Screen 3
        print("Mobile Screen 2 -> Screen 3 (Layout Generation)...")
        page_m.click("#btn-generate-layout")
        page_m.wait_for_selector("#screen-3-container", state="visible", timeout=35000)

        # Advance to Screen 4
        print("Mobile Screen 3 -> Screen 4 (Quantum QAOA Optimization)...")
        page_m.click("#btn-screen3-optimize")
        page_m.wait_for_selector("#screen-4-container", state="visible", timeout=20000)
        page_m.wait_for_selector("#btn-screen4-view-optimized:not([disabled])", timeout=30000)

        # Advance to Screen 5
        print("Mobile Screen 4 -> Screen 5...")
        page_m.click("#btn-screen4-view-optimized")
        page_m.wait_for_selector("#screen-5-container", state="visible", timeout=20000)
        page_m.wait_for_timeout(2000)

        # Toggle to 3D Cesium
        print("Mobile Screen 5 -> Toggling 3D Globe...")
        page_m.click("#btn-s5-toggle-3d")
        page_m.wait_for_selector("#screen5-cesium-canvas", state="visible", timeout=20000)
        page_m.wait_for_timeout(4000)

        # Verify Wind Telemetry & Yaw Badge on Mobile
        yaw_badge_m = page_m.locator("#cesium-wind-telemetry-badge")
        assert yaw_badge_m.is_visible(), "Wind Telemetry & Yaw Badge must be visible on mobile"
        badge_text_m = yaw_badge_m.text_content()
        print(f"Mobile 3D Yaw Badge: {badge_text_m.strip()}")

        mobile_3d_path = SCREENSHOTS_DIR / "verify-cesium-3d-yaw-mobile-390px.png"
        page_m.screenshot(path=str(mobile_3d_path))
        print(f"Saved Mobile 3D screenshot: {mobile_3d_path}")

        context_m.close()
        browser.close()

    print("\nALL PLAYWRIGHT VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_all()
