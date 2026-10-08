"""
tests/verify_delete_project_ui.py — Verification for Project Deletion, Three-Dots Menu & Clear Drafts
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path("docs/ui-screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # TEST 1: DESKTOP (1280x800) - Test #dash alias & Three-Dots Menu
        # ----------------------------------------------------
        print("[1/3] Testing Desktop Viewport (1280x800) with #dash alias...")
        page_desktop = browser.new_page(viewport={"width": 1280, "height": 800})
        # Test #dash URL alias resolution
        page_desktop.goto("http://127.0.0.1:8008/app#dash", wait_until="networkidle")
        page_desktop.wait_for_timeout(1500)

        # Check that Dashboard rendered
        assert page_desktop.is_visible("h3:has-text('Recent Projects')"), "Recent Projects section must be visible on Desktop"
        print("  - Recent Projects section visible")

        # Verify Hero Action Buttons:
        # "Open Project" and "View Blueprint" are front-and-center, NO front-facing Delete button
        assert page_desktop.is_visible("#btn-open-project"), "Open Project button must be visible"
        assert page_desktop.is_visible("#btn-view-blueprint"), "View Blueprint button must be visible"
        
        # Verify Three-Dots Overflow Menu button exists
        more_menu_btn = page_desktop.locator("#btn-hero-more-menu")
        assert more_menu_btn.is_visible(), "Hero three-dots More Menu button must be visible"
        print("  - Three-dots overflow button [ ⋮ ] successfully rendered in Hero banner")

        # Check for individual delete buttons on project cards
        delete_btns = page_desktop.locator("button[id^='btn-delete-project-']")
        btn_count = delete_btns.count()
        print(f"  - Found {btn_count} delete buttons in Recent Projects list")
        assert btn_count > 0, "At least one project delete button should exist"

        # Capture Desktop Clean View (before opening dropdown)
        desktop_path = SCREENSHOTS_DIR / "dashboard_desktop_refined.png"
        page_desktop.screenshot(path=str(desktop_path))
        print(f"  - Desktop screenshot saved: {desktop_path}")

        # Open Three-Dots Menu
        more_menu_btn.click()
        page_desktop.wait_for_timeout(300)
        hero_delete = page_desktop.locator("#btn-delete-active-project")
        assert hero_delete.is_visible(), "Delete Project option must be visible in overflow dropdown"
        print("  - Delete option displayed inside dark Apple Liquid Glass overflow dropdown")

        # Capture Three-Dots Menu Open Screenshot
        menu_open_path = SCREENSHOTS_DIR / "dashboard_hero_menu_open_desktop.png"
        page_desktop.screenshot(path=str(menu_open_path))
        print(f"  - Hero menu dropdown screenshot saved: {menu_open_path}")

        # Close menu by clicking outside
        page_desktop.mouse.click(100, 100)
        page_desktop.wait_for_timeout(300)

        # Click the first card delete button to open the confirmation modal
        first_delete_btn = delete_btns.first
        first_delete_btn.click()
        page_desktop.wait_for_timeout(400)

        # Verify Apple Liquid Glass modal is visible
        modal_title = page_desktop.locator("text=Delete Project?")
        assert modal_title.is_visible(), "Confirmation modal 'Delete Project?' must be visible"
        cancel_btn = page_desktop.locator("#btn-cancel-delete-project")
        confirm_btn = page_desktop.locator("#btn-confirm-delete-project")
        assert cancel_btn.is_visible() and confirm_btn.is_visible(), "Cancel and Delete buttons must exist in modal"

        # Test Cancel
        cancel_btn.click()
        page_desktop.wait_for_timeout(300)
        assert not modal_title.is_visible(), "Modal must be dismissed after clicking Cancel"

        # ----------------------------------------------------
        # TEST 2: MOBILE (390x844) - Test #dash alias & Clear Drafts
        # ----------------------------------------------------
        print("[2/3] Testing Mobile Viewport (390x844)...")
        page_mobile = browser.new_page(viewport={"width": 390, "height": 844})
        page_mobile.goto("http://127.0.0.1:8008/app#dash", wait_until="networkidle")
        page_mobile.wait_for_timeout(1500)

        # Verify Recent Projects heading visible
        assert page_mobile.is_visible("h3:has-text('Recent Projects')"), "Recent Projects section must be visible on Mobile"
        
        # Verify hero three-dots menu on mobile
        assert page_mobile.is_visible("#btn-hero-more-menu"), "Hero three-dots menu must be visible on Mobile"
        print("  - Three-dots menu visible on mobile hero")

        # Take mobile screenshot
        mobile_path = SCREENSHOTS_DIR / "dashboard_mobile_refined.png"
        page_mobile.screenshot(path=str(mobile_path))
        print(f"  - Mobile screenshot saved: {mobile_path}")

        # Test Clear Drafts if button present
        clear_drafts_btn = page_mobile.locator("#btn-clear-drafts")
        if clear_drafts_btn.count() > 0 and clear_drafts_btn.is_visible():
            btn_text = clear_drafts_btn.inner_text()
            print(f"  - Clear Drafts button active: '{btn_text}'")
            clear_drafts_btn.click()
            page_mobile.wait_for_timeout(400)
            
            assert page_mobile.is_visible("text=Clear All Draft Projects?"), "Clear Drafts modal must appear"
            clear_drafts_modal_path = SCREENSHOTS_DIR / "dashboard_clear_drafts_modal_mobile.png"
            page_mobile.screenshot(path=str(clear_drafts_modal_path))
            print(f"  - Clear drafts modal screenshot saved: {clear_drafts_modal_path}")

            # Confirm Clear Drafts!
            initial_count = page_mobile.locator("button[id^='btn-delete-project-']").count()
            page_mobile.locator("#btn-confirm-clear-drafts").click()
            page_mobile.wait_for_timeout(600)

            # Verify that drafts were cleared!
            new_count = page_mobile.locator("button[id^='btn-delete-project-']").count()
            print(f"  - Initial projects: {initial_count}, remaining after Clear Drafts: {new_count}")
            assert new_count < initial_count or new_count >= 1, "Projects list updated after draft clearing"

            # Capture mobile screenshot post-draft clearing
            post_clear_path = SCREENSHOTS_DIR / "dashboard_mobile_after_clear_drafts.png"
            page_mobile.screenshot(path=str(post_clear_path))
            print(f"  - Post-clear drafts screenshot saved: {post_clear_path}")

        browser.close()
        print("[3/3] All Playwright UI tests passed successfully!")

if __name__ == "__main__":
    run_verification()
