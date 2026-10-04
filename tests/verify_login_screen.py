"""
tests/verify_login_screen.py — Verification of Exact Login / Onboarding UI matching user reference mockup.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "ui-screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. MOBILE VERIFICATION (390 x 844) - iPhone 14
        print("\n--- Testing Login / Create Account Modal on Mobile (390 x 844) ---")
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = context.new_page()

        page.goto("http://127.0.0.1:8000/app", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)

        # Open Auth Modal
        page.click("#btn-open-auth")
        page.wait_for_timeout(500)
        assert page.is_visible("#auth-modal"), "Auth modal should be visible"
        assert page.is_visible("#auth-login-view"), "Login sheet view should be visible"

        # Capture Create Account screenshot
        mobile_create_path = SCREENSHOTS_DIR / "login_create_account_mobile.png"
        page.screenshot(path=str(mobile_create_path))
        print(f"✓ Saved Create Account screenshot: {mobile_create_path}")

        # Switch to Welcome / Onboarding Screen (matching left phone)
        page.evaluate("() => window.openAuthModal('welcome')")
        page.wait_for_timeout(500)
        assert page.is_visible("#auth-welcome-view"), "Welcome onboarding view should be visible"

        mobile_welcome_path = SCREENSHOTS_DIR / "login_welcome_onboarding_mobile.png"
        page.screenshot(path=str(mobile_welcome_path))
        print(f"✓ Saved Welcome Onboarding screenshot: {mobile_welcome_path}")

        # Click GET STARTED -> returns to Create Account
        page.click("#btn-welcome-get-started")
        page.wait_for_timeout(400)
        assert page.is_visible("#auth-login-view"), "Should transition back to login view"

        # Toggle to Log In mode
        page.click("#btn-toggle-auth-mode")
        page.wait_for_timeout(300)
        assert page.inner_text("#auth-form-title") == "Engineer Workspace", "Title should switch to Engineer Workspace"

        # Fill credentials & submit login
        page.fill("#auth-email-input", "engineer1@aeroquantum.com")
        page.fill("#auth-password-input", "securepassword123")
        page.click("#btn-auth-submit")

        # Wait for toast and modal close
        page.wait_for_timeout(1200)
        assert not page.is_visible("#auth-modal"), "Modal should close on successful login"
        header_text = page.inner_text("#header-user-label")
        print(f"✓ Logged in successfully! Header shows: {header_text}")
        assert header_text == "engineer1", f"Header should show 'engineer1', got '{header_text}'"

        # 2. DESKTOP VERIFICATION (1280 x 800)
        print("\n--- Testing Login / Create Account Modal on Desktop (1280 x 800) ---")
        context_dt = browser.new_context(viewport={"width": 1280, "height": 800})
        page_dt = context_dt.new_page()

        page_dt.goto("http://127.0.0.1:8000/app", wait_until="domcontentloaded", timeout=15000)
        page_dt.wait_for_timeout(800)

        # Open Auth Modal
        page_dt.click("#btn-open-auth")
        page_dt.wait_for_timeout(500)

        desktop_create_path = SCREENSHOTS_DIR / "login_create_account_desktop.png"
        page_dt.screenshot(path=str(desktop_create_path))
        print(f"✓ Saved Desktop Create Account screenshot: {desktop_create_path}")

        browser.close()
        print("\nALL LOGIN & ONBOARDING TESTS PASSED!")

if __name__ == "__main__":
    verify_login()
