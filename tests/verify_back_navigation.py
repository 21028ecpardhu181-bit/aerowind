import asyncio
import sys
from playwright.async_api import async_playwright

async def run_tests():
    print("=== Testing Mobile & Browser Back Navigation ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Test 1: Mobile Viewport (390 x 844)
        print("\n--- Test 1: Mobile Viewport (390 x 844) ---")
        context = await browser.new_context(viewport={'width': 390, 'height': 844})
        page = await context.new_page()

        # Step A: Load Home
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        await asyncio.sleep(1)

        # Check we are on home screen
        h1_text = await page.locator("h1").inner_text()
        assert "Optimizing" in h1_text, f"Expected home screen h1, got: {h1_text}"
        print("✓ Verified on Home Screen.")

        # Header back button should NOT be visible on home
        header_back = page.locator("#btn-header-back")
        assert not await header_back.is_visible(), "Header back button should not be visible on home screen"
        print("✓ Header back button hidden on Home.")

        # Step B: Click Create New Project -> goes to s1_site
        print("Tapping 'Create New Project'...")
        await page.locator("#btn-project-new").first.click()
        await page.wait_for_selector("#map", state="attached", timeout=10000)
        await asyncio.sleep(1)

        # Verify on Screen 1
        screen1 = page.locator("#screen-1-container")
        assert await screen1.is_visible(), "Expected Screen 1 Site container to be visible"
        print("✓ Successfully navigated to Screen 1 (Site Selection).")

        # Header Back button MUST now be visible
        assert await header_back.is_visible(), "Header back button must be visible on Screen 1"
        print("✓ Header back button is visible on Screen 1.")

        # Screen 1 Search Pill Back button should also be visible
        screen1_back = page.locator("#btn-screen1-back")
        assert await screen1_back.is_visible(), "Screen 1 search pill back button must be visible"
        print("✓ Screen 1 in-pill back button is visible.")

        # Step C: Simulate Mobile Browser Back (page.go_back)
        print("Simulating mobile browser back action (page.go_back)...")
        await page.go_back()
        await asyncio.sleep(1)

        # Should be back on Home Screen!
        assert await page.locator("h1").is_visible(), "Should be back on Home Screen after browser back"
        h1_after_back = await page.locator("h1").inner_text()
        assert "Optimizing" in h1_after_back, f"Expected home screen after back, got: {h1_after_back}"
        print("✓ Browser Back successfully returned to Home screen without leaving the site!")

        # Step D: Test Forward and in-app Header Back button
        print("Navigating forward into Screen 1 again...")
        await page.go_forward()
        await asyncio.sleep(1)
        assert await screen1.is_visible(), "Expected Screen 1 after forward"

        print("Clicking in-app Header Back button (#btn-header-back)...")
        await header_back.click()
        await asyncio.sleep(1)
        assert "Optimizing" in await page.locator("h1").inner_text(), "Expected Home screen after header back button click"
        print("✓ In-app Header Back button successfully returned to Home screen!")

        # Step E: Multi-Step Workflow Back Navigation
        print("\n--- Test 2: Multi-Step Workflow History (Home -> S1 -> S2 -> Back to S1) ---")
        await page.locator("#btn-project-new").first.click()
        await page.wait_for_selector("#screen-1-container", timeout=10000)
        await asyncio.sleep(1)

        # Confirm Site to go to Screen 2
        print("Confirming Site to enter Screen 2 Config...")
        confirm_btn = page.locator("#btn-confirm-site-peek:visible, #btn-confirm-site:visible").first
        await confirm_btn.click()
        await page.wait_for_selector("#screen-2-container", timeout=10000)
        await asyncio.sleep(1)
        print("✓ Entered Screen 2 Config.")

        # Browser Back should go to Screen 1
        print("Pressing browser Back from Screen 2...")
        await page.go_back()
        await asyncio.sleep(1)
        assert await screen1.is_visible(), "Expected Screen 1 after pressing browser back from Screen 2"
        print("✓ Successfully navigated back from Screen 2 to Screen 1!")

        # Another Browser Back should go to Home
        print("Pressing browser Back from Screen 1...")
        await page.go_back()
        await asyncio.sleep(1)
        assert "Optimizing" in await page.locator("h1").inner_text(), "Expected Home screen after 2nd browser back"
        print("✓ Successfully navigated back from Screen 1 to Home!")

        # Step F: Project Dashboard Back Navigation
        print("\n--- Test 3: Project Dashboard Back Navigation ---")
        # Tap bottom nav Projects tab
        projects_tab = page.locator("#btn-mobile-nav-projects")
        await projects_tab.click()
        await asyncio.sleep(1)

        # Should be on Dashboard
        dashboard_back = page.locator("#btn-dashboard-back")
        assert await dashboard_back.is_visible(), "Expected Dashboard Back button to be visible"
        print("✓ Entered Project Dashboard. Found Dashboard Back button.")

        print("Clicking Dashboard Back button...")
        await dashboard_back.click()
        await asyncio.sleep(1)
        assert "Optimizing" in await page.locator("h1").inner_text(), "Expected Home screen after Dashboard back button"
        print("✓ Dashboard Back button successfully returned to Home screen!")

        await context.close()
        await browser.close()

    print("\n✅ ALL BACK NAVIGATION & HISTORY TESTS PASSED PERFECTLY!")

if __name__ == '__main__':
    asyncio.run(run_tests())
