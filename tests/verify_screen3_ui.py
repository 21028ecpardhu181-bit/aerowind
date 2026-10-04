"""
tests/verify_screen3_ui.py — Playwright Verification for Screen 3: Initial Layout Analysis.
Tests mobile-first layout (390px), map hero, Jensen wake cones, wake conflicts,
telemetry table, SVG wind rose polar chart, bottom sheet interaction, and desktop responsiveness.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_screen3():
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
        time.sleep(2.0) # allow aerodynamic computation and map render

        # 1. Verify Stepper and Sub-header
        step_pill = page_m.locator("#mobile-step-pill").text_content()
        print(f"Step Pill: {step_pill.strip()}")
        assert "Step 3/6" in step_pill, "Mobile step pill should show Step 3/6"

        ind_text = page_m.locator("#s3-indicator-text").text_content()
        print(f"Site Indicator: {ind_text.strip()}")
        assert "Kanyakumari" in ind_text, "Site name should persist in Screen 3 header"

        # 2. Verify Map Hero and Canvas Overlay
        assert page_m.locator("#screen3-map").is_visible(), "Screen 3 Leaflet map must be visible"
        assert page_m.locator("#screen3-canvas").is_visible(), "Screen 3 Canvas overlay must be visible"

        # 3. Verify Floating Wind Vector Indicator & Speed Legend
        assert page_m.locator("#s3-wind-vector-badge").is_visible(), "Wind vector badge must be visible"
        wind_text = page_m.locator("#s3-wind-vector-text").text_content()
        print(f"Wind Vector: {wind_text.strip()}")
        assert "Wind:" in wind_text, "Wind speed and direction text missing"

        assert page_m.locator("#s3-wind-speed-legend").is_visible(), "Aerodynamic speed legend must be visible"

        # 4. Verify Turbine Markers on Leaflet Map
        turbine_pins = page_m.locator(".turbine-map-pin")
        pin_count = turbine_pins.count()
        print(f"Turbine Map Pins rendered: {pin_count}")
        assert pin_count >= 10, f"Expected at least 10 turbine map pins, got {pin_count}"

        # 5. Verify Mobile Peek Chips Row
        peek_turbines = page_m.locator("#s3-peek-turbines").text_content()
        peek_aep = page_m.locator("#s3-peek-aep").text_content()
        peek_wake_loss = page_m.locator("#s3-peek-wake-loss").text_content()
        peek_conflicts = page_m.locator("#s3-peek-conflicts").text_content()
        print(f"Mobile Glance Peek Chips: Turbines={peek_turbines.strip()} | AEP={peek_aep.strip()} | WakeLoss={peek_wake_loss.strip()} | Conflicts={peek_conflicts.strip()}")
        assert peek_turbines.strip() != "", "Peek turbines chip missing"
        assert "GWh" in peek_aep, "Peek AEP should display GWh units"
        assert "%" in peek_wake_loss, "Peek wake loss should display % units"

        # 6. Capture Screen 3 Mobile (Map Hero + Collapsed/Glance Sheet)
        screenshot_mobile_glance = SCREENSHOTS_DIR / "screen3-mobile-390px.png"
        page_m.screenshot(path=str(screenshot_mobile_glance))
        print(f"Saved mobile glance screenshot: {screenshot_mobile_glance}")

        # 7. Expand Bottom Sheet and Verify Engineering Telemetry
        print("Expanding mobile bottom sheet...")
        page_m.locator("#s3-panel-toggle").click()
        time.sleep(0.5)

        meta_gross = page_m.locator("#s3-meta-gross-aep").text_content()
        meta_net = page_m.locator("#s3-meta-net-aep").text_content()
        meta_loss = page_m.locator("#s3-meta-wake-loss").text_content()
        meta_spacing = page_m.locator("#s3-meta-min-spacing").text_content()
        meta_conflicts = page_m.locator("#s3-meta-conflicts-count").text_content()
        print(f"Telemetry Table: Gross={meta_gross.strip()} | Net={meta_net.strip()} | Loss={meta_loss.strip()} | Spacing={meta_spacing.strip()} | Conflicts={meta_conflicts.strip()}")
        assert "GWh" in meta_gross, "Gross AEP missing in telemetry"
        assert "GWh" in meta_net, "Net AEP missing in telemetry"
        assert "%" in meta_loss, "Wake interaction loss missing in telemetry"

        # 8. Verify SVG Wind Rose Polar Radar Chart
        svg_polygons = page_m.locator("#s3-wind-rose-svg polygon")
        poly_count = svg_polygons.count()
        print(f"Wind Rose Polar Petals rendered: {poly_count}")
        assert poly_count >= 16, f"Expected 16 sector petals in SVG wind rose, got {poly_count}"

        # 9. Verify Primary Action Button
        optimize_btn = page_m.locator("#btn-screen3-optimize")
        assert optimize_btn.is_visible(), "OPTIMIZE WITH QAOA button must be visible"

        # 10. Capture Screen 3 Mobile Expanded Bottom Sheet Screenshot
        screenshot_mobile_expanded = SCREENSHOTS_DIR / "screen3-mobile-expanded-390px.png"
        page_m.screenshot(path=str(screenshot_mobile_expanded))
        print(f"Saved mobile expanded screenshot: {screenshot_mobile_expanded}")

        context_mobile.close()

        # =====================================================================
        # 2. DESKTOP VIEWPORT TEST (1280 x 800) — Responsive Architecture
        # =====================================================================
        print("\n--- Testing Desktop Viewport (1280 x 800) ---")
        context_desktop = browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        page_d = context_desktop.new_page()
        page_d.on("pageerror", lambda err: errors.append(f"[Desktop Error] {err}"))

        page_d.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        page_d.wait_for_selector("#btn-confirm-site", timeout=10000)
        time.sleep(1.0)

        # Screen 1 -> Screen 2 -> Screen 3
        page_d.locator("#btn-confirm-site").click()
        page_d.wait_for_selector("#screen-2-container", state="visible", timeout=10000)
        time.sleep(1.0)
        page_d.locator("#btn-generate-layout").click()
        page_d.wait_for_selector("#screen-3-container", state="visible", timeout=10000)
        time.sleep(2.0)

        # Verify Desktop Layout (Side-by-side: Map hero on left, Analysis sidebar on right)
        map_box = page_d.locator(".s3-map-container").bounding_box()
        panel_box = page_d.locator(".s3-analysis-panel").bounding_box()
        print(f"Desktop Map Width: {map_box['width']}px | Analysis Sidebar Width: {panel_box['width']}px")
        assert map_box['width'] > 600, "Desktop map should occupy predominant viewport width"
        assert panel_box['width'] >= 350, "Desktop analysis panel should be displayed as side panel"

        # Capture Desktop Screenshot
        screenshot_desktop = SCREENSHOTS_DIR / "screen3-desktop-1280px.png"
        page_d.screenshot(path=str(screenshot_desktop))
        print(f"Saved desktop screenshot: {screenshot_desktop}")

        # Click Primary Action "OPTIMIZE WITH QAOA" to verify navigation to Screen 4
        print("Testing transition to Screen 4 (QAOA Optimization)...")
        page_d.locator("#btn-screen3-optimize").click()
        page_d.wait_for_selector("#screen-4-container", state="visible", timeout=5000)
        time.sleep(0.5)
        step_pill_s4 = page_d.locator("#mobile-step-pill").text_content()
        print(f"Transitioned to Step: {step_pill_s4.strip()}")
        assert "Step 4/6" in step_pill_s4, "Should advance to Step 4/6 after clicking Optimize"

        context_desktop.close()
        browser.close()

    if errors:
        print("\nERRORS ENCOUNTERED:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("\n✅ SCREEN 3 VERIFICATION PASSED ON ALL VIEWPORTS!")

if __name__ == "__main__":
    verify_screen3()
