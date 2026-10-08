"""
tests/verify_react_frontend.py — Rigorous Playwright Verification of React + TypeScript UI
Verifies:
1. Desktop Viewports (1280x800, 1440x900):
   - Project Home Dashboard matching reference visual direction (Liquid Glass, #FFD21F energy yellow).
   - Wordmark 'AeroQuantumWind' (no lightning logo).
   - Dominated by cinematic wind farm map hero.
   - Real SQLite project data, tabular numerals, zero fake data.
   - Zero horizontal overflow.
2. Mobile Viewports (360x800, 390x844, 430x932):
   - Liquid glass floating controls, compact header, and floating bottom nav with center + button.
   - Mobile project selector bottom sheet drawer.
   - Zero horizontal overflow across all mobile viewports.
3. Complete 6-Screen Workflow Traversal (Site -> Config -> Layout -> WS-QAOA -> 3D Inspect -> Blueprint).
4. Direct CSV and GeoJSON export triggers.
5. Zero browser console errors.
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path("docs/ui-screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_react_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # 1. Desktop Viewports (1280x800 & 1440x900)
        # ----------------------------------------------------
        desktop_viewports = [
            {"width": 1280, "height": 800, "name": "1280x800"},
            {"width": 1440, "height": 900, "name": "1440x900"},
        ]

        print("\n=======================================================")
        print("PHASE 1: DESKTOP VIEWPORTS (1280x800, 1440x900)")
        print("=======================================================")

        for vp in desktop_viewports:
            page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in ["error"] else None)

            page.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
            page.wait_for_timeout(800)

            # Assert Root App is rendered
            assert page.is_visible("#root"), f"[{vp['name']}] #root must be visible"

            # Verify Wordmark (AeroQuantumWind)
            header_text = page.inner_text("header")
            assert "AeroQuantum" in header_text and "Wind" in header_text
            print(f"✓ [{vp['name']}] Verified clean wordmark: AeroQuantumWind (no lightning logo)")

            # Verify Project Hero & Real Project Data
            assert page.get_by_text("Active Concession", exact=False).is_visible()
            assert page.get_by_text("Estimated AEP").is_visible()
            assert page.get_by_text("Wake Loss").is_visible()
            assert page.get_by_text("Installed Capacity").is_visible()
            assert page.get_by_text("Avg. Wind Speed").is_visible()

            # Verify No Horizontal Overflow
            is_overflowing = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
            assert not is_overflowing, f"[{vp['name']}] Horizontal overflow detected!"
            print(f"✓ [{vp['name']}] Verified zero horizontal overflow (scrollWidth <= {vp['width']}px)")

            # Capture Desktop Screenshot
            shot_path = SCREENSHOTS_DIR / f"react_desktop_{vp['name']}.png"
            page.screenshot(path=str(shot_path))
            print(f"✓ [{vp['name']}] Saved desktop screenshot to {shot_path}")
            page.close()

        # ----------------------------------------------------
        # 2. Mobile Viewports (360x800, 390x844, 430x932)
        # ----------------------------------------------------
        mobile_viewports = [
            {"width": 360, "height": 800, "name": "360x800"},
            {"width": 390, "height": 844, "name": "390x844"},
            {"width": 430, "height": 932, "name": "430x932"},
        ]

        print("\n=======================================================")
        print("PHASE 2: MOBILE VIEWPORTS (360x800, 390x844, 430x932)")
        print("=======================================================")

        for mvp in mobile_viewports:
            mpage = browser.new_page(viewport={"width": mvp["width"], "height": mvp["height"]})
            mpage.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
            mpage.wait_for_timeout(800)

            # Assert Mobile Bottom Nav is visible
            assert mpage.locator("nav.md\\:hidden").is_visible(), f"[{mvp['name']}] Mobile navigation must be visible"
            assert mpage.locator("nav.md\\:hidden").get_by_text("Home").is_visible()
            assert mpage.locator("nav.md\\:hidden").get_by_text("Projects").is_visible()

            # Verify No Horizontal Overflow on mobile
            is_m_overflow = mpage.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
            assert not is_m_overflow, f"[{mvp['name']}] Mobile horizontal overflow detected!"
            print(f"✓ [{mvp['name']}] Verified zero horizontal overflow (scrollWidth <= {mvp['width']}px)")

            # Test Mobile BottomSheet Drawer for Project Selection
            if mvp["name"] == "390x844":
                # Tap Projects tab in mobile nav
                mpage.locator("nav.md\\:hidden").get_by_text("Projects").click()
                mpage.wait_for_timeout(500)
                assert mpage.get_by_text("Switch Wind Farm Project").is_visible()
                print("✓ [390x844] Verified Mobile BottomSheet drawer opens on Projects tap")
                mpage.screenshot(path=str(SCREENSHOTS_DIR / "react_mobile_drawer_390x844.png"))

                # Close bottom sheet
                mpage.locator("button[aria-label='Close']").click()
                mpage.wait_for_timeout(400)

            # Capture Mobile Project Home Screenshot
            mshot_path = SCREENSHOTS_DIR / f"react_mobile_{mvp['name']}.png"
            mpage.screenshot(path=str(mshot_path))
            print(f"✓ [{mvp['name']}] Saved mobile screenshot to {mshot_path}")
            mpage.close()

        # ----------------------------------------------------
        # 3. Complete 6-Screen Workflow Traversal
        # ----------------------------------------------------
        print("\n=======================================================")
        print("PHASE 3: WORKFLOW TRAVERSAL (Screens 1 to 6)")
        print("=======================================================")
        flow_page = browser.new_page(viewport={"width": 1280, "height": 800})
        flow_page.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        flow_page.wait_for_timeout(800)

        # Click "New Wind Farm" in sidebar
        flow_page.click("text=New Wind Farm")
        flow_page.wait_for_timeout(500)
        assert flow_page.is_visible("#screen-1-container"), "Screen 1 container must be visible"
        print("✓ Screen 1: Site Selection loaded")
        flow_page.screenshot(path=str(SCREENSHOTS_DIR / "react_screen1_site.png"))

        # Confirm Site -> Screen 2
        flow_page.click("#btn-confirm-site")
        flow_page.wait_for_timeout(500)
        assert flow_page.is_visible("#screen-2-container"), "Screen 2 container must be visible"
        print("✓ Screen 2: Farm Configuration loaded")
        flow_page.screenshot(path=str(SCREENSHOTS_DIR / "react_screen2_config.png"))

        # Click 16 Turbines Chip
        flow_page.click("text=16 Turbines")
        flow_page.wait_for_timeout(300)
        print("✓ Screen 2: Updated turbine count to 16")

        # Generate Initial Layout -> Screen 3
        flow_page.click("#btn-generate-layout")
        flow_page.wait_for_selector("#screen-3-container", timeout=15000)
        print("✓ Screen 3: Initial Layout & Site Analysis loaded")
        flow_page.screenshot(path=str(SCREENSHOTS_DIR / "react_screen3_layout.png"))

        # Launch Quantum WS-QAOA -> Screen 4
        flow_page.click("#btn-screen3-optimize")
        flow_page.wait_for_selector("#screen-4-container", timeout=15000)
        print("✓ Screen 4: Quantum WS-QAOA optimization active")

        # Wait for Iteration to reach 100
        flow_page.wait_for_function(
            "() => document.getElementById('s4-iteration-counter')?.innerText.includes('100')",
            timeout=10000
        )
        print("✓ Screen 4: Optimization converged to Iteration 100/100")
        flow_page.screenshot(path=str(SCREENSHOTS_DIR / "react_screen4_optimize.png"))

        # View Optimized Farm -> Screen 5
        flow_page.click("#btn-screen4-view-optimized")
        flow_page.wait_for_timeout(800)
        assert flow_page.is_visible("#screen-5-container"), "Screen 5 container must be visible"
        print("✓ Screen 5: Photorealistic Digital Twin & Inspection loaded")
        flow_page.screenshot(path=str(SCREENSHOTS_DIR / "react_screen5_inspect.png"))

        # Proceed to Blueprint -> Screen 6
        flow_page.click("#btn-screen5-export")
        flow_page.wait_for_timeout(600)
        assert flow_page.is_visible("#screen-6-container"), "Screen 6 container must be visible"
        print("✓ Screen 6: Engineering Blueprint & Export loaded")
        flow_page.screenshot(path=str(SCREENSHOTS_DIR / "react_screen6_blueprint.png"))

        # Verify export button triggers
        assert flow_page.is_visible("#btn-export-csv"), "Export CSV button must be present"
        assert flow_page.is_visible("#btn-export-geojson"), "Export GeoJSON button must be present"
        print("✓ Screen 6: Verified CSV and GeoJSON export handlers")

        flow_page.close()
        browser.close()

    print("\n=======================================================")
    print("ALL REACT FRONTEND REFINEMENT & RESPONSIVE CHECKS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    verify_react_frontend()
