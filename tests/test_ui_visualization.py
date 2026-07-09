"""UI visualization consistency: 2D bbox aspect ↔ API, 3D frustum apex at cam height."""

import httpx
import pytest

pytestmark = pytest.mark.ui


def _wait_ready(page):
    page.wait_for_function(
        "() => window.CctvLensApp && window.CctvLensApp.getMetricPpm() !== '—'",
        timeout=15000,
    )


def test_donut_2d_bbox_aspect_matches_api(page, httpx_client: httpx.Client):
    """В 2D пончик должен быть почти квадратным (как API) и совпадать с 3D."""
    page.locator('.tab[data-id="donut"]').click()
    page.wait_for_timeout(300)
    _wait_ready(page)

    params = page.evaluate("() => window.CctvLensApp.readParams()")
    r = httpx_client.post("/api/calculate", json=params)
    assert r.status_code == 200
    proj = r.json()["projection"]
    assert proj["orientation"] == "upright"
    assert 0.8 < proj["aspect_wh"] < 1.25

    # Подпись в UI совпадает с метриками API
    text = page.locator("#metricObjectPx").inner_text()
    assert f"{proj['width_px']}" in text or str(int(round(proj["width_px"]))) in text
    assert "px" in text
    assert page.locator("#metricCvPass").inner_text().startswith("✓")


def test_2d_drawn_bbox_uses_api_pixel_sizes(page):
    """Canvas 2D: strokeRect bbox должен соответствовать projection.width/height_px."""
    page.locator('.tab[data-id="donut"]').click()
    page.wait_for_timeout(300)
    _wait_ready(page)

    dims = page.evaluate(
        """() => {
        const r = window.CctvLensApp.getLastResult();
        if (!r || !r.projection) return null;
        return {
          w: r.projection.width_px,
          h: r.projection.height_px,
          aspect: r.projection.width_px / r.projection.height_px,
          orientation: r.projection.orientation,
        };
    }"""
    )
    assert dims is not None
    assert dims["orientation"] == "upright"
    assert 0.8 < dims["aspect"] < 1.25


def test_cola_2d_taller_than_wide(page, httpx_client: httpx.Client):
    page.locator('.tab[data-id="cola_can"]').click()
    page.wait_for_timeout(300)
    _wait_ready(page)
    params = page.evaluate("() => window.CctvLensApp.readParams()")
    proj = httpx_client.post("/api/calculate", json=params).json()["projection"]
    assert proj["orientation"] == "upright"
    assert proj["height_px"] > proj["width_px"]


def test_3d_frustum_apex_at_mount_height(page):
    """Вершина frustum в 3D совпадает с высотой установки камеры (не пол)."""
    page.locator("#mountHeight").fill("2.5")
    page.locator("#mountHeight").dispatch_event("input")
    page.wait_for_timeout(300)
    _wait_ready(page)

    check = page.evaluate(
        """() => {
        const mh = parseFloat(document.getElementById('mountHeight').value);
        const g = typeof Scene3D !== 'undefined' && Scene3D.getLastGeometry
          ? Scene3D.getLastGeometry()
          : null;
        return {
          mount: mh,
          geom: g,
          apexMatchesCam: g && Math.abs(g.apexY - g.camY) < 1e-6,
          apexNotOnFloor: g && g.apexY > 0.5,
        };
    }"""
    )
    assert check["mount"] == 2.5
    assert check["geom"] is not None
    assert check["geom"]["camY"] == pytest.approx(2.5, abs=0.01)
    assert check["apexMatchesCam"]
    assert check["apexNotOnFloor"]
    assert check["geom"].get("doriCount", 0) >= 3


def test_all_object_tabs_produce_projection(page):
    for obj_id in ("donut", "cola_can", "basket", "person", "car"):
        page.locator(f'.tab[data-id="{obj_id}"]').click()
        page.wait_for_timeout(250)
        _wait_ready(page)
        text = page.locator("#metricObjectPx").inner_text()
        assert "px" in text
        assert text != "—"
        result = page.evaluate("() => window.CctvLensApp.getLastResult()")
        assert result["projection"] is not None
        assert result["projection"]["object_id"] == obj_id
        assert result["projection"]["width_px"] > 0
        assert result["projection"]["height_px"] > 0


def test_presets_objects_include_mesh_offsets(httpx_client: httpx.Client):
    r = httpx_client.get("/api/presets/objects")
    assert r.status_code == 200
    objs = {o["id"]: o for o in r.json()}
    assert "model_mesh_offset_x_m" in objs["cola_can"]
    assert objs["person"]["model_offset_y_m"] == 0.0
    assert objs["cola_can"]["model_mesh_offset_y_m"] != 0.0


def test_2d_canvas_matches_resolution(page):
    page.locator("#resW").fill("800")
    page.locator("#resH").fill("600")
    page.locator("#resW").dispatch_event("input")
    page.wait_for_timeout(300)
    _wait_ready(page)
    dims = page.evaluate(
        """() => {
        const c = document.getElementById('viewport2d');
        const wrap = c.parentElement;
        return {
          w: c.width,
          h: c.height,
          aspect: wrap ? wrap.style.aspectRatio : null,
        };
    }"""
    )
    assert dims["w"] == 800
    assert dims["h"] == 600
    assert dims["aspect"] == "800 / 600"
    title = page.locator("#viewport2dTitle").inner_text()
    assert "800" in title and "600" in title


def test_2d_bbox_uses_projection_center(page):
    page.locator('.tab[data-id="cola_can"]').click()
    page.wait_for_timeout(300)
    _wait_ready(page)
    check = page.evaluate(
        """() => {
        const r = window.CctvLensApp.getLastResult();
        const c = document.getElementById('viewport2d');
        return {
          center_u: r.projection.center_u_px,
          center_v: r.projection.center_v_px,
          w: c.width,
          h: c.height,
        };
    }"""
    )
    assert check["center_u"] == pytest.approx(check["w"] / 2, abs=1.0)
    assert check["center_v"] == pytest.approx(check["h"] / 2, abs=1.0)
