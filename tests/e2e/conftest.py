"""E2E test fixtures for Playwright - session-scoped page."""

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser():
    """Create a session-scoped browser instance."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope="session")
def context(browser):
    """Create a session-scoped context."""
    context = browser.new_context()
    yield context
    context.close()


@pytest.fixture(scope="session")
def page(context):
    """Create a session-scoped page shared across all tests."""
    page = context.new_page()
    yield page


@pytest.fixture(scope="function")
def cleanup_page(page):
    """Reset page state between tests."""
    yield
    try:
        page.evaluate("() => { localStorage.clear(); }")
    except Exception:
        pass


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "http://localhost:5000"
