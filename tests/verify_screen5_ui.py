"""
tests/verify_screen5_ui.py — Playwright Verification for Screen 5: Optimized 3D Wind Farm.
Tests mobile-first layout (390px) and desktop layout (1280px), hero map, wind simulation canvas,
interactive Before/After toggle, turbine inspector with navigation and selection, layout comparison table,
and primary action navigation to Screen 6.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_screen5():
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # =====================================================================
        # 1. MOBILE VIEWPORT TEST (390 x 844) — Primary Target
        # =====================================================================
        print("\n--- Testing Mobile Viewport (390 x 844) ---")
        context_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        )
        page_m = context_mobile.new_page()
        page_m.on("pageerror", lambda err: errors.append(f"[Mobile Error] {err}"))
        page_m.on("console", lambda msg: print(f"[Browser Console {msg.type}] {msg.text}") if msg.type in ["error", "warning"] else None)

        page_m.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        page_m.wait_for_selector("#btn-confirm-site", timeout=10000)
        time.sleep(1.0)

        # Screen 1 -> Screen 2
        print("Screen 1 -> Screen 2: Confirming site...")
        page_m.locator("#btn-confirm-site").click()
        page_m.wait_for_selector("#screen-2-container", state="visible", timeout=10000)
        time.sleep(1.0)

        # Screen 2 -> Screen 3
        print("Screen 2 -> Screen 3: Generating initial layout...")
        page_m.locator("#btn-generate-layout").click()
        page_m.wait_for_selector("#screen-3-container", state="visible", timeout=10000)
        time.sleep(1.5)

        # Screen 3 -> Screen 4
        print("Screen 3 -> Screen 4: Clicking OPTIMIZE WITH QAOA...")
        page_m.locator("#btn-screen3-optimize").click()
        page_m.wait_for_selector("#screen-4-container", state="visible", timeout=10000)

        # Screen 4: Wait for simulation to finish and click VIEW OPTIMIZED LAYOUT
        print("Screen 4: Waiting for QAOA simulation completion...")
        page_m.wait_for_selector("#btn-screen4-view-optimized:not([disabled])", timeout=15000)
        time.sleep(1.0)

        # Screen 4 -> Screen 5
        print("Screen 4 -> Screen 5: Clicking VIEW OPTIMIZED LAYOUT...")
        page_m.locator("#btn-screen4-view-optimized").click()
        page_m.wait_for_selector("#screen-5-container", state="visible", timeout=10000)
        time.sleep(1.5)

        # 1. Verify Stepper and Sub-header
        step_pill = page_m.locator("#mobile-step-pill").text_content()
        print(f"Step Pill: {step_pill.strip()}")
        assert "Step 5/6" in step_pill, f"Expected Step 5/6, got: {step_pill}"

        ind_text = page_m.locator("#s5-indicator-text").text_content()
        print(f"Site Indicator: {ind_text.strip()}")
        assert "QAOA" in ind_text, "Site indicator should mention QAOA"

        # 2. Verify Map & Canvas
        map_elem = page_m.locator("#screen5-map")
        assert map_elem.is_visible(), "Screen 5 map container must be visible"

        canvas_elem = page_m.locator("#screen5-canvas")
        assert canvas_elem.is_visible(), "Screen 5 aerodynamic canvas must be visible"

        # 3. Verify Wind Vector & Speed Legend
        wind_vector = page_m.locator("#s5-wind-vector-text").text_content()
        print(f"Wind Vector: {wind_vector.strip()}")
        assert "Wind Direction" in wind_vector, "Wind direction vector must be displayed"

        legend = page_m.locator("#s5-wind-speed-legend")
        assert legend.is_visible(), "Wind speed legend must be visible"

        # 4. Verify Floating Controls
        btn_before = page_m.locator("#s5-btn-before")
        btn_opt = page_m.locator("#s5-btn-optimized")
        assert btn_before.is_visible() and btn_opt.is_visible(), "Before/Optimized segmented toggle must be visible"
        assert "active" in (btn_opt.get_attribute("class") or ""), "Optimized toggle button should be active by default"

        # 5. Capture Mobile Map Collapsed Screenshot
        mobile_path = SCREENSHOTS_DIR / "screen5-mobile-390px.png"
        page_m.screenshot(path=str(mobile_path))
        print(f"Saved mobile screenshot: {mobile_path}")

        # 6. Verify Bottom Sheet Peek Chips Row
        peek_turbines = page_m.locator("#s5-peek-turbines").text_content()
        peek_aep = page_m.locator("#s5-peek-aep").text_content()
        peek_wake = page_m.locator("#s5-peek-wake-loss").text_content()
        print(f"Peek row: Turbines={peek_turbines}, AEP={peek_aep}, Wake Loss={peek_wake}")
        assert peek_turbines and peek_aep and peek_wake, "Peek row chips must display values"

        # 7. Expand Bottom Sheet
        print("Expanding bottom sheet...")
        page_m.locator("#s5-panel-toggle").click()
        time.sleep(0.5)

        # 8. Verify Layout Telemetry Card
        meta_aep = page_m.locator("#s5-meta-aep").text_content()
        meta_wake = page_m.locator("#s5-meta-wake-loss").text_content()
        meta_spacing = page_m.locator("#s5-meta-avg-spacing").text_content()
        print(f"Telemetry Card: AEP={meta_aep}, Wake Loss={meta_wake}, Spacing={meta_spacing}")
        assert "GWh" in meta_aep, "AEP must be formatted in GWh/year"
        assert "%" in meta_wake, "Wake loss must be formatted in %"

        # 9. Verify Interactive Turbine Inspector Card
        inspector_name = page_m.locator("#s5-inspector-name").text_content()
        inspector_out = page_m.locator("#s5-inspector-output").text_content()
        inspector_near = page_m.locator("#s5-inspector-nearest").text_content()
        print(f"Turbine Inspector: Name={inspector_name}, Output={inspector_out}, Nearest={inspector_near}")
        assert "Turbine" in inspector_name, "Inspector must display Turbine name"
        assert "MW" in inspector_out, "Estimated Output must be in MW"

        # Test Stepper Next Turbine
        print("Testing Stepper Next Turbine...")
        page_m.locator("#btn-s5-next-turbine").click()
        time.sleep(0.3)
        inspector_name_next = page_m.locator("#s5-inspector-name").text_content()
        print(f"After next button: {inspector_name_next}")

        # 10. Verify Layout Comparison Table
        comp_aep = page_m.locator("#s5-comp-opt-aep").text_content()
        comp_aep_badge = page_m.locator("#s5-comp-aep-badge").text_content()
        comp_wake = page_m.locator("#s5-comp-opt-wake").text_content()
        comp_wake_badge = page_m.locator("#s5-comp-wake-badge").text_content()
        print(f"Comparison Table: AEP={comp_aep} ({comp_aep_badge}), Wake={comp_wake} ({comp_wake_badge})")
        assert "+" in comp_aep_badge, "AEP improvement badge must show positive gain"

        # Capture Mobile Inspector Expanded Screenshot
        mobile_inspector_path = SCREENSHOTS_DIR / "screen5-mobile-inspector-390px.png"
        page_m.screenshot(path=str(mobile_inspector_path))
        print(f"Saved mobile inspector screenshot: {mobile_inspector_path}")

        # 11. Test Before / After Toggle
        print("Testing Before / After toggle...")
        page_m.locator("#s5-btn-before").click()
        time.sleep(0.4)
        assert "active" in (page_m.locator("#s5-btn-before").get_attribute("class") or "")

        page_m.locator("#s5-btn-optimized").click()
        time.sleep(0.4)
        assert "active" in (page_m.locator("#s5-btn-optimized").get_attribute("class") or "")

        # 12. Test Primary Action: EXPORT BLUEPRINT -> Screen 6
        print("Testing primary action: EXPORT BLUEPRINT...")
        page_m.locator("#btn-screen5-export").click()
        page_m.wait_for_selector("#screen-6-container", state="visible", timeout=10000)
        time.sleep(0.5)

        s6_header = page_m.locator("#screen-6-container").text_content()
        assert "Screen 6" in s6_header, "Should successfully advance to Screen 6 placeholder"
        print("Screen 6 reached successfully!")

        # Back to Screen 5
        page_m.locator("#screen-6-container button.btn-sub-back").click()
        page_m.wait_for_selector("#screen-5-container", state="visible", timeout=10000)
        time.sleep(0.5)

        context_mobile.close()

        # =====================================================================
        # 2. DESKTOP VIEWPORT TEST (1280 x 800)
        # =====================================================================
        print("\n--- Testing Desktop Viewport (1280 x 800) ---")
        context_desktop = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page_d = context_desktop.new_page()
        page_d.on("pageerror", lambda err: errors.append(f"[Desktop Error] {err}"))

        page_d.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        time.sleep(0.5)

        # Fast forward to Screen 5 via app methods or buttons
        page_d.locator("#btn-confirm-site").click()
        page_d.wait_for_selector("#screen-2-container", state="visible")
        page_d.locator("#btn-generate-layout").click()
        page_d.wait_for_selector("#screen-3-container", state="visible")
        time.sleep(1.5)

        page_d.locator("#btn-screen3-optimize").click()
        page_d.wait_for_selector("#screen-4-container", state="visible")
        page_d.wait_for_selector("#btn-screen4-view-optimized:not([disabled])", timeout=15000)
        page_d.locator("#btn-screen4-view-optimized").click()
        page_d.wait_for_selector("#screen-5-container", state="visible")
        page_d.wait_for_selector("#screen5-map .leaflet-tile-loaded", timeout=10000)
        page_d.wait_for_timeout(2000)

        # On desktop, the side analysis panel is visible
        assert page_d.locator("#screen-5-sheet").is_visible(), "Analysis sidebar must be visible on desktop"
        assert page_d.locator("#s5-turbine-inspector").is_visible(), "Turbine inspector must be visible on desktop"

        desktop_path = SCREENSHOTS_DIR / "screen5-desktop-1280px.png"
        page_d.screenshot(path=str(desktop_path))
        print(f"Saved desktop screenshot: {desktop_path}")

        context_desktop.close()
        browser.close()

    if errors:
        print("\nERRORS ENCOUNTERED:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("\nAll Screen 5 Playwright UI checks PASSED successfully!")

if __name__ == "__main__":
    verify_screen5()
