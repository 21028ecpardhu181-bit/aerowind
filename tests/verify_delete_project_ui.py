"""
tests/verify_delete_project_ui.py — Verification for Project Deletion in Dashboard, Cards & Sidebar
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path("docs/ui-screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # TEST 1: DESKTOP (1280x800)
        # ----------------------------------------------------
        print("[1/3] Testing Desktop Viewport (1280x800)...")
        page_desktop = browser.new_page(viewport={"width": 1280, "height": 800})
        page_desktop.goto("http://127.0.0.1:8008/app#dashboard", wait_until="networkidle")
        page_desktop.wait_for_timeout(1500)

        # Check that Dashboard rendered
        assert page_desktop.is_visible("h3:has-text('Recent Projects')"), "Recent Projects section must be visible on Desktop"
        print("  - Recent Projects section visible")

        # Check for delete buttons on project cards
        delete_btns = page_desktop.locator("button[id^='btn-delete-project-']")
        btn_count = delete_btns.count()
        print(f"  - Found {btn_count} delete buttons in Recent Projects list")
        assert btn_count > 0, "At least one project delete button should exist"

        # Check for hero banner delete button
        hero_delete = page_desktop.locator("#btn-delete-active-project")
        assert hero_delete.is_visible(), "Hero banner Delete button should be visible"
        print("  - Active project hero Delete button visible")

        # Take desktop screenshot before interaction
        desktop_path = SCREENSHOTS_DIR / "dashboard_delete_option_desktop.png"
        page_desktop.screenshot(path=str(desktop_path))
        print(f"  - Desktop screenshot saved: {desktop_path}")

        # Click the first delete button to open the confirmation modal
        first_delete_btn = delete_btns.first
        first_delete_btn.click()
        page_desktop.wait_for_timeout(500)

        # Verify Apple Liquid Glass modal is visible
        modal_title = page_desktop.locator("text=Delete Project?")
        assert modal_title.is_visible(), "Confirmation modal 'Delete Project?' must be visible"
        cancel_btn = page_desktop.locator("#btn-cancel-delete-project")
        confirm_btn = page_desktop.locator("#btn-confirm-delete-project")
        assert cancel_btn.is_visible() and confirm_btn.is_visible(), "Cancel and Delete buttons must exist in modal"
        print("  - Confirmation modal displayed with Delete Project? title and action buttons")

        # Take screenshot of the confirmation modal
        modal_path = SCREENSHOTS_DIR / "dashboard_delete_modal_desktop.png"
        page_desktop.screenshot(path=str(modal_path))
        print(f"  - Modal screenshot saved: {modal_path}")

        # Test Cancel
        cancel_btn.click()
        page_desktop.wait_for_timeout(500)
        assert not modal_title.is_visible(), "Modal must be dismissed after clicking Cancel"
        print("  - Cancel button successfully dismisses confirmation modal")

        # ----------------------------------------------------
        # TEST 2: MOBILE (390x844)
        # ----------------------------------------------------
        print("[2/3] Testing Mobile Viewport (390x844)...")
        page_mobile = browser.new_page(viewport={"width": 390, "height": 844})
        page_mobile.goto("http://127.0.0.1:8008/app#dashboard", wait_until="networkidle")
        page_mobile.wait_for_timeout(1500)

        # Verify hero banner and recent projects are visible on mobile
        assert page_mobile.is_visible("h3:has-text('Recent Projects')"), "Recent Projects section must be visible on Mobile"
        mobile_delete_btns = page_mobile.locator("button[id^='btn-delete-project-']")
        mobile_btn_count = mobile_delete_btns.count()
        print(f"  - Found {mobile_btn_count} delete buttons on mobile")
        assert mobile_btn_count > 0, "Delete buttons must be visible on mobile"

        # Take mobile screenshot
        mobile_path = SCREENSHOTS_DIR / "dashboard_delete_option_mobile.png"
        page_mobile.screenshot(path=str(mobile_path))
        print(f"  - Mobile screenshot saved: {mobile_path}")

        # Test opening modal on mobile
        mobile_delete_btns.first.click()
        page_mobile.wait_for_timeout(500)
        assert page_mobile.is_visible("text=Delete Project?"), "Mobile confirmation modal must appear"
        
        mobile_modal_path = SCREENSHOTS_DIR / "dashboard_delete_modal_mobile.png"
        page_mobile.screenshot(path=str(mobile_modal_path))
        print(f"  - Mobile modal screenshot saved: {mobile_modal_path}")

        # Cancel on mobile
        page_mobile.locator("#btn-cancel-delete-project").click()
        page_mobile.wait_for_timeout(400)

        # Test Clear Drafts if button present
        clear_drafts_btn = page_mobile.locator("#btn-clear-drafts")
        if clear_drafts_btn.count() > 0 and clear_drafts_btn.is_visible():
            print("  - Testing Clear Drafts modal on mobile...")
            clear_drafts_btn.click()
            page_mobile.wait_for_timeout(500)
            assert page_mobile.is_visible("text=Clear All Draft Projects?"), "Clear Drafts modal must appear"
            clear_drafts_modal_path = SCREENSHOTS_DIR / "dashboard_clear_drafts_modal_mobile.png"
            page_mobile.screenshot(path=str(clear_drafts_modal_path))
            print(f"  - Clear drafts modal screenshot saved: {clear_drafts_modal_path}")
            page_mobile.locator("#btn-cancel-clear-drafts").click()
            page_mobile.wait_for_timeout(400)

        browser.close()
        print("[3/3] All Playwright UI tests passed successfully!")

if __name__ == "__main__":
    run_verification()
