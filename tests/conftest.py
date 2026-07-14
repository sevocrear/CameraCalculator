"""Pytest configuration."""

import asyncio
import os

import httpx
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL.rstrip("/")


class ASGITestClient:
    """Small synchronous facade over HTTPX's asynchronous ASGI transport."""

    def __init__(self):
        from cctv_lens_calc.api.main import create_app

        self._app = create_app()

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                timeout=30.0,
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self.request("POST", path, **kwargs)


@pytest.fixture(scope="session")
def asgi_client() -> ASGITestClient:
    """In-process API client for deterministic unit and smoke tests."""
    return ASGITestClient()


@pytest.fixture(scope="session")
def httpx_client(base_url: str):
    """Live HTTP client used only by browser integration tests."""
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
