"""
tests/verify_screen4_ui.py — Playwright Verification for Screen 4: QAOA Quantum Optimization.
Tests mobile-first layout (390px), QAOA simulation status, progress animation, QUBO decision matrix,
abstract quantum circuit diagram, constraints verification, and transition to Screen 5.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_screen4():
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
        if page_m.is_visible("#btn-project-new"):
            page_m.click("#btn-project-new")
            page_m.wait_for_timeout(1000)
        page_m.wait_for_selector("#btn-confirm-site", timeout=10000)
        time.sleep(1.0)

        # Screen 1 -> Screen 2
        print("Screen 1 -> Screen 2: Confirming site...")
        page_m.locator("#btn-confirm-site-peek:visible, #btn-confirm-site").first.click(force=True)
        page_m.wait_for_selector("#screen-2-container", state="visible", timeout=10000)
        time.sleep(1.0)

        # Screen 2 -> Screen 3
        print("Screen 2 -> Screen 3: Generating initial layout...")
        page_m.locator("#btn-generate-layout").click(force=True)
        page_m.wait_for_selector("#screen-3-container", state="visible", timeout=10000)
        time.sleep(1.5)

        # Screen 3 -> Screen 4
        print("Screen 3 -> Screen 4: Clicking OPTIMIZE WITH QAOA...")
        page_m.locator("#btn-screen3-optimize").click(force=True)
        page_m.wait_for_selector("#screen-4-container", state="visible", timeout=10000)

        # 1. Verify Stepper and Sub-header
        step_pill = page_m.locator("#mobile-step-pill").text_content()
        print(f"Step Pill: {step_pill.strip()}")
        assert "Step 4/6" in step_pill, "Mobile step pill should show Step 4/6"

        ind_text = page_m.locator("#s4-indicator-text").text_content()
        print(f"Site Indicator: {ind_text.strip()}")
        assert any(name in ind_text for name in ["Bommuru", "Kanyakumari", "Anantapur", "Wind"]), "Site name should persist in Screen 4 header"

        # 2. Wait for QAOA optimization simulation to complete
        print("Waiting for QAOA simulation to complete...")
        page_m.wait_for_selector("#s4-status-card:not(.running)", timeout=15000)
        time.sleep(1.0)

        status_title = page_m.locator("#s4-status-title").text_content()
        print(f"Status Title: {status_title.strip()}")
        assert "Best feasible layout identified" in status_title, "Should show Best feasible layout identified"

        # 3. Verify Progress Bar
        counter_text = page_m.locator("#s4-iteration-counter").text_content()
        print(f"Iteration Counter: {counter_text.strip()}")
        assert "100 / 100" in counter_text or "100%" in counter_text, "Progress should reach 100%"

        # 4. Verify KPI Stats Trio
        kpi_cur = page_m.locator("#s4-kpi-current-aep").text_content()
        kpi_best = page_m.locator("#s4-kpi-best-aep").text_content()
        kpi_imp = page_m.locator("#s4-kpi-improvement").text_content()
        print(f"KPI Trio: Current={kpi_cur.strip()} | Best={kpi_best.strip()} | Improvement={kpi_imp.strip()}")
        assert "GWh" in kpi_cur, "Current AEP missing"
        assert "GWh" in kpi_best, "Best AEP missing"
        assert "+" in kpi_imp or "%" in kpi_imp, "Improvement percentage missing"

        # 5. Verify QUBO Decision Matrix Grid
        qubo_bits = page_m.locator("#s4-qubo-grid .qubo-bit-box")
        bits_count = qubo_bits.count()
        active_bits = page_m.locator("#s4-qubo-grid .qubo-bit-box.active").count()
        print(f"QUBO Grid: {bits_count} total candidate boxes, {active_bits} active turbine positions")
        assert bits_count >= 16, f"Expected at least 16 candidate boxes, found {bits_count}"
        assert active_bits >= 10, f"Expected at least 10 active turbines in QUBO solution, found {active_bits}"

        # 6. Verify Abstract QAOA Circuit Diagram SVG
        circuit_svg = page_m.locator("#s4-circuit-svg")
        assert circuit_svg.is_visible(), "QAOA circuit SVG diagram must be visible"

        # 7. Verify Constraint Verification Checks
        check_turb = page_m.locator("#s4-check-turbines").text_content()
        check_spac = page_m.locator("#s4-check-spacing").text_content()
        check_boun = page_m.locator("#s4-check-boundary").text_content()
        print(f"Constraints: Turbines={check_turb.strip()} | Spacing={check_spac.strip()} | Boundary={check_boun.strip()}")
        assert "Satisfied" in check_turb, "Turbine count constraint must be satisfied"
        assert "Satisfied" in check_spac, "Minimum spacing constraint must be satisfied"
        assert "Satisfied" in check_boun, "Site boundary constraint must be satisfied"

        # 8. Verify Primary Action Button
        view_opt_btn = page_m.locator("#btn-screen4-view-optimized")
        assert view_opt_btn.is_visible(), "VIEW OPTIMIZED LAYOUT button must be visible"

        # 9. Capture Screen 4 Mobile Screenshot (Top / Overview)
        screenshot_mobile = SCREENSHOTS_DIR / "screen4-mobile-390px.png"
        page_m.screenshot(path=str(screenshot_mobile))
        print(f"Saved mobile screenshot: {screenshot_mobile}")

        # 9b. Scroll down to inspect QUBO matrix, QAOA circuit, and constraints
        page_m.locator("#s4-section-circuit").scroll_into_view_if_needed()
        time.sleep(0.4)
        screenshot_mobile_scrolled = SCREENSHOTS_DIR / "screen4-mobile-scrolled-390px.png"
        page_m.screenshot(path=str(screenshot_mobile_scrolled))
        print(f"Saved mobile scrolled screenshot: {screenshot_mobile_scrolled}")

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
        page_d.wait_for_selector("#btn-project-new:visible, #card-workflow-site:visible", timeout=10000)
        page_d.locator("#btn-project-new:visible, #card-workflow-site:visible").first.click()
        page_d.wait_for_selector("#screen-1-container", timeout=10000)
        time.sleep(1.0)

        # Full navigation: Screen 1 -> 2 -> 3 -> 4
        page_d.locator("#btn-confirm-site-peek:visible, #btn-confirm-site").first.click(force=True)
        page_d.wait_for_selector("#screen-2-container", state="visible", timeout=10000)
        time.sleep(1.0)
        page_d.locator("#btn-generate-layout").click(force=True)
        page_d.wait_for_selector("#screen-3-container", state="visible", timeout=10000)
        time.sleep(1.5)
        page_d.locator("#btn-screen3-optimize").click(force=True)
        page_d.wait_for_selector("#screen-4-container", state="visible", timeout=10000)
        time.sleep(1.5)

        # Capture Desktop Screenshot
        screenshot_desktop = SCREENSHOTS_DIR / "screen4-desktop-1280px.png"
        page_d.screenshot(path=str(screenshot_desktop))
        print(f"Saved desktop screenshot: {screenshot_desktop}")

        # Click Primary Action "VIEW OPTIMIZED LAYOUT" to verify transition to Screen 5
        print("Testing transition to Screen 5 (Inspect Optimized 3D Wind Farm)...")
        page_d.locator("#btn-screen4-view-optimized").click()
        page_d.wait_for_selector("#screen-5-container", state="visible", timeout=5000)
        time.sleep(0.5)
        step_pill_s5 = page_d.locator("#mobile-step-pill").text_content()
        print(f"Transitioned to Step: {step_pill_s5.strip()}")
        assert "Step 5/6" in step_pill_s5, "Should advance to Step 5/6 after clicking View Optimized Layout"

        context_desktop.close()
        browser.close()

    if errors:
        print("\nERRORS ENCOUNTERED:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("\n✅ SCREEN 4 VERIFICATION PASSED ON ALL VIEWPORTS!")

if __name__ == "__main__":
    verify_screen4()
