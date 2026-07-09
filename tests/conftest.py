"""Pytest configuration."""

import os

import pytest

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def httpx_client(base_url):
    import httpx

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def browser_context_args():
    return {"viewport": {"width": 1280, "height": 900}}


@pytest.fixture(scope="session")
def playwright_browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(playwright_browser, base_url):
    pg = playwright_browser.new_page()
    pg.goto(base_url + "/", wait_until="domcontentloaded")
    pg.wait_for_selector("#metricPpm", timeout=15000)
    pg.wait_for_function(
        "() => window.CctvLensApp && window.CctvLensApp.getMetricPpm() !== '—'",
        timeout=15000,
    )
    yield pg
    pg.close()
