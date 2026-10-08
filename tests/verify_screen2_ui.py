"""
tests/verify_screen2_ui.py — Playwright Verification for Screen 2: Farm Configuration.
Tests mobile-first layout (390px), site persistence, capacity validation, controls, and navigation.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_screen2():
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. MOBILE VIEWPORT TEST (390 x 844)
        print("\n--- Testing Mobile Viewport (390 x 844) ---")
        context_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        )
        page_m = context_mobile.new_page()
        page_m.on("pageerror", lambda err: errors.append(f"[Mobile Error] {err}"))

        page_m.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        page_m.wait_for_selector("#btn-confirm-site", timeout=10000)
        time.sleep(1.5)

        # Click Confirm Site in Screen 1
        print("Navigating from Screen 1 to Screen 2...")
        page_m.locator("#btn-confirm-site").click()
        page_m.wait_for_selector("#screen-2-container", state="visible", timeout=10000)
        time.sleep(1)

        # 1. Verify Stepper and Sub-header
        step_pill = page_m.locator("#mobile-step-pill").text_content()
        print(f"Step Pill: {step_pill.strip()}")
        assert "Step 2/6" in step_pill, "Mobile step pill should show Step 2/6"

        ind_text = page_m.locator("#s2-indicator-text").text_content()
        print(f"Site Indicator: {ind_text.strip()}")
        assert "Kanyakumari" in ind_text, "Persisted site name missing in header"
        assert "8.0883" in ind_text, "Persisted latitude missing in header"

        # 2. Verify Persisted Site Metadata Card
        meta_loc = page_m.locator("#s2-meta-location").text_content()
        meta_coords = page_m.locator("#s2-meta-coords").text_content()
        meta_area = page_m.locator("#s2-meta-area").text_content()
        print(f"Persisted Details: {meta_loc.strip()} | {meta_coords.strip()} | {meta_area.strip()}")
        assert "Kanyakumari" in meta_loc, "Site location mismatch"
        assert "8.0883" in meta_coords, "Site coords mismatch"

        # 3. Take Clean Screen 2 Mobile Screenshot
        screenshot_mobile = SCREENSHOTS_DIR / "screen2-mobile-390px.png"
        page_m.screenshot(path=str(screenshot_mobile))
        print(f"Saved mobile screenshot: {screenshot_mobile}")

        # 4. Test Model Change (Select Vestas V110)
        print("Testing turbine model dropdown change...")
        page_m.select_option("#cfg-turbine-model", "vestas-110")
        time.sleep(0.5)
        rotor_val = page_m.locator("#cfg-rotor-diam").input_value()
        hub_val = page_m.locator("#cfg-hub-height").input_value()
        print(f"Updated Specs after Vestas selection: Rotor {rotor_val}m, Hub {hub_val}m")
        assert rotor_val == "110", "Rotor diameter did not sync with Vestas preset"
        assert hub_val == "100", "Hub height did not sync with Vestas preset"

        # 5. Test Real-Time Capacity Alert with High Turbine Count (e.g. 50 turbines)
        print("Testing capacity gate with 50 turbines...")
        page_m.fill("#cfg-turbines-count", "50")
        page_m.locator("#cfg-turbines-count").dispatch_event("input")
        time.sleep(0.8)

        capacity_card = page_m.locator("#cfg-capacity-card")
        card_class = capacity_card.get_attribute("class")
        print(f"Capacity card class with 50 turbines: {card_class}")
        assert "exceeded" in card_class, "Capacity card should be 'exceeded' for 50 turbines"

        clamp_btn = page_m.locator("#btn-clamp-capacity")
        assert clamp_btn.is_visible(), "Clamp capacity button should be visible when capacity is exceeded"

        # Scroll capacity card into view for screenshot
        page_m.evaluate("document.getElementById('cfg-capacity-card').scrollIntoView({ block: 'center' })")
        time.sleep(0.5)

        # Take Capacity Warning Screenshot
        warning_screenshot = SCREENSHOTS_DIR / "screen2-capacity-warning-390px.png"
        page_m.screenshot(path=str(warning_screenshot))
        print(f"Saved capacity warning screenshot: {warning_screenshot}")

        # Click Clamp Button
        print("Clicking clamp capacity button...")
        clamp_btn.click()
        time.sleep(0.8)

        clamped_count = int(page_m.locator("#cfg-turbines-count").input_value())
        print(f"Clamped turbine count: {clamped_count}")
        assert clamped_count < 30, f"Clamped count {clamped_count} is too high for this site"

        card_class_after = capacity_card.get_attribute("class")
        print(f"Capacity card class after clamp: {card_class_after}")
        assert "optimal" in card_class_after, "Capacity card should return to 'optimal' after clamp"

        # 6. Test Wind Direction & Compass
        print("Testing wind direction slider...")
        page_m.fill("#cfg-wind-dir-slider", "225")
        page_m.locator("#cfg-wind-dir-slider").dispatch_event("input")
        time.sleep(0.5)
        wind_badge = page_m.locator("#badge-wind-dir").text_content()
        print(f"Wind Direction Badge: {wind_badge.strip()}")
        assert "225" in wind_badge, "Wind badge did not update to 225°"

        # 7. Test Spacing Chips
        print("Testing spacing chip selection (7D)...")
        page_m.locator('.chip-btn[data-spacing="7"]').click()
        time.sleep(0.5)
        spacing_badge = page_m.locator("#badge-spacing-meters").text_content()
        print(f"Spacing Badge: {spacing_badge.strip()}")
        assert "7D" in spacing_badge, "Spacing badge did not update to 7D"

        # 8. Test Advanced Accordion
        print("Testing advanced accordion toggle...")
        page_m.evaluate("document.getElementById('accordion-advanced-header').scrollIntoView({ block: 'center' })")
        time.sleep(0.5)
        page_m.evaluate("document.getElementById('accordion-advanced-header').click()")
        time.sleep(0.5)
        accordion_wrapper = page_m.locator("#accordion-advanced-wrapper")
        assert "expanded" in accordion_wrapper.get_attribute("class"), "Accordion failed to expand"

        # 9. Test Primary Action: GENERATE INITIAL LAYOUT
        print("Clicking GENERATE INITIAL LAYOUT button...")
        page_m.locator("#btn-generate-layout").click()
        page_m.wait_for_selector("#screen-3-container", state="visible", timeout=10000)
        time.sleep(1)

        screen3_title = page_m.locator("#screen-3-container div").first.text_content()
        print(f"Screen 3 Header: {screen3_title.strip()}")
        assert "Screen 3: Analyze Initial Layout" in screen3_title, "Failed to navigate to Screen 3"

        context_mobile.close()

        # 2. DESKTOP VIEWPORT TEST (1280 x 800)
        print("\n--- Testing Desktop Viewport (1280 x 800) ---")
        context_desktop = browser.new_context(viewport={"width": 1280, "height": 800})
        page_d = context_desktop.new_page()
        page_d.on("pageerror", lambda err: errors.append(f"[Desktop Error] {err}"))

        page_d.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        page_d.wait_for_selector("#btn-confirm-site", timeout=10000)
        time.sleep(1)

        # Confirm site to reach Screen 2
        page_d.locator("#btn-confirm-site").click()
        page_d.wait_for_selector("#screen-2-container", state="visible", timeout=10000)
        time.sleep(1)

        # Verify Desktop Stepper
        step2_active = page_d.locator('.step-item[data-step="2"]').get_attribute("class")
        print(f"Desktop Step 2 class: {step2_active}")
        assert "active" in step2_active, "Desktop step 2 should be active"

        # Desktop Screenshot
        screenshot_desktop = SCREENSHOTS_DIR / "screen2-desktop-1280px.png"
        page_d.screenshot(path=str(screenshot_desktop))
        print(f"Saved desktop screenshot: {screenshot_desktop}")

        context_desktop.close()
        browser.close()

    if errors:
        print("\nERRORS ENCOUNTERED:")
        for e in errors:
            print(" - ", e)
        sys.exit(1)
    else:
        print("\nAll Screen 2 Playwright tests passed successfully!")

if __name__ == "__main__":
    verify_screen2()
