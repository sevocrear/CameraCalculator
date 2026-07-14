"""Browser visual tests: bbox ↔ rendered object, fisheye 180 frustum, matrix configs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.ui

FIXTURE = Path(__file__).parent / "fixtures" / "projection_matrix.json"
MATRIX = json.loads(FIXTURE.read_text(encoding="utf-8"))

# Ключевые конфигурации: rect + fisheye edge FOV
VISUAL_MATRIX = [
    ("R15", "donut"),
    ("R60", "donut"),
    ("R60", "cola_can"),
    ("R90", "cola_can"),
    ("F60", "cola_can"),
    ("F90", "basket"),
    ("F179", "basket"),
    ("F180", "cola_can"),
    ("F180", "basket"),
    ("F180", "donut"),
]

RESOLUTION_CASES = [
    (1920, 1080),
    (1280, 720),
    (640, 480),
    (2560, 1440),
]


def _wait_ready(page):
    page.wait_for_function(
        "() => window.CctvLensApp && window.CctvLensApp.getMetricPpm() !== '—'",
        timeout=15000,
    )


def _wait_model_rendered(page, timeout_ms=12000):
    page.wait_for_function(
        """() => {
        return typeof Viewport2D !== 'undefined'
          && Viewport2D.getLastScreenBBox
          && Viewport2D.getLastScreenBBox() !== null
          && Viewport2D.getLastScreenBBox().width > 0;
    }""",
        timeout=timeout_ms,
    )


def _focal_mm_for_ui(cfg: dict) -> float:
    if cfg["lens_type"] == "fisheye_equidistant":
        from cctv_lens_calc.domain.fisheye import effective_focal_from_fov

        return effective_focal_from_fov(cfg["sensor_width_mm"], cfg["hfov_deg"])
    from cctv_lens_calc.domain.projection import rectilinear_focal_from_hfov

    return rectilinear_focal_from_hfov(cfg["sensor_width_mm"], cfg["hfov_deg"])


def _sensor_format_for_cfg(cfg: dict) -> str:
    if cfg.get("sensor_format_id"):
        return cfg["sensor_format_id"]
    w = cfg["sensor_width_mm"]
    if abs(w - 7.18) < 0.01:
        return "1_1_8_inch"
    return "1_2_8_inch"


def _apply_config(page, cfg: dict, object_id: str):
    page.locator("#lensType").select_option(cfg["lens_type"])
    page.locator("#sensorFormat").select_option(_sensor_format_for_cfg(cfg))
    page.locator("#resW").fill(str(cfg["resolution_w"]))
    page.locator("#resH").fill(str(cfg["resolution_h"]))
    page.locator("#focal").fill(f"{_focal_mm_for_ui(cfg):.4f}")
    if cfg["lens_type"] == "fisheye_equidistant":
        page.locator("#fisheyeFov").fill(str(cfg["hfov_deg"]))
    page.evaluate(
        """(cfg) => {
        const setRange = (id, val) => {
          const el = document.getElementById(id);
          if (!el) return;
          el.value = String(val);
          el.dispatchEvent(new Event('input', { bubbles: true }));
          const span = document.getElementById(id + 'Val');
          if (span) span.textContent = String(val);
        };
        setRange('distance', cfg.distance_m);
        setRange('objectDistance', cfg.object_distance_m);
    }""",
        cfg,
    )
    page.locator(f'.tab[data-id="{object_id}"]').click()
    page.locator("#sensorFormat").dispatch_event("change")
    page.wait_for_timeout(400)
    _wait_ready(page)
    _wait_model_rendered(page)


def _bbox_alignment(page) -> dict:
    return page.evaluate(
        """() => {
        const align = Viewport2D.getBBoxAlignment();
        const screen = Viewport2D.getLastScreenBBox();
        const api = Viewport2D.getLastApiBBox();
        const c = document.getElementById('viewport2d');
        const wrap = c ? c.parentElement : null;
        return {
          align,
          screen,
          api,
          canvasW: c.width,
          canvasH: c.height,
          cssAspect: wrap ? wrap.style.aspectRatio : null,
          lensType: document.getElementById('lensType').value,
        };
    }"""
    )


def _canvas_has_object_pixels_in_api_bbox(page) -> bool:
    return page.evaluate(
        """() => {
        const api = Viewport2D.getLastApiBBox();
        const c = document.getElementById('viewport2d');
        if (!api || !c) return false;
        const ctx = c.getContext('2d');
        const x0 = Math.max(0, Math.floor(api.left));
        const y0 = Math.max(0, Math.floor(api.top));
        const x1 = Math.min(c.width, Math.ceil(api.left + api.width));
        const y1 = Math.min(c.height, Math.ceil(api.top + api.height));
        if (x1 <= x0 || y1 <= y0) return false;
        const data = ctx.getImageData(x0, y0, x1 - x0, y1 - y0).data;
        let nonBg = 0;
        for (let i = 0; i < data.length; i += 4) {
          const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
          if (a > 40 && (r < 200 || g < 200 || b < 200)) nonBg += 1;
        }
        const area = (x1 - x0) * (y1 - y0);
        return nonBg > area * 0.02;
    }"""
    )


@pytest.mark.parametrize("cfg_id,object_id", VISUAL_MATRIX)
def test_2d_bbox_aligns_with_rendered_object(page, cfg_id, object_id):
    """Зелёная рамка ≈ проекция физического bbox / меша (rect: ±15%, fisheye: объект внутри)."""
    cfg = next(c for c in MATRIX if c["id"] == cfg_id)
    _apply_config(page, cfg, object_id)
    data = _bbox_alignment(page)
    assert data["screen"] is not None
    assert data["api"] is not None

    if data["lensType"] == "rectilinear":
        align = data["align"]
        assert align is not None
        assert 0.82 <= align["wRatio"] <= 1.18, f"wRatio={align['wRatio']}"
        assert 0.82 <= align["hRatio"] <= 1.18, f"hRatio={align['hRatio']}"
        assert align["centerDeltaU"] < data["canvasW"] * 0.08
        assert align["centerDeltaV"] < data["canvasH"] * 0.08
    else:
        assert _canvas_has_object_pixels_in_api_bbox(page), "fisheye: объект не виден внутри bbox"


@pytest.mark.parametrize("res_w,res_h", RESOLUTION_CASES)
def test_2d_canvas_matches_resolution(page, res_w, res_h):
    """Canvas internal size and CSS aspect follow resolution W×H."""
    page.locator("#resW").fill(str(res_w))
    page.locator("#resH").fill(str(res_h))
    page.locator("#resW").dispatch_event("input")
    page.wait_for_timeout(400)
    _wait_ready(page)

    state = page.evaluate(
        """() => {
        const c = document.getElementById('viewport2d');
        const wrap = c.parentElement;
        const res = Viewport2D.getResolution();
        return {
          canvasW: c.width,
          canvasH: c.height,
          resW: res.width,
          resH: res.height,
          cssAspect: wrap ? wrap.style.aspectRatio : null,
        };
    }"""
    )
    assert state["canvasW"] == res_w
    assert state["canvasH"] == res_h
    assert state["resW"] == res_w
    assert state["resH"] == res_h
    assert state["cssAspect"] == f"{res_w} / {res_h}"


def test_sensor_format_change_updates_fov_not_canvas(page):
    page.locator("#resW").fill("1920")
    page.locator("#resH").fill("1080")
    page.locator("#resW").dispatch_event("input")
    _wait_ready(page)

    before = page.evaluate(
        """() => ({
        hfov: document.getElementById('metricHfov').textContent,
        canvasW: document.getElementById('viewport2d').width,
        canvasH: document.getElementById('viewport2d').height,
    })"""
    )

    page.locator("#sensorFormat").select_option("1_3_inch")
    page.locator("#sensorFormat").dispatch_event("change")
    page.wait_for_timeout(400)
    _wait_ready(page)

    after = page.evaluate(
        """() => ({
        hfov: document.getElementById('metricHfov').textContent,
        canvasW: document.getElementById('viewport2d').width,
        canvasH: document.getElementById('viewport2d').height,
    })"""
    )
    assert after["hfov"] != before["hfov"]
    assert after["canvasW"] == before["canvasW"] == 1920
    assert after["canvasH"] == before["canvasH"] == 1080


def test_sensor_format_change_updates_3d_frustum_width(page):
    """3D frustum half-width must follow HFOV when sensor format changes (no false cap)."""
    page.locator("#lensType").select_option("rectilinear")
    page.locator("#lensType").dispatch_event("change")
    page.locator("#focal").fill("2.8")
    page.locator("#focal").dispatch_event("input")
    page.evaluate(
        """() => {
        const setRange = (id, val) => {
          const el = document.getElementById(id);
          el.value = String(val);
          el.dispatchEvent(new Event('input', { bubbles: true }));
          document.getElementById(id + 'Val').textContent = String(val);
        };
        setRange('distance', 7.4);
        setRange('objectDistance', 0.45);
    }"""
    )
    page.locator("#sensorFormat").select_option("1_3_inch")
    page.locator("#sensorFormat").dispatch_event("change")
    page.wait_for_timeout(400)
    _wait_ready(page)

    small = page.evaluate("() => Scene3D.getFrustumState()")
    assert small is not None
    assert small["halfW"] > 0

    page.locator("#sensorFormat").select_option("2_3_inch")
    page.locator("#sensorFormat").dispatch_event("change")
    page.wait_for_timeout(400)
    _wait_ready(page)

    large = page.evaluate("() => Scene3D.getFrustumState()")
    assert large is not None
    assert large["halfW"] > small["halfW"] * 1.15
    assert large["hfovDeg"] > small["hfovDeg"]


def test_fisheye_180_user_url_coverage_and_object_visible(page, base_url):
    """URL пользователя: coverage конечный, объект виден, frustum не «в обратную сторону»."""
    page.goto(
        f"{base_url}/?preset=ceiling_fisheye_1080p&z=7.4&obj=cola_can&oz=0.45",
        wait_until="domcontentloaded",
    )
    _wait_ready(page)
    _wait_model_rendered(page)

    cov_text = page.locator("#metricCoverage").inner_text()
    assert "e+" not in cov_text.lower()
    nums = [float(x) for x in re.findall(r"[\d.]+", cov_text)]
    assert nums[0] < 50.0

    ppm = float(page.locator("#metricPpm").inner_text())
    assert ppm > 0

    assert _canvas_has_object_pixels_in_api_bbox(page)

    obj_state = page.evaluate(
        """() => {
        const dbg = Scene3D.getDebugObjectState();
        const g = Scene3D.getLastGeometry();
        return {
          holderZ: dbg ? dbg.holder[2] : null,
          apexY: g ? g.apexY : null,
          camY: g ? g.camY : null,
        };
    }"""
    )
    assert obj_state["holderZ"] is not None
    assert obj_state["holderZ"] < 0, "объект должен быть перед камерой (−Z)"
    assert obj_state["apexY"] == pytest.approx(obj_state["camY"], abs=0.01)


def test_fisheye_179_vs_180_different_pixels(page, base_url):
    page.goto(
        f"{base_url}/?preset=ceiling_fisheye_1080p&z=7.4&obj=basket&oz=0.45",
        wait_until="domcontentloaded",
    )
    _wait_ready(page)
    w180 = page.evaluate("() => window.CctvLensApp.getLastResult().projection.width_px")

    page.locator("#fisheyeFov").fill("179")
    page.locator("#fisheyeFov").dispatch_event("input")
    page.wait_for_timeout(400)
    _wait_ready(page)
    w179 = page.evaluate("() => window.CctvLensApp.getLastResult().projection.width_px")

    assert w179 > w180
    assert abs(w179 - w180) > 1.0


def test_3d_frustum_apex_at_mount_height(page):
    page.locator("#mountHeight").fill("2.5")
    page.locator("#mountHeight").dispatch_event("input")
    page.wait_for_timeout(300)
    _wait_ready(page)

    check = page.evaluate(
        """() => {
        const g = Scene3D.getLastGeometry();
        return g && Math.abs(g.apexY - g.camY) < 1e-6 && g.apexY > 0.5;
    }"""
    )
    assert check
