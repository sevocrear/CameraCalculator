"""Playwright UI tests."""

import httpx
import pytest

pytestmark = pytest.mark.ui


def test_page_loads_metrics(page):
    assert page.locator("#metricHfov").inner_text() != "—"
    assert page.locator("#metricPpm").inner_text() != "—"


def test_slider_updates_metrics(page):
    before = page.locator("#metricPpm").inner_text()
    page.locator("#distance").fill("5")
    page.locator("#distance").dispatch_event("input")
    page.wait_for_function(
        "b => document.getElementById('metricPpm').textContent !== b",
        arg=before,
        timeout=5000,
    )
    after = page.locator("#metricPpm").inner_text()
    assert after != before


def test_object_tab_updates_px(page):
    page.locator('.tab[data-id="donut"]').click()
    page.wait_for_function(
        "() => (document.getElementById('metricObjectPx').textContent || '').includes('Пончик')",
        timeout=10000,
    )
    text_donut = page.locator("#metricObjectPx").inner_text()
    page.locator('.tab[data-id="car"]').click()
    page.wait_for_function(
        "() => (document.getElementById('metricObjectPx').textContent || '').includes('Авто')",
        timeout=10000,
    )
    text_car = page.locator("#metricObjectPx").inner_text()
    assert text_donut != text_car
    assert "px" in text_car


def test_2d_canvas_has_content(page):
    page.locator("#viewBtn2d").click()
    page.wait_for_function(
        "() => !document.getElementById('viewport2dWrap').hidden",
        timeout=3000,
    )
    canvas = page.locator("#viewport2d")
    box = canvas.bounding_box()
    assert box is not None
    assert box["width"] > 0
    not_blank = page.evaluate(
        """() => {
        const c = document.getElementById('viewport2d');
        const ctx = c.getContext('2d');
        const d = ctx.getImageData(0, 0, c.width, c.height).data;
        for (let i = 0; i < d.length; i += 4) {
          if (d[i] !== 13 || d[i+1] !== 17 || d[i+2] !== 23) return true;
        }
        return false;
    }"""
    )
    assert not_blank


def test_3d_scene_initialized(page):
    page.wait_for_selector("#viewport3d canvas", timeout=10000)
    has_webgl = page.evaluate(
        """() => {
        const c = document.querySelector('#viewport3d canvas');
        if (!c) return false;
        return !!(c.getContext('webgl') || c.getContext('webgl2'));
    }"""
    )
    assert has_webgl
    has_controls = page.evaluate(
        "() => typeof THREE !== 'undefined' && typeof THREE.OrbitControls === 'function'"
    )
    assert has_controls


def test_api_ui_consistency(page, httpx_client: httpx.Client, base_url: str):
    ppm_ui = page.locator("#metricPpm").inner_text()
    params = page.evaluate("() => window.CctvLensApp.readParams()")
    r = httpx_client.post("/api/calculate", json=params)
    assert r.status_code == 200
    ppm_api = str(r.json()["density"]["ppm"])
    assert ppm_ui == ppm_api


def test_tooltips_present(page):
    tips = page.locator(".has-tip").count()
    assert tips >= 10
    page.locator('[data-help="metricPpm"]').hover()
    page.wait_for_selector('[data-help="metricPpm"] .tip-bubble', state="visible", timeout=3000)


def test_share_url_restores_state(page, base_url: str):
    page.goto(
        f"{base_url}/?preset=fisheye_camera&z=0.4&obj=donut&oz=0.3",
        wait_until="domcontentloaded",
    )
    page.wait_for_selector("#metricPpm", timeout=15000)
    page.wait_for_function(
        "() => window.CctvLensApp && window.CctvLensApp.getMetricPpm() !== '—'",
        timeout=15000,
    )
    assert page.locator("#cameraPreset").input_value() == "fisheye_camera"
    assert page.locator("#distance").input_value() == "0.4"
    assert page.locator("#lensType").input_value() == "fisheye_equidistant"


def test_share_url_restores_manual_fisheye_fov(page, base_url: str):
    page.goto(f"{base_url}/?preset=fisheye_camera", wait_until="domcontentloaded")
    page.wait_for_function("() => document.getElementById('metricHfov').textContent !== '—'")
    page.locator("#fisheyeFov").fill("175")
    page.locator("#fisheyeFov").dispatch_event("input")
    page.wait_for_function("() => document.getElementById('metricHfov').textContent === '175°'")
    shared_url = page.url

    page.goto(shared_url, wait_until="domcontentloaded")
    page.wait_for_function("() => document.getElementById('metricHfov').textContent === '175°'")
    assert page.locator("#fisheyeFov").input_value() == "175"


@pytest.mark.parametrize("width,height", [(1280, 720), (1440, 900), (1920, 1080)])
def test_desktop_layout_fits_without_document_scroll(page, width: int, height: int):
    page.set_viewport_size({"width": width, "height": height})
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("() => document.getElementById('metricHfov').textContent !== '—'")
    layout = page.evaluate(
        """() => {
          const panels = ['.sidebar', '.viewport-panel', '.metrics-panel', '.dori-panel'];
          return {
            viewport: [innerWidth, innerHeight],
            document: [document.documentElement.scrollWidth, document.documentElement.scrollHeight],
            panels: panels.map((selector) => {
              const rect = document.querySelector(selector).getBoundingClientRect();
              return {
                selector,
                left: rect.left,
                top: rect.top,
                right: rect.right,
                bottom: rect.bottom,
              };
            }),
          };
        }"""
    )
    assert layout["document"][0] <= layout["viewport"][0] + 1
    assert layout["document"][1] <= layout["viewport"][1] + 1
    for panel in layout["panels"]:
        assert panel["left"] >= -1
        assert panel["top"] >= -1
        assert panel["right"] <= width + 1
        assert panel["bottom"] <= height + 1
