"""
tests/verify_screen1_ui.py — Playwright Verification for Screen 1: Site Selection.
Tests both Mobile (390px viewport) and Desktop (1280px viewport).
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_screen1():
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
        page_m.wait_for_selector("#map", timeout=10000)
        page_m.wait_for_selector("#btn-confirm-site", timeout=10000)
        
        # Wait a moment for leaflet tiles & polygon to render
        time.sleep(2)
        
        # Verify Mobile Elements
        brand_text = page_m.locator(".brand-name").text_content()
        print(f"Brand: {brand_text.strip()}")
        assert "AeroQuantum" in brand_text, "Brand text missing"
        
        loc_text = page_m.locator("#meta-location-name").text_content()
        print(f"Meta Location: {loc_text.strip()}")
        assert "Kanyakumari" in loc_text, "Default location mismatch"
        
        lat_text = page_m.locator("#meta-latitude").text_content()
        lon_text = page_m.locator("#meta-longitude").text_content()
        print(f"Coordinates: Lat {lat_text.strip()}, Lon {lon_text.strip()}")
        assert "8.0883" in lat_text, "Latitude mismatch"
        assert "77.5385" in lon_text, "Longitude mismatch"
        
        area_text = page_m.locator("#meta-area").text_content()
        print(f"Area: {area_text.strip()}")
        
        # Take initial mobile screenshot
        mobile_screenshot = SCREENSHOTS_DIR / "screen1-mobile-390px.png"
        page_m.screenshot(path=str(mobile_screenshot))
        print(f"Saved mobile screenshot: {mobile_screenshot}")
        
        # Test expanding bottom sheet
        drag_handle = page_m.locator("#mobile-drag-handle")
        if drag_handle.is_visible():
            drag_handle.click()
            time.sleep(0.5)
            mobile_expanded_screenshot = SCREENSHOTS_DIR / "screen1-mobile-expanded-390px.png"
            page_m.screenshot(path=str(mobile_expanded_screenshot))
            print(f"Saved mobile expanded screenshot: {mobile_expanded_screenshot}")
        
        # Test clicking map to select a custom coordinate
        print("Testing map direct click...")
        page_m.mouse.click(200, 300)
        time.sleep(1)
        updated_lat = page_m.locator("#meta-latitude").text_content()
        print(f"Latitude after map click: {updated_lat.strip()}")
        
        # Test searching a location
        print("Testing site search input...")
        search_input = page_m.locator("#map-search-input")
        search_input.fill("Jaisalmer, Rajasthan")
        search_input.press("Enter")
        time.sleep(2)
        
        search_site_title = page_m.locator("#meta-location-name").text_content()
        print(f"Site after search: {search_site_title.strip()}")
        assert "Jaisalmer" in search_site_title, "Search failed to select Jaisalmer"
        
        # Test Confirm Site Button
        print("Testing Confirm Site button click...")
        page_m.locator("#btn-confirm-site").click()
        time.sleep(1)
        
        # Verify screen 2 container becomes visible
        screen2_display = page_m.locator("#screen-2-container").is_visible()
        print(f"Screen 2 container visible after confirm: {screen2_display}")
        assert screen2_display, "Screen 2 not visible after confirm"
        
        context_mobile.close()
        
        # 2. DESKTOP VIEWPORT TEST (1280 x 800)
        print("\n--- Testing Desktop Viewport (1280 x 800) ---")
        context_desktop = browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        page_d = context_desktop.new_page()
        page_d.on("pageerror", lambda err: errors.append(f"[Desktop Error] {err}"))
        
        page_d.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        page_d.wait_for_selector("#map", timeout=10000)
        time.sleep(2)
        
        # Verify Desktop Stepper
        step_items = page_d.locator(".step-item").count()
        print(f"Desktop Stepper Steps count: {step_items}")
        assert step_items == 6, f"Expected 6 workflow steps, got {step_items}"
        
        # Take desktop screenshot
        desktop_screenshot = SCREENSHOTS_DIR / "screen1-desktop-1280px.png"
        page_d.screenshot(path=str(desktop_screenshot))
        print(f"Saved desktop screenshot: {desktop_screenshot}")
        
        context_desktop.close()
        browser.close()
        
    if errors:
        print("\nERRORS ENCOUNTERED:")
        for e in errors:
            print(" - ", e)
        sys.exit(1)
    else:
        print("\nAll Screen 1 Playwright tests passed successfully!")

if __name__ == "__main__":
    verify_screen1()
